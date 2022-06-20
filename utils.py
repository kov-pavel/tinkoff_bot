from datetime import datetime, date
from typing import List

from pytz import timezone

from exceptions import InvalidNumber, InvalidDate


def handler(func):
    """Хендлеры имеют право не пробрасывать исключение вверх по иерархии, а осуществлять их обработку внутри себя"""

    def wrapper(msg):
        return func(msg)

    return wrapper


def localize(d: datetime) \
        -> datetime:
    return timezone('Europe/Moscow').localize(d)


def get_now() \
        -> datetime:
    return localize(datetime.now())


def parse_date(date_str: str) \
        -> date:
    yy = parse_int(date_str[0:4])
    mm = parse_int(date_str[5:7])
    dd = parse_int(date_str[8:10])

    try:
        return date(yy, mm, dd)
    except ValueError:
        raise InvalidDate()


def parse_int(n: str) \
        -> int:
    try:
        return int(n)
    except ValueError:
        raise InvalidNumber()


def no_portfolio_with_id(id: int, broker_account_ids: List[int]) \
        -> bool:
    for broker_account_id in broker_account_ids:
        if broker_account_id == id:
            return False
    return True
