"""
Culers Hub – Barça RSS → Telegram bot
Fetches the 4 validated Barça RSS feeds and pushes new articles
to a Telegram channel on a configurable schedule.
"""

import logging
import sys
import time

from config import CHECK_INTERVAL_MINUTES, FEEDS, SEND_INTERVAL_SECONDS
from feed_fetcher import fetch_all
from storage import init_db, is_sent, mark_sent
from telegram_sender import send_article, verify_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)



def run_once() -> None:
    logger.info("── Checking feeds ──────────────────────────────────")
    articles = fetch_all()
    logger.info("Total articles fetched: %d", len(articles))

    sent_count = 0
    skipped_count = 0

    for article in articles:
        if is_sent(article.id):
            skipped_count += 1
            continue

        logger.info("Sending: [%s] %s", article.source, article.title)
        success = send_article(article)
        if success:
            mark_sent(article.id)
            sent_count += 1
            time.sleep(SEND_INTERVAL_SECONDS)
        else:
            logger.warning("Failed to send article, will retry next cycle: %s", article.title)

    logger.info(
        "Cycle complete – sent: %d  already seen: %d  total: %d",
        sent_count,
        skipped_count,
        len(articles),
    )


def main() -> None:
    logger.info("═══════════════════════════════════════════════════")
    logger.info("  Culers Hub – Barça RSS → Telegram")
    logger.info("  Active feeds  : %d", len(FEEDS))
    logger.info("  Check interval: every %d minutes", CHECK_INTERVAL_MINUTES)
    logger.info("  Send interval : %d seconds between posts", SEND_INTERVAL_SECONDS)
    logger.info("═══════════════════════════════════════════════════")

    init_db()

    if not verify_bot():
        logger.critical("Aborting: invalid Telegram bot token.")
        sys.exit(1)

    interval_seconds = CHECK_INTERVAL_MINUTES * 60

    while True:
        run_once()
        logger.info("Next check in %d minutes…", CHECK_INTERVAL_MINUTES)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
