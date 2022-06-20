import datetime
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from tinkoff.invest import Client

import subscriptions
from config import bot
from subscriptions import job
from utils import get_now


@bot.message_handler(commands=["start", "help"])
def info(msg):
    bot.reply_to(msg, "Бот для ведения учёта статистики брокерского портфеля Тинькофф.\n"
                      "Доступные функции:\n"
                      "/subscribe - подписка на обновления портфеля\n"
                      "/unsubscribe - отписка от обновлений портфеля\n")
    bot.reply_to(msg, datetime.datetime.now().time())


@bot.message_handler(commands=["subscribe"])
def subscribe(msg):
    bot.reply_to(msg, "Введите информацию о новой подписке в формате: "
                      "<Tinkoff API token> "
                      "<Broker account ID> "
                 )
    bot.register_next_step_handler(msg, subscriptions.subscribe)


@bot.message_handler(commands=["unsubscribe"])
def unsubscribe(msg):
    bot.reply_to(msg, "Введите информацию об отписке в формате: "
                      "<Broker account ID> "
                 )
    bot.register_next_step_handler(msg, subscriptions.unsubscribe)


if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(job, "interval", seconds=10)
    scheduler.start()

    try:
        bot.infinity_polling()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

    # Sample of interaction with library
    # with Client('t.OlLuxv6KVTTFcCflCyXnVXdMN-_hk2PLSjqmbPe-x5dlGFkiuNCKzS5opq6C3Jt9nSJ460soBaHjayI9z3d68g') as client:
    #     a = client.users.get_accounts().accounts
    #     b = client.operations \
    #         .get_operations(
    #             account_id=str(a[2].id),
    #             from_=a[2].opened_date,
    #             to=get_now()
    #         ) \
    #         .operations
    #     print(a[0].id)

    # t.OlLuxv6KVTTFcCflCyXnVXdMN-_hk2PLSjqmbPe-x5dlGFkiuNCKzS5opq6C3Jt9nSJ460soBaHjayI9z3d68g 2149013142
