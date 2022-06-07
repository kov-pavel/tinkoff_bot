from CoR.stocks_CoR import add_stocks_CoR
from CoR.stocks_CoR import delete_stocks_CoR

from config import bot
from db import Database


if __name__ == '__main__':
    bot.infinity_polling()
    # with Database() as db:
    #     db.cmd()
