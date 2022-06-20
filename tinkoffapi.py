from datetime import datetime, date
from decimal import Decimal
from typing import List

import tinvest
from tinvest import UserApi, SyncClient
from tinvest.schemas import PortfolioPosition, Operation

from exceptions import InvalidTinkoffToken
from utils import localize, get_now


class TinkoffApi:
    """Обёртка для работы с API Тинькова на основе библиотеки tinvest"""

    def __init__(self, tinkoff_token: str, broker_account_id: int, broker_account_started_at: date):
        try:
            self._client = tinvest.SyncClient(tinkoff_token)
            self._tinkoff_token = tinkoff_token
            self._broker_account_id = broker_account_id
            self._broker_account_started_at = broker_account_started_at
        except Exception:
            raise InvalidTinkoffToken()

    def get_usd_course(self) \
            -> Decimal:
        """Отдаёт текущий курс доллара в брокере"""
        return Decimal(str(
            tinvest.MarketApi(self._client) \
                .market_orderbook_get(figi="BBG0013HGFT4", depth=1) \
                .parse_json().payload
                .last_price
        ))

    @staticmethod
    def get_broker_account_ids(tinkoff_token: str) \
            -> List[int]:
        portfolios = UserApi(SyncClient(tinkoff_token)).accounts_get().parse_json().payload.accounts
        res = []
        for portfolio in portfolios:
            res.append(portfolio.broker_account_id)
        return res

    def get_portfolio_positions(self) \
            -> List[PortfolioPosition]:
        """Возвращает все позиции в портфеле"""
        positions = tinvest.PortfolioApi(self._client) \
            .portfolio_get(broker_account_id=self._broker_account_id) \
            .parse_json().payload.positions
        return positions

    def get_all_operations(self) \
            -> List[Operation]:
        """Возвращает все операции в портфеле с указанной даты"""
        now = get_now()

        operations = tinvest \
            .OperationsApi(self._client) \
            .operations_get(broker_account_id=self._broker_account_id, from_=self._broker_account_started_at.__str__(), to=now) \
            .parse_json().payload.operations
        return operations
