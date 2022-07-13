import os.path
from datetime import date
from typing import NamedTuple

import telebot.types
from tinkoff.invest import Operation

from config import bot, REPORT_NAME, SUBSCRIPTION_MESSAGE_PATTERN
from db import Database
from exceptions import NotEnoughArguments, InvalidPortfolioID
from tinkoffapi import TinkoffApi
from utils import handler, parse_int, get_canonical_price, int_to_rub


class Profit(NamedTuple):
    """Структура выгоды в отчёте"""
    absolute: int
    relative: int


NULL_PROFIT = Profit(0, 0)


class SubscriptionMessage(NamedTuple):
    """Структура распаршенного сообщения о подписке"""
    tinkoff_token: str
    broker_account_id: int
    broker_account_started_at: date


class UnsubscriptionMessage(NamedTuple):
    """Структура распаршенного сообщения об отписке"""
    broker_account_id: int


class ReportUnit:
    """Структура составной части отчёта"""
    figi: str
    name: str
    ticker: str
    currency: str
    balance: float
    bought_at_sum: int
    fee: float
    profit: Profit

    def __init__(self, *args):
        self.figi = args[0]
        self.name = args[1]
        self.ticker = args[2]
        self.currency = args[3]
        self.balance = args[4]
        self.bought_at_sum = args[5]
        self.fee = args[6]
        self.profit = args[7]

    def set_profit(self, profit: Profit):
        self.profit = profit

    def get_balance(self):
        return self.balance

    def get_bought_at_sum(self):
        return self.bought_at_sum

    def get_fee(self):
        return self.fee


@handler
def subscribe(msg: telebot.types.Message):
    try:
        parsed_subscription_msg = _parse_subscription_message(msg)

        with Database() as db:
            db.add(
                msg.from_user.id,
                parsed_subscription_msg.tinkoff_token,
                parsed_subscription_msg.broker_account_id,
            )
        bot.reply_to(msg, "Успешно!")
    except Exception as e:
        bot.reply_to(msg, e.message)


@handler
def unsubscribe(msg: telebot.types.Message):
    try:
        parsed_unsubscription_msg = _parse_unsubscription_message(msg)

        with Database() as db:
            db.delete(
                msg.from_user.id,
                parsed_unsubscription_msg.broker_account_id
            )
        bot.reply_to(msg, "Успешно!")
    except Exception as e:
        bot.reply_to(msg, e.message)


def job():
    with Database() as db:
        user_ids = db.get_user_ids()
        for user_id in user_ids:
            apis = db.get(user_id)
            for api in apis:
                _notify(_parse_api(api), user_id)


def _parse_subscription_message(msg: telebot.types.Message) \
        -> SubscriptionMessage:
    """Парсит текст пришедшего сообщения о подписке"""
    regex_res = SUBSCRIPTION_MESSAGE_PATTERN.match(msg.text)
    if not regex_res \
            or not regex_res.group(1) \
            or not regex_res.group(2):
        raise NotEnoughArguments()

    tinkoff_token = regex_res.group(1)
    broker_account_id = int(regex_res.group(2))
    broker_account_started_at = TinkoffApi(tinkoff_token, broker_account_id).get_broker_account_started_at()

    return SubscriptionMessage(tinkoff_token, broker_account_id, broker_account_started_at)


def _parse_unsubscription_message(msg: telebot.types.Message) \
        -> UnsubscriptionMessage:
    broker_account_id = parse_int(msg.text)
    user_id = msg.from_user.id

    with Database() as db:
        if db.not_exists_key(user_id, broker_account_id):
            raise InvalidPortfolioID()

    return UnsubscriptionMessage(broker_account_id)


def _notify(api: TinkoffApi, user_id: int):
    try:
        _form_report(api)
        with open(REPORT_NAME, "rb") as f:
            bot.send_document(user_id, f)
    except Exception as e:
        bot.send_message(user_id, e)
    finally:
        os.remove(REPORT_NAME)


def _parse_api(raw_api: tuple) \
        -> TinkoffApi:
    tinkoff_token = raw_api[1]
    broker_id = parse_int(raw_api[2])
    return TinkoffApi(tinkoff_token, broker_id)


def _form_report(api: TinkoffApi):
    """Формирует отчёт о доходности прослушиваемого портфеля"""

    operations_map = _get_operations_map(api)

    with open(REPORT_NAME, "w") as f:
        csv_rows = _get_csv_rows(operations_map, api)
        f.write("\n".join(csv_rows))


