import os

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "30"))
DB_PATH = os.getenv("DB_PATH", "/data/sent_articles.db")
MAX_ARTICLE_AGE_HOURS = int(os.getenv("MAX_ARTICLE_AGE_HOURS", "48"))
SEND_INTERVAL_SECONDS = int(os.getenv("SEND_INTERVAL_SECONDS", "60"))

FEEDS = [
    {"name": "Barca Blaugranes", "url": "https://www.barcablaugranes.com/rss/index.xml"},
    {"name": "Barca Universal", "url": "https://barcauniversal.com/feed"},
    {"name": "BarcaBlog", "url": "https://barcablog.com/feed"},
    {"name": "Barcelona Football Blog", "url": "https://barcelonafootballblog.com/feed"},
    {"name": "Barca News Network", "url": "https://barcanewsnetwork.com/feed"},
]
