import logging
import os
import re

import telebot
from telebot import TeleBot

TELEBOT_TOKEN = os.getenv('TELEBOT_TOKEN')
DB_NAME = "tinkoff_api.db"
REPORT_NAME = "positions.csv"
SUBSCRIPTION_MESSAGE_PATTERN = re.compile(r"(.+) (\d+)")
BALANCE_SHORTCUT = "items"
RUBBLES_SHORTCUT = "rub"

bot = TeleBot(TELEBOT_TOKEN)
logger = telebot.logger
telebot.logger.setLevel(logging.ERROR)
