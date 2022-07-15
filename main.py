# coding: utf8

from apscheduler.schedulers.background import BackgroundScheduler

import subscriptions
from config import bot, logger
from subscriptions import job


@bot.message_handler(commands=["start", "help"])
def info(msg):
    bot.reply_to(msg, "Бот для ведения учёта статистики брокерского портфеля Тинькофф.\n"
                      "Доступные функции:\n"
                      "/subscribe - подписка на обновления портфеля\n"
                      "/unsubscribe - отписка от обновлений портфеля\n")


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
    scheduler.add_job(job, "interval", days=1)
    scheduler.start()

    try:
        bot.infinity_polling()
    except (KeyboardInterrupt, SystemExit) as e:
        scheduler.shutdown()
        logger.error(e)
