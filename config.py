import os
from datetime import datetime

TELEBOT_TOKEN = os.getenv('TELEBOT_TOKEN')
TINKOFF_TOKEN = os.getenv('TINKOFF_TOKEN')
BROKER_ACCOUNT_ID = os.getenv('BROKER_ACCOUNT_ID')
BROKER_ACCOUNT_STARTED_AT = datetime.strptime(os.getenv('BROKER_ACCOUNT_STARTED_AT'), '%d.%m.%Y')