def _get_operations_map(api: TinkoffApi) \
        -> tuple[dict[str, ReportUnit], int]:
    res = {}
    operations = api.get_all_operations()
    total_inputs_sum = 0
    for operation in operations:
        if _is_input(operation):
            total_inputs_sum += get_canonical_price(operation.payment)
            continue

        figi = operation.figi
        name = api.get_name(figi)
        ticker = api.get_ticker(figi)
        currency = operation.currency

        balance = 0
        bought_at_sum = 0
        fee = 0

        match operation.operation_type:
            case operation.operation_type.OPERATION_TYPE_BUY:
                balance = operation.quantity
                bought_at_sum = balance * get_canonical_price(operation.price)
            case operation.operation_type.OPERATION_TYPE_BROKER_FEE:
                fee = get_canonical_price(operation.payment)
            case operation.operation_type.OPERATION_TYPE_SELL:
                bought_at_sum = -get_canonical_price(operation.payment)
                balance = -operation.quantity

        profit = NULL_PROFIT

        if _is_usd(operation):
            usd_course = api.get_usd_course()
            bought_at_sum *= usd_course
            fee *= usd_course

        if name in res.keys():
            balance += res[name].get_balance()
            bought_at_sum += res[name].get_bought_at_sum()
            fee += res[name].get_fee()

        report_unit = ReportUnit(figi, name, ticker, currency, balance, bought_at_sum, fee, profit)
        res[name] = report_unit

    for position in res.values():
        profit = _get_profit(position, api)
        position.set_profit(profit)

    return res, total_inputs_sum


def _get_csv_rows(operations_map: tuple[dict[str, ReportUnit], int], api: TinkoffApi) \
        -> list:
    csv_rows = [",".join([
        "наименование актива",
        "тикер",
        "валюта",
        "баланс",
        "куплено на сумму",
        "брокерские сборы",
        "прибыль"
    ])]

    total_bought_at_sum = 0
    total_fee_sum = 0
    total_portfolio_sum = 0

    for report_unit in operations_map[0].values():
        name = report_unit.name
        ticker = report_unit.ticker
        currency = report_unit.currency
        balance = str(report_unit.balance)
        bought_at_sum = str(report_unit.bought_at_sum)
        fee = int_to_rub(report_unit.fee)
        absolute_profit = int_to_rub(report_unit.profit.absolute)
        relative_profit = int(report_unit.profit.relative)
        profit = f"{absolute_profit} ({relative_profit}%)"

        total_bought_at_sum += report_unit.bought_at_sum
        total_fee_sum += report_unit.fee
        total_portfolio_sum += report_unit.balance * api.get_price(report_unit.figi)

        csv_rows.append(",".join([
            name,
            ticker,
            currency,
            balance,
            bought_at_sum,
            fee,
            profit
        ]))

    total_absolute_profit = int(total_portfolio_sum - total_bought_at_sum)
    total_relative_profit = int(100 * total_absolute_profit / total_bought_at_sum) if total_bought_at_sum != 0 else 0
    total_absolute_profit = int_to_rub(total_absolute_profit)
    total_profit = f"{total_absolute_profit} ({total_relative_profit}%)"
    total_balance = int_to_rub(int(operations_map[1] - total_bought_at_sum))
    total_bought_at_sum = str(total_bought_at_sum)
    total_fee_sum = int_to_rub(total_fee_sum)

    csv_rows.append(",".join([
        "Всего",
        "-",
        "rub",
        total_balance,
        total_bought_at_sum,
        total_fee_sum,
        total_profit
    ]))

    return csv_rows


def _get_profit(report_unit: ReportUnit, api: TinkoffApi) \
        -> Profit:
    bought_at_sum = report_unit.bought_at_sum
    cur_asset_value = report_unit.balance * api.get_price(report_unit.figi)
    absolute_profit = int(cur_asset_value - bought_at_sum)
    relative_profit = int(100 * absolute_profit / bought_at_sum) if bought_at_sum != 0 else 0
    return Profit(absolute_profit, relative_profit)


def _is_fee(operation: Operation) \
        -> bool:
    return operation.operation_type == operation.operation_type.OPERATION_TYPE_BROKER_FEE


def _is_buy(operation: Operation) \
        -> bool:
    return operation.operation_type == operation.operation_type.OPERATION_TYPE_BUY


def _is_input(operation: Operation) \
        -> bool:
    return operation.operation_type == operation.operation_type.OPERATION_TYPE_INPUT


def _is_usd(operation: Operation) \
        -> bool:
    return operation.currency == "usd"
