import re
from datetime import date
from decimal import Decimal
from typing import NamedTuple

import telebot.types

from config import bot
from db import Database
from exceptions import NotEnoughArguments
from tinkoffapi import TinkoffApi
from utils import parse_date, parse_int, handler


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
    parsed_subscribe_msg = _parse_subscribe_message(msg.text)

    with Database() as db:
        db.add(
            msg.from_user.id,
            parsed_subscribe_msg.tinkoff_token,
            parsed_subscribe_msg.broker_account_id,
            parsed_subscribe_msg.broker_account_started_at
        )


@handler
def unsubscribe(msg: telebot.types.Message):
    parsed_unsubscribe_msg = _parse_unsubscribe_message(msg.text)

    with Database() as db:
        db.delete(
            msg.from_user.id,
            parsed_unsubscribe_msg.broker_account_id
        )


@handler
def get_broker_accounts_ids(msg: telebot.types.Message):
    try:
        tinkoff_token = msg.text
        bot.reply_to(msg, TinkoffApi.get_broker_account_ids(tinkoff_token))
    except ValueError:
        return bot.reply_to(msg, "Нет доступных портфелей Тинькофф инвестиций!")


def job():
    with Database() as db:
        user_ids = db.get_user_ids()
        for user_id in user_ids:
            apis = db.get(user_id)
            for api in apis:
                _notify(api, user_id)


def _parse_subscribe_message(raw_message: str) \
        -> SubscriptionMessage:
    """Парсит текст пришедшего сообщения о подписке"""
    regex_res = re.match(r"(.+) (\d+) (\d{2}\.\d{2}\.\d{4})", raw_message)
    if not regex_res \
            or not regex_res.group(0) \
            or not regex_res.group(1) \
            or not regex_res.group(2) \
            or not regex_res.group(3) \
            or not regex_res.group(4) \
            or not regex_res.group(5):
        raise NotEnoughArguments()

    tinkoff_token = regex_res.group(0)
    broker_account_id = regex_res.group(1)
    broker_account_started_at = parse_date(regex_res.group(2))

    return SubscriptionMessage(tinkoff_token, broker_account_id, broker_account_started_at)


def _parse_unsubscribe_message(raw_message: str) \
        -> UnsubscriptionMessage:
    broker_account_id = parse_int(raw_message)
    return UnsubscriptionMessage(broker_account_id)


def _notify(raw_api: tuple, user_id: int):
    api = _parse_api(raw_api)
    report = _get_report(api)
    bot.send_message(user_id, report)


def _parse_api(raw_api: tuple) \
        -> TinkoffApi:
    tinkoff_token = raw_api[1]
    broker_id = parse_int(raw_api[2])
    broker_account_started_at = parse_date(raw_api[3])
    return TinkoffApi(tinkoff_token, broker_id, broker_account_started_at)


def _get_report(api: TinkoffApi) \
        -> str:
    """Формирует отчёт о доходности прослушиваемого портфеля"""
    portfolio_sum = _get_portfolio_sum(api)
    sum_pay_in = _get_sum_pay_in(api)
    profit_in_rub = portfolio_sum - sum_pay_in
    profit_in_percent = 100 * round(profit_in_rub / sum_pay_in, 4) if sum_pay_in != 0 else 0
    return f"Пополнения: {sum_pay_in:n} руб\n" \
           f"Текущая  рублёвая стоимость портфеля: {portfolio_sum:n} руб\n" \
           f"Рублёвая прибыль: {profit_in_rub:n} руб ({profit_in_percent:n}%)"


def _get_portfolio_sum(api: TinkoffApi) \
        -> int:
    """Возвращает текущую стоимость портфеля в рублях без учета
       просто лежащих на аккаунте рублей в деньгах"""
    positions = api.get_portfolio_positions()

    portfolio_sum = Decimal('0')
    for position in positions:
        current_ticker_cost = (Decimal(str(position.balance))
                               * Decimal(str(position.average_position_price.value))
                               + Decimal(str(position.expected_yield.value)))
        if position.average_position_price.currency.name == "usd":
            current_ticker_cost *= api.get_usd_course()
        portfolio_sum += current_ticker_cost
    return int(portfolio_sum)


def _get_sum_pay_in(api: TinkoffApi) \
        -> int:
    """Возвращает сумму всех пополнений в рублях"""
    operations = api.get_all_operations()

    sum_pay_in = Decimal('0')
    for operation in operations:
        if operation.operation_type.value == "PayIn":
            sum_pay_in += Decimal(str(operation.payment))
    return int(sum_pay_in)
