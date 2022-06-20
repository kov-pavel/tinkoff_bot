import re
from datetime import date
from decimal import Decimal
from typing import NamedTuple

import telebot.types
from tinkoff.invest import MoneyValue

from config import bot
from db import Database
from exceptions import NotEnoughArguments, InvalidPortfolioID
from tinkoffapi import TinkoffApi
from utils import handler, parse_int, price_to_decimal


class SubscriptionMessage(NamedTuple):
    """Структура распаршенного сообщения о подписке"""
    tinkoff_token: str
    broker_account_id: int
    broker_account_started_at: date


class UnsubscriptionMessage(NamedTuple):
    """Структура распаршенного сообщения об отписке"""
    broker_account_id: int


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
                _notify(api, user_id)


def _parse_subscription_message(msg: telebot.types.Message) \
        -> SubscriptionMessage:
    """Парсит текст пришедшего сообщения о подписке"""
    regex_res = re.match(r"(.+) (\d+)", msg.text)
    if not regex_res \
            or not regex_res.group(1) \
            or not regex_res.group(2):
        raise NotEnoughArguments()

    tinkoff_token = regex_res.group(1)
    broker_account_id = int(regex_res.group(2))
    api = TinkoffApi(tinkoff_token, broker_account_id)

    return SubscriptionMessage(tinkoff_token, broker_account_id, api.get_broker_account_started_at())


def _parse_unsubscription_message(msg: telebot.types.Message) \
        -> UnsubscriptionMessage:
    broker_account_id = parse_int(msg.text)
    user_id = msg.from_user.id

    with Database() as db:
        if db.not_exists_key(user_id, broker_account_id):
            raise InvalidPortfolioID()

    return UnsubscriptionMessage(broker_account_id)


def _notify(raw_api: tuple, user_id: int):
    api = _parse_api(raw_api)
    report = _get_report(api)
    bot.send_message(user_id, report)


def _parse_api(raw_api: tuple) \
        -> TinkoffApi:
    tinkoff_token = raw_api[1]
    broker_id = parse_int(raw_api[2])
    return TinkoffApi(tinkoff_token, broker_id)


def _get_report(api: TinkoffApi) \
        -> str:
    """Формирует отчёт о доходности прослушиваемого портфеля"""

    portfolio_sum = _get_portfolio_sum(api)
    sum_pay_in = _get_sum_pay_in(api)
    portfolio_taxes_sum = _get_portfolio_taxes_sum(api)

    income = portfolio_sum
    outcome = sum_pay_in + portfolio_taxes_sum
    profit_in_rub = income - outcome
    profit_in_percent = 100 * round(profit_in_rub / outcome, 4) if outcome != 0 else 0

    return f"Пополнения: {sum_pay_in:n} руб\n" \
           f"Удержания брокером: {portfolio_taxes_sum:n} руб\n" \
           f"Текущая  рублёвая стоимость портфеля: {portfolio_sum:n} руб\n" \
           f"Рублёвая прибыль: {profit_in_rub:n} руб ({profit_in_percent:n}%)"


def _get_portfolio_sum(api: TinkoffApi) \
        -> int:
    """Возвращает текущую стоимость портфеля в рублях"""
    operations = api.get_all_operations()
    portfolio_sum = Decimal('0')

    for operation in operations:
        if operation.operation_type == operation.operation_type.OPERATION_TYPE_BUY:
            current_ticker_cost = operation.quantity * api.get_price(operation.figi)
            if operation.currency == "usd":
                current_ticker_cost *= api.get_usd_course()
            portfolio_sum += current_ticker_cost

    return int(portfolio_sum)


def _get_portfolio_taxes_sum(api: TinkoffApi) \
        -> int:
    """Возвращает сумму всех собранных брокером налогов"""
    operations = api.get_all_operations()
    portfolio_taxes_sum = Decimal('0')

    for operation in operations:
        if operation.operation_type == operation.operation_type.OPERATION_TYPE_BROKER_FEE:
            payment = operation.payment
            payment.units = -payment.units
            payment.nano = -payment.nano
            portfolio_taxes_sum += price_to_decimal(payment)

    return int(portfolio_taxes_sum)


def _get_sum_pay_in(api: TinkoffApi) \
        -> int:
    """Возвращает сумму всех пополнений в рублях"""
    operations = api.get_all_operations()
    sum_pay_in = Decimal('0')

    for operation in operations:
        if operation.operation_type == operation.operation_type.OPERATION_TYPE_INPUT:
            sum_pay_in += price_to_decimal(operation.payment)

    return int(sum_pay_in)
