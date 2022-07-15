import os.path
from datetime import date
from typing import NamedTuple

import telebot.types
from tinkoff.invest import Operation

from config import bot, REPORT_NAME, SUBSCRIPTION_MESSAGE_PATTERN, logger, BALANCE_SHORTCUT, RUBBLES_SHORTCUT
from db import Database
from exceptions import NotEnoughArguments, InvalidPortfolioID, InvalidTinkoffToken, InvalidNumber
from tinkoffapi import TinkoffApi
from utils import handler, parse_int, get_canonical_price, to_rub, list_to_string


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
    _figi: str
    _name: str
    _ticker: str
    _currency: str
    _balance: float
    _bought_at_sum: int
    _fee: int
    _absolute_profit: Profit or str
    _relative_profit: Profit

    def __init__(self, *args):
        self._figi = args[0]
        self._name = args[1]
        self._ticker = args[2]
        self._currency = args[3]
        self._balance = args[4]
        self._bought_at_sum = args[5]
        self._fee = args[6]
        self._absolute_profit = args[7]
        self._relative_profit = args[8]

    def set_relative_profit(self, relative_profit: Profit):
        self._relative_profit = relative_profit

    def get_figi(self):
        return self._figi

    def get_name(self):
        return self._name

    def get_ticker(self):
        return self._ticker

    def get_currency(self):
        return self._currency

    def get_balance(self):
        return self._balance

    def get_bought_at_sum(self):
        return self._bought_at_sum

    def get_fee(self):
        return self._fee

    def get_absolute_profit(self):
        return self._absolute_profit

    def get_relative_profit(self):
        return self._relative_profit


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
    except (NotEnoughArguments, InvalidNumber, InvalidPortfolioID, InvalidTinkoffToken) as e:
        bot.reply_to(msg, e.message)
    except Exception as e:
        bot.reply_to(msg, "Не могу подписаться на прослушивание портфеля!")
        logger.error(e)


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
    except (NotEnoughArguments, InvalidNumber, InvalidPortfolioID) as e:
        bot.reply_to(msg, e.message)
    except Exception as e:
        bot.reply_to(msg, "Не могу отписаться от прослушивания портфеля!")
        logger.error(e)


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


@handler
def _notify(api: TinkoffApi, user_id: int):
    try:
        _form_report(api)
        with open(REPORT_NAME, "rb") as f:
            bot.send_document(user_id, f)
    except Exception as e:
        bot.send_message(user_id, "Произошла фатальная ошибка! Пожалуйста, сообщите о ней администратору.")
        print(e)
        logger.error(e)
    finally:
        if os.path.exists(os.path.realpath(REPORT_NAME)):
            os.remove(REPORT_NAME)


def _parse_api(raw_api: tuple) \
        -> TinkoffApi:
    tinkoff_token = raw_api[1]
    broker_id = parse_int(raw_api[2])
    return TinkoffApi(tinkoff_token, broker_id)


def _form_report(api: TinkoffApi):
    """Формирует отчёт о доходности прослушиваемого портфеля"""

    operations_map = _get_operations_map(api)
    csv_rows = _get_csv_rows(operations_map, api)
    csv_rows = list_to_string(csv_rows)

    with open(REPORT_NAME, "w") as f:
        f.write(csv_rows)


def _get_operations_map(api: TinkoffApi) \
        -> tuple[dict[str, ReportUnit], int]:
    res = {}
    operations = api.get_all_operations()
    total_inputs_sum = 0
    for operation in operations:
        if _is_input(operation):
            total_inputs_sum += int(get_canonical_price(operation.payment))
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
                bought_at_sum = int(balance * get_canonical_price(operation.price))
            case operation.operation_type.OPERATION_TYPE_BROKER_FEE:
                fee = int(get_canonical_price(operation.payment))
            case operation.operation_type.OPERATION_TYPE_SELL:
                bought_at_sum = -int(get_canonical_price(operation.payment))
                balance = -operation.quantity

        absolute_profit = NULL_PROFIT
        relative_profit = NULL_PROFIT

        if _is_usd(operation):
            usd_course = api.get_usd_course()
            bought_at_sum *= usd_course
            fee *= usd_course

        if name in res.keys():
            balance += res[name].get_balance()
            bought_at_sum += res[name].get_bought_at_sum()
            fee += res[name].get_fee()

        report_unit\
            = ReportUnit(figi, name, ticker, currency, balance, bought_at_sum, fee, absolute_profit, relative_profit)
        res[name] = report_unit

    for position in res.values():
        relative_profit = _get_relative_profit(position, api)
        position.set_relative_profit(relative_profit)

    return res, total_inputs_sum


