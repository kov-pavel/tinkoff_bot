import re
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

import telebot.types

from config import bot
from db import Database
from exceptions import NotEnoughArguments, InvalidPortfolio
from tinkoffapi import TinkoffApi
from utils import parse_date, parse_int, handler, no_portfolio_with_id


class SubscriptionMessage(NamedTuple):
    """Структура распаршенного сообщения о подписке"""
    tinkoff_token: str
    broker_account_id: int
    broker_account_started_at: datetime


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
                parsed_subscription_msg.broker_account_started_at
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


def _parse_subscription_message(msg: telebot.types.Message) \
        -> SubscriptionMessage:
    """Парсит текст пришедшего сообщения о подписке"""
    regex_res = re.match(r"(.+) (\d+) (\d{2}\.\d{2}\.\d{4})", msg.text)
    if not regex_res \
            or not regex_res.group(0) \
            or not regex_res.group(1) \
            or not regex_res.group(2):
        raise NotEnoughArguments()

    tinkoff_token = regex_res.group(0)
    broker_account_id = regex_res.group(1)
    broker_account_started_at = parse_date(regex_res.group(2))

    broker_account_ids = TinkoffApi.get_broker_account_ids(tinkoff_token)
    if broker_account_ids is None or no_portfolio_with_id(broker_account_id, broker_account_ids):
        raise InvalidPortfolio()

    return SubscriptionMessage(tinkoff_token, broker_account_id, broker_account_started_at)


def _parse_unsubscription_message(msg: telebot.types.Message) \
        -> UnsubscriptionMessage:
    broker_account_id = parse_int(msg.text)
    user_id = msg.from_user.id

    with Database() as db:
        if db.not_exists_key(user_id, broker_account_id):
            raise InvalidPortfolio()

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
