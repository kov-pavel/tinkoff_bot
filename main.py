import schedule as schedule

from config import bot
from subscriptions import job, subscribe, unsubscribe, get_broker_accounts_ids


@bot.message_handler(commands=["start", "help"])
def info(msg):
    bot.reply_to(msg, "Бот для ведения учёта статистики брокерского портфеля Тинькофф.\n"
                      "Доступные функции:\n"
                      "/subscribe - подписка на обновления портфеля\n"
                      "/unsubscribe - отписка от обновлений портфеля\n"
                      "/broker_account_ids - вывод всех доступных портфелей")


@bot.message_handler(commands=["subscribe"])
def subscribe(msg):
    bot.reply_to(msg, "Введите информацию о новой подписке в формате: "
                      "<Tinkoff API token> "
                      "<Broker account ID> "
                      "<Дата начала прослушки>"
                 )
    bot.register_next_step_handler(msg, subscribe)


@bot.message_handler(commands=["unsubscribe"])
def unsubscribe(msg):
    bot.reply_to(msg, "Введите информацию об отписке в формате: "
                      "<Broker account ID> "
                 )
    bot.register_next_step_handler(msg, unsubscribe)


@bot.message_handler(commands=["broker_account_ids"])
def get_broker_account_ids(msg):
    bot.reply_to(msg, "Введите Tinkoff API token")
    bot.register_next_step_handler(msg, get_broker_accounts_ids)


if __name__ == "__main__":
    schedule.every().day.at("21:00").do(job)

    while True:
        schedule.run_pending()
        bot.infinity_polling()
