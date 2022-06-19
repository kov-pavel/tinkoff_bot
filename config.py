import os

from telebot import TeleBot

TELEBOT_TOKEN = os.getenv('TELEBOT_TOKEN')
DB_NAME = "tinkoff_api.db"

bot = TeleBot(TELEBOT_TOKEN)
