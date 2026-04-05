import logging
import re
import unicodedata
import hashlib
import html
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import feedparser
from bs4 import BeautifulSoup
from config import (
    DEDUP_SIMILARITY_THRESHOLD,
    FEEDS,
    MAX_ARTICLE_AGE_HOURS,
    TRANSLATE_TO_PERSIAN,
)
from summarizer import summarize, translate_to_persian

logger = logging.getLogger(__name__)


@dataclass
class Article:
    id: str
    source: str
    title: str
    url: str
    summary: str
    image_url: Optional[str]
    published_at: Optional[datetime]
    canonical_url: str
    title_key: str
    content_hash: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean_text(text: str) -> str:
    """
    Full sanitisation pipeline applied to both title and summary:
      1. Parse through BeautifulSoup  → strips HTML tags + decodes entities
      2. Normalize unicode (NFC)       → canonical form, no weird composed chars
      3. Remove control characters     → keep only printable + normal whitespace
      4. Collapse whitespace           → no runs of spaces/newlines
    """
    if not text or not text.strip():
        return ""
    # Only run BS4 if the string looks like it might contain HTML
    if "<" in text or "&" in text:
        text = BeautifulSoup(text, "lxml").get_text(separator=" ")
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[^\S\n\r\t ]+", " ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"[\u200b\u200c\u200d\u200e\u200f\u00ad\ufeff]", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    truncated = text[: max_len - 1].rsplit(" ", 1)[0]
    return truncated + "…"


def canonicalize_url(url: str) -> str:
    """Normalize URLs so tracking-query variants map to the same key."""
    if not url:
        return ""
    try:
        split = urlsplit(url.strip())
        query_pairs = [
            (k, v)
            for k, v in parse_qsl(split.query, keep_blank_values=True)
            if not (k.startswith("utm_") or k in {"fbclid", "gclid", "igshid", "mc_cid", "mc_eid"})
        ]
        query = urlencode(sorted(query_pairs), doseq=True)
        normalized_path = re.sub(r"/{2,}", "/", split.path.rstrip("/"))
        return urlunsplit(
            (
                split.scheme.lower(),
                split.netloc.lower(),
                normalized_path,
                query,
                "",
            )
        )
    except Exception:
        return url.strip()


def normalize_title(title: str) -> str:
    """Normalize title text for stable duplicate comparisons."""
    normalized = _clean_text(html.unescape(title or "")).lower()
    normalized = re.sub(r"[\W_]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def article_content_hash(title: str, summary: str) -> str:
    """Create stable hash fingerprint from normalized title and summary excerpt."""
    payload = f"{normalize_title(title)}|||{_clean_text(summary).lower()[:300]}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Cross-source title deduplication
# ---------------------------------------------------------------------------

_STOP_WORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "as",
    "is",
    "was",
    "are",
    "were",
    "be",
    "it",
    "its",
    "this",
    "that",
    "he",
    "she",
    "they",
    "we",
    "has",
    "have",
    "after",
    "will",
    "could",
    "would",
    "about",
    "over",
    "vs",
    "fc",
    "cf",
    "barcelona",
    "barca",
    "در",
    "به",
    "از",
    "با",
    "برای",
    "این",
    "آن",
    "که",
    "و",
    "la",
    "el",
    "los",
    "las",
    "de",
    "del",
    "y",
    "en",
}


def title_tokens(title: str) -> frozenset:
    """Normalize a title to a frozenset of meaningful lowercase word tokens."""
    cleaned = normalize_title(title)
    tokens = {tok for tok in cleaned.split() if tok not in _STOP_WORDS and len(tok) > 1}
    return frozenset(tokens)


def is_similar_title(
    title: str,
    seen: list,
    threshold: float = DEDUP_SIMILARITY_THRESHOLD,
) -> bool:
    """
    Return True if 'title' is too similar to any title in 'seen'.
    Uses Jaccard similarity on word token sets.
    A threshold of 0.5 means 50 % token overlap → treated as the same story.
    """
    tokens = title_tokens(title)
    if not tokens:
        return False
    for seen_tokens in seen:
        union = tokens | seen_tokens
        if union and len(tokens & seen_tokens) / len(union) >= threshold:
            return True
    return False