def _get_csv_rows(operations_map: tuple[dict[str, ReportUnit], int], api: TinkoffApi) \
        -> list[str]:
    csv_rows = _form_csv_titles()

    total_bought_at_sum = 0
    total_fee_sum = 0
    total_portfolio_sum = 0

    for report_unit in operations_map[0].values():
        completed_csv_row = _get_completed_csv_row(report_unit)
        _append_csv_row(completed_csv_row, csv_rows)

        total_bought_at_sum += report_unit.get_bought_at_sum()
        total_fee_sum += report_unit.get_fee()
        total_portfolio_sum += int(report_unit.get_balance() * api.get_price(report_unit.get_figi()))

    total_inputs_sum = operations_map[1]
    total_completed_csv_row = _get_total_completed_csv_row(total_bought_at_sum, total_fee_sum,
                                                           total_portfolio_sum, total_inputs_sum)
    _append_csv_row(total_completed_csv_row, csv_rows)

    return csv_rows


def _form_csv_titles() \
        -> list[str]:
    return [",".join([
        "securities name",
        "ticker",
        "currency",
        "balance",
        "bought at sum",
        "broker's fees",
        "absolute profit",
        "relative profit"
    ])]


def _get_completed_csv_row(report_unit: ReportUnit) \
        -> ReportUnit:
    figi = report_unit.get_figi()
    name = report_unit.get_name()
    ticker = report_unit.get_ticker()
    currency = report_unit.get_currency()
    balance = str(report_unit.get_balance()) + " " + BALANCE_SHORTCUT
    bought_at_sum = str(report_unit.get_bought_at_sum())
    fee = to_rub(report_unit.get_fee())
    absolute_profit = to_rub(report_unit.get_relative_profit().absolute)
    relative_profit = int(report_unit.get_relative_profit().relative)
    relative_profit = f"{absolute_profit} ({relative_profit}%)"
    absolute_profit = "-"

    return ReportUnit(
        figi,
        name,
        ticker,
        currency,
        balance,
        bought_at_sum,
        fee,
        absolute_profit,
        relative_profit
    )


def _get_total_completed_csv_row(total_bought_at_sum: int, total_fee_sum: int,
                                 total_portfolio_sum: int, total_inputs_sum: int) \
        -> ReportUnit:
    figi = ""
    total_relative_absolute_profit = total_portfolio_sum - total_bought_at_sum
    total_relative_relative_profit = int(
        100.0 * total_relative_absolute_profit / total_bought_at_sum) if total_bought_at_sum != 0 else 0
    total_absolute_absolute_profit = total_relative_absolute_profit
    total_relative_absolute_profit = to_rub(total_relative_absolute_profit)
    total_relative_profit = f"{total_relative_absolute_profit} ({total_relative_relative_profit}%)"
    total_absolute_relative_profit = int(
        100.0 * total_absolute_absolute_profit / total_inputs_sum) if total_inputs_sum != 0 else 0
    total_absolute_absolute_profit = to_rub(total_absolute_absolute_profit)
    total_absolute_profit = f"{total_absolute_absolute_profit} ({total_absolute_relative_profit}%)"

    total_balance = to_rub(total_inputs_sum - total_bought_at_sum)
    total_bought_at_sum = str(total_bought_at_sum)
    total_fee_sum = to_rub(total_fee_sum)

    return ReportUnit(
        figi,
        "Total",
        "-",
        RUBBLES_SHORTCUT,
        total_balance,
        total_bought_at_sum,
        total_fee_sum,
        total_absolute_profit,
        total_relative_profit
    )


def _append_csv_row(csv_row: ReportUnit, csv_rows: list[str]):
    csv_rows.append(",".join([
        csv_row.get_name(),
        csv_row.get_ticker(),
        csv_row.get_currency(),
        csv_row.get_balance(),
        csv_row.get_bought_at_sum(),
        csv_row.get_fee(),
        csv_row.get_absolute_profit(),
        csv_row.get_relative_profit()
    ]))


def _get_relative_profit(report_unit: ReportUnit, api: TinkoffApi) \
        -> Profit:
    bought_at_sum = report_unit.get_bought_at_sum()
    cur_asset_value = report_unit.get_balance() * api.get_price(report_unit.get_figi())
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
