import sqlite3
import logging
from typing import Optional

from config import DB_PATH


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sent_articles (
                id TEXT PRIMARY KEY,
                canonical_url TEXT,
                title_key TEXT,
                content_hash TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _ensure_columns(conn)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sent_articles_canonical_url ON sent_articles(canonical_url)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sent_articles_title_key ON sent_articles(title_key)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sent_articles_content_hash ON sent_articles(content_hash)"
        )
        conn.commit()
    logging.info("Database ready at %s", DB_PATH)


def _ensure_columns(conn: sqlite3.Connection) -> None:
    """Best-effort migration for DBs created before dedup fingerprint columns existed."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(sent_articles)")}

    if "canonical_url" not in existing:
        conn.execute("ALTER TABLE sent_articles ADD COLUMN canonical_url TEXT")
    if "title_key" not in existing:
        conn.execute("ALTER TABLE sent_articles ADD COLUMN title_key TEXT")
    if "content_hash" not in existing:
        conn.execute("ALTER TABLE sent_articles ADD COLUMN content_hash TEXT")


def is_sent(article_id: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT 1 FROM sent_articles WHERE id = ?", (article_id,))
        return cur.fetchone() is not None


def is_sent_by_url(canonical_url: Optional[str]) -> bool:
    if not canonical_url:
        return False
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT 1 FROM sent_articles WHERE canonical_url = ?",
            (canonical_url,),
        )
        return cur.fetchone() is not None


def is_sent_by_title_key(title_key: Optional[str]) -> bool:
    if not title_key:
        return False
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT 1 FROM sent_articles WHERE title_key = ?",
            (title_key,),
        )
        return cur.fetchone() is not None


def is_sent_by_content_hash(content_hash: Optional[str]) -> bool:
    if not content_hash:
        return False
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT 1 FROM sent_articles WHERE content_hash = ?",
            (content_hash,),
        )
        return cur.fetchone() is not None


def mark_sent(
    article_id: str,
    canonical_url: Optional[str] = None,
    title_key: Optional[str] = None,
    content_hash: Optional[str] = None,
) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO sent_articles (id, canonical_url, title_key, content_hash)
            VALUES (?, ?, ?, ?)
            """,
            (article_id, canonical_url, title_key, content_hash),
        )
        conn.commit()
