from datetime import datetime

from pytz import timezone

from exceptions import InvalidNumber, InvalidDate


def handler(func):
    """Хендлеры имеют право не пробрасывать исключение вверх по иерархии, а осуществлять их обработку внутри себя"""

    def wrapper(msg):
        return func(msg)

    return wrapper


def localize(d: datetime) -> datetime:
    return timezone('Europe/Moscow').localize(d)


def get_now() -> datetime:
    return localize(datetime.now())


def parse_date(date_str: str) -> datetime:
    yy = parse_int(date_str[4:8])
    mm = parse_int(date_str[2:4])
    dd = parse_int(date_str[0:2])

    try:
        return datetime(yy, mm, dd)
    except ValueError:
        raise InvalidDate()


def parse_int(n: str) -> int:
    try:
        return int(n)
    except ValueError:
        raise InvalidNumber()


def no_portfolio_with_id(id: int, broker_account_ids: list) -> bool:
    for broker_account_id in broker_account_ids:
        if broker_account_id[3] == id:
            return False
    return True
