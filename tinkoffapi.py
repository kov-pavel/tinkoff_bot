from datetime import datetime
from decimal import Decimal
from typing import List

from tinkoff.invest import Client, Operation, RequestError

from exceptions import InvalidTinkoffToken, InvalidPortfolioID
from utils import get_now, price_to_decimal


class TinkoffApi:
    """Обёртка для работы с API Тинькова на основе библиотеки tinvest"""

    def __init__(self, tinkoff_token: str, broker_account_id: int):
        try:
            with Client(tinkoff_token) as client:
                ok = False
                for account in client.users.get_accounts().accounts:
                    if int(account.id) == broker_account_id:
                        self._broker_account_started_at = account.opened_date
                        ok = True
                        break

                if not ok:
                    raise InvalidPortfolioID()

            self._tinkoff_token = tinkoff_token
            self._broker_account_id = broker_account_id
        except RequestError:
            raise InvalidTinkoffToken()

    def get_usd_course(self) \
            -> Decimal:
        """Отдаёт текущий курс доллара в брокере"""
        return self.get_price("BBG0013HGFT4")

    def get_price(self, figi: str) \
            -> Decimal:
        """Отдаёт текущую цену фиги в брокере"""
        with Client(self._tinkoff_token) as client:
            price = client.market_data.get_last_prices(figi=[figi]).last_prices[0].price
        return price_to_decimal(price)

    def get_broker_account_started_at(self) \
            -> datetime:
        return self._broker_account_started_at

    @staticmethod
    def get_broker_account_ids(tinkoff_token: str) \
            -> List[int]:
        with Client(tinkoff_token) as client:
            accounts = client.users.get_accounts().accounts
        res = []
        for account in accounts:
            res.append(account.id)
        return res

    def get_all_operations(self) \
            -> List[Operation]:
        """Возвращает все операции в портфеле с указанной даты"""
        with Client(self._tinkoff_token) as client:
            return client \
                .operations \
                .get_operations(
                    account_id=str(self._broker_account_id),
                    from_=self._broker_account_started_at,
                    to=get_now()
                ) \
                .operations
