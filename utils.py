# coding: utf8
import codecs
from datetime import datetime

from pytz import timezone
from tinkoff.invest import MoneyValue

from config import RUBBLES_SHORTCUT, ENCODING
from exceptions import InvalidNumber


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


def parse_int(n: str) \
        -> int:
    try:
        return int(n)
    except ValueError:
        raise InvalidNumber()


def get_canonical_price(price: MoneyValue) -> float:
    return float(str(abs(price.units)) + "." + str(abs(price.nano)))


def to_rub(i: float) \
        -> str:
    return str(i) + " " + RUBBLES_SHORTCUT


def list_to_string(l: list) \
        -> str:
    res: str = ""
    for elem in l:
        res += str(elem) + "\n"
    return res


def write_file(path: str, src: str):
    with codecs.open(path, "w", ENCODING) as f:
        f.write(src)
