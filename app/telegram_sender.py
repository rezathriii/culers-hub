import logging
import time
from typing import Optional

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from feed_fetcher import Article

logger = logging.getLogger(__name__)

_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Telegram HTML parse-mode caps
_CAPTION_LIMIT = 1024
_MESSAGE_LIMIT = 4096


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def _esc(text: str) -> str:
    """Escape text for Telegram HTML parse mode."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _format_date(article: Article) -> str:
    if article.published_at is None:
        return ""
    return article.published_at.strftime("📅 %d %b %Y, %H:%M UTC")


def _format_html(article: Article) -> str:
    source = _esc(article.source)
    title = _esc(article.title)
    summary = _esc(article.summary)
    url = article.url
    date_line = _format_date(article)
    date_str = f"\n<i>{date_line}</i>" if date_line else ""
    return (
        f"<b>🔵 {source}</b>{date_str}\n\n"
        f"<b>{title}</b>\n\n"
        f"{summary}\n\n"
        f'<a href="{url}">Read more →</a>'
    )


# ---------------------------------------------------------------------------
# Telegram API calls with retry
# ---------------------------------------------------------------------------

def _post(endpoint: str, payload: dict, retries: int = 3) -> Optional[dict]:
    url = f"{_API_BASE}/{endpoint}"
    for attempt in range(retries):
        try:
            resp = requests.post(url, json=payload, timeout=30)
            data = resp.json()
            if resp.ok:
                return data
            logger.error("Telegram %s error (attempt %d/%d): %s", endpoint, attempt + 1, retries, data)
            if resp.status_code != 429 and 400 <= resp.status_code < 500:
                return None
            if attempt < retries - 1:
                backoff = 2 ** attempt
                logger.info("Retrying in %ds…", backoff)
                time.sleep(backoff)
        except requests.RequestException as exc:
            logger.error("Network error on %s (attempt %d/%d): %s", endpoint, attempt + 1, retries, exc)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return None


def _send_photo(photo_url: str, caption: str) -> bool:
    result = _post(
        "sendPhoto",
        {
            "chat_id": TELEGRAM_CHAT_ID,
            "photo": photo_url,
            "caption": caption[:_CAPTION_LIMIT],
            "parse_mode": "HTML",
        },
    )
    return result is not None


def _send_message(text: str) -> bool:
    result = _post(
        "sendMessage",
        {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text[:_MESSAGE_LIMIT],
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
    )
    return result is not None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_article(article: Article) -> bool:
    """
    Send an article to the configured Telegram channel.
    If the article has an image, uses sendPhoto; otherwise sendMessage.
    Falls back to sendMessage if the photo URL fails.
    Returns True on success.
    """
    caption = _format_html(article)

    if article.image_url:
        success = _send_photo(article.image_url, caption)
        if not success:
            logger.warning("Photo send failed for '%s'; falling back to text message", article.title)
            success = _send_message(caption)
        return success

    return _send_message(caption)


def verify_bot() -> bool:
    """Call getMe to confirm the bot token is valid before starting the loop."""
    result = _post("getMe", {}, retries=1)
    if result and result.get("ok"):
        username = result["result"].get("username", "?")
        logger.info("Telegram bot verified: @%s", username)
        return True
    logger.error("Telegram bot verification failed. Check TELEGRAM_BOT_TOKEN.")
    return False
