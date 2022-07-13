import os
import re

from telebot import TeleBot

TELEBOT_TOKEN = os.getenv('TELEBOT_TOKEN')
DB_NAME = "tinkoff_api.db"
REPORT_NAME = "positions.csv"
SUBSCRIPTION_MESSAGE_PATTERN = re.compile(r"(.+) (\d+)")

bot = TeleBot(TELEBOT_TOKEN)
