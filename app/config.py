import os
from typing import List
import yaml

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "30"))
DB_PATH = os.getenv("DB_PATH", "/data/sent_articles.db")
MAX_ARTICLE_AGE_HOURS = int(os.getenv("MAX_ARTICLE_AGE_HOURS", "1"))
SEND_INTERVAL_SECONDS = int(os.getenv("SEND_INTERVAL_SECONDS", "60"))
FEEDS_FILE = os.getenv("FEEDS_FILE", "/app/feeds.yaml")
DEDUP_SIMILARITY_THRESHOLD = float(os.getenv("DEDUP_SIMILARITY_THRESHOLD", "0.35"))
TRANSLATE_TO_PERSIAN = os.getenv("TRANSLATE_TO_PERSIAN", "false").lower() in (
    "1",
    "true",
    "yes",
)


def _load_feeds() -> List[dict]:
    with open(FEEDS_FILE) as fh:
        data = yaml.safe_load(fh)
    feeds = data.get("feeds") or []
    if not feeds:
        raise ValueError(f"No feeds found in {FEEDS_FILE}")
    for entry in feeds:
        if not entry.get("name") or not entry.get("url"):
            raise ValueError(f"Each feed must have 'name' and 'url'. Bad entry: {entry}")
    return feeds


FEEDS = _load_feeds()
