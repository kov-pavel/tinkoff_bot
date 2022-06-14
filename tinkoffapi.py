from decimal import Decimal
from typing import List

import tinvest
import tinvest.schemas

from config import TINKOFF_TOKEN, BROKER_ACCOUNT_ID, BROKER_ACCOUNT_STARTED_AT
from utils import localize, get_now


class TinkoffApi:
    """Обёртка для работы с API Тинькова на основе библиотеки tinvest"""

    def __init__(self):
        self._client = tinvest.SyncClient(TINKOFF_TOKEN)

    def get_usd_course(self) -> Decimal:
        """Отдаёт текущий курс доллара в брокере"""
        return Decimal(str(
            tinvest.MarketApi(self._client) \
                .market_orderbook_get(figi="BBG0013HGFT4", depth=1) \
                .parse_json().payload
                .last_price
        ))

    def get_portfolio_positions(self) \
            -> List[tinvest.schemas.PortfolioPosition]:
        """Возвращает все позиции в портфеле"""
        positions = tinvest.PortfolioApi(self._client) \
            .portfolio_get(broker_account_id=BROKER_ACCOUNT_ID) \
            .parse_json().payload.positions
        return positions

    def get_all_operations(self) \
            -> List[tinvest.schemas.Operation]:
        """Возвращает все операции в портфеле с указанной даты"""
        from_ = localize(BROKER_ACCOUNT_STARTED_AT)
        now = get_now()

        operations = tinvest \
            .OperationsApi(self._client) \
            .operations_get(broker_account_id=BROKER_ACCOUNT_ID, from_=from_, to=now) \
            .parse_json().payload.operations
        return operations