def _extract_image(entry) -> Optional[str]:
    """
    Try multiple locations where a feed entry may carry an image:
      1. media:content  (feedparser: entry.media_content)
      2. media:thumbnail
      3. enclosure
      4. First <img> inside entry content / summary HTML
    """
    media_content = getattr(entry, "media_content", None)
    if media_content:
        for m in media_content:
            url = m.get("url", "")
            mime = m.get("type", "")
            medium = m.get("medium", "")
            if url and (medium == "image" or mime.startswith("image")):
                return url
        url = media_content[0].get("url", "")
        if url:
            return url

    media_thumbnail = getattr(entry, "media_thumbnail", None)
    if media_thumbnail:
        url = media_thumbnail[0].get("url", "")
        if url:
            return url

    enclosures = getattr(entry, "enclosures", None)
    if enclosures:
        for enc in enclosures:
            if "image" in enc.get("type", ""):
                return enc.get("href") or enc.get("url") or ""

    raw_html = ""
    content = getattr(entry, "content", None)
    if content:
        raw_html = content[0].get("value", "")
    if not raw_html:
        raw_html = getattr(entry, "summary", "") or ""

    if raw_html:
        soup = BeautifulSoup(raw_html, "lxml")
        img = soup.find("img")
        if img:
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""
            if src.startswith("http"):
                return src

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _parse_date(entry) -> Optional[datetime]:
    """Return a timezone-aware UTC datetime from feedparser's parsed time structs."""
    import calendar

    for field in ("published_parsed", "updated_parsed"):
        val = entry.get(field)
        if val:
            try:
                ts = calendar.timegm(val)
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                pass
    return None


def _is_too_old(published_at: Optional[datetime]) -> bool:
    """Return True if the article is older than MAX_ARTICLE_AGE_HOURS."""
    if MAX_ARTICLE_AGE_HOURS <= 0 or published_at is None:
        return False
    age = datetime.now(tz=timezone.utc) - published_at
    return age.total_seconds() > MAX_ARTICLE_AGE_HOURS * 3600


def _parse_entry(entry, source_name: str) -> Optional[Article]:
    article_id = entry.get("id") or entry.get("link") or entry.get("title")
    if not article_id:
        return None

    title = _clean_text(entry.get("title") or "")
    link = (entry.get("link") or "").strip()
    if not title or not link:
        return None

    published_at = _parse_date(entry)

    if _is_too_old(published_at):
        return None

    raw_html = ""
    content = getattr(entry, "content", None)
    if content:
        raw_html = content[0].get("value", "")
    if not raw_html:
        raw_html = getattr(entry, "summary", "") or ""

    summary = summarize(title, _truncate(_clean_text(raw_html), 500))
    canonical_url = canonicalize_url(link)
    title_key = normalize_title(title)
    content_hash = article_content_hash(title, summary)

    if TRANSLATE_TO_PERSIAN:
        title = translate_to_persian(title)
        summary = translate_to_persian(summary)

    image_url = _extract_image(entry)

    return Article(
        id=article_id,
        source=source_name,
        title=title,
        url=link,
        summary=summary,
        image_url=image_url,
        published_at=published_at,
        canonical_url=canonical_url,
        title_key=title_key,
        content_hash=content_hash,
    )


def fetch_feed(source_name: str, url: str) -> List[Article]:
    articles: List[Article] = []
    try:
        feed = feedparser.parse(url, agent="CulersHubBot/1.0")
        if feed.bozo and not feed.entries:
            logger.warning("Feed parse error [%s]: %s", source_name, feed.bozo_exception)
            return articles
        for entry in feed.entries:
            article = _parse_entry(entry, source_name)
            if article:
                articles.append(article)
        logger.info("Fetched %d articles from %s", len(articles), source_name)
        return articles
    except Exception:
        logger.exception("Unexpected error fetching feed [%s] %s", source_name, url)
    return articles


def fetch_all() -> List[Article]:
    all_articles: List[Article] = []
    for feed_cfg in FEEDS:
        articles = fetch_feed(feed_cfg["name"], feed_cfg["url"])
        all_articles.extend(articles)
    return all_articles
