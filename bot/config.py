import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ORDER_CHANNEL_ID = int(os.getenv("ORDER_CHANNEL_ID", "0"))
MEMBERSHIP_CHANNEL_ID = int(os.getenv("MEMBERSHIP_CHANNEL_ID", "0"))
