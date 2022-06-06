import re
from urllib.request import urlopen

from lxml import html
from lxml.etree import _Element


def valid_ticker(bot):
    def inner(func):
        def wrapper(msg):
            try:
                check_ticker(msg.text)
            except ValueError as ex:
                return bot.reply_to(msg, ex)

            return func(msg)

        return wrapper

    return inner


def positive_number(bot):
    def inner(func):
        def wrapper(*args, **kwargs):
            try:
                msg = args[0]
                num = float(msg.text)

                if num <= 0:
                    return bot.reply_to(msg, "Недопустимое значение")
            except ValueError:
                return bot.reply_to(msg, "Неправильный формат")

            return func(msg, num, **kwargs)

        return wrapper

    return inner


def check_ticker(ticker: str) -> _Element:
    page = html.parse(urlopen('https://www.tinkoff.ru/invest/stocks/' + ticker))
    found = page.xpath(
        '/html/body/div[1]/div/div[2]/div/div[1]/div[2]/div[1]/div[2]/div/div[2]/div[1]/div/div/div[2]/span/span')

    if len(found) == 0:
        raise ValueError("Нет компании с таким тикером")

    return found


# will be in backend
def take_stocks_cost(ticker: str) -> int:
    found = check_ticker(ticker)
    node = found[0]
    cost = node.text_content().replace(" ", "")
    cost = int(re.sub("[^0-9,]", "", cost))
    return cost

