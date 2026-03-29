import sqlite3
import logging

from config import DB_PATH


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sent_articles (
                id TEXT PRIMARY KEY,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    logging.info("Database ready at %s", DB_PATH)


def is_sent(article_id: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT 1 FROM sent_articles WHERE id = ?", (article_id,))
        return cur.fetchone() is not None


def mark_sent(article_id: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR IGNORE INTO sent_articles (id) VALUES (?)", (article_id,))
        conn.commit()
