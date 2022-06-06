import logging
import os

import telebot

DB_NAME = "stocks.db"
token = os.getenv("TOKEN")
bot = telebot.TeleBot(token)
logger = telebot.logger
telebot.logger.setLevel(logging.ERROR)
