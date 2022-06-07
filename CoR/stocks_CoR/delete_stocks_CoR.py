from CoR.stocks_CoR.utils import valid_ticker, positive_number
from config import bot
from db import Database


@bot.message_handler(commands=['delete_stocks'])
def read_ticker(msg):
    bot.reply_to(msg, "Введите тикер")
    bot.register_next_step_handler(msg, read_stocks_count)


@valid_ticker(bot)
def read_stocks_count(msg):
    ticker = msg.text
    bot.reply_to(msg, "Введите кол-во акций")
    bot.register_next_step_handler(msg, read_stocks_cost, ticker=ticker)


@positive_number(bot)
def read_stocks_cost(msg, stocks_amount: int, ticker: str):
    bot.reply_to(msg, "Введите стоимость акций")
    bot.register_next_step_handler(msg, delete_stocks, ticker=ticker, stocks_amount=stocks_amount)


@positive_number(bot)
def delete_stocks(msg, stocks_cost: float, ticker: str, stocks_amount: int):
    with Database() as db:
        stocks = db.get_stocks(ticker)
        
        if (stocks is None) or (stocks[1] < stocks_amount):
            bot.reply_to(msg, "У вас нет такого количества акций")
            return
        
        if stocks[1] == stocks_amount:
            db.delete_stocks(ticker)
        else:
            stocks[1] -= stocks_amount
            stocks[2] -= stocks_cost
            db.update_stocks(ticker, stocks[1], stocks[2])

        print(db.get_stocks_packages())

    bot.reply_to(msg, "Успешно!")
