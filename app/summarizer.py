"""
LLM-powered summarizer using the local llama-server (llama.cpp OpenAI-compatible API).
Falls back to the original RSS excerpt if the LLM call fails.
"""

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:9000")
LLM_ENABLED = os.getenv("LLM_ENABLED", "true").lower() in ("1", "true", "yes")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))

_SYSTEM_PROMPT = (
    "You are a concise football news assistant. "
    "Given a news article title and excerpt, write a clean 2–3 sentence summary "
    "in English. Be factual and neutral. Do not add opinions or speculation. "
    "Do not repeat the title. Output only the summary, nothing else."
)


def summarize(title: str, original_excerpt: str) -> str:
    """
    Generate a 2–3 sentence LLM summary of the article.
    Returns the original excerpt unchanged if LLM is disabled or the call fails.
    """
    if not LLM_ENABLED:
        return original_excerpt

    user_msg = f"Title: {title}\n\nExcerpt: {original_excerpt}"

    payload = {
        "model": "local",
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ],
        "max_tokens": 120,
        "temperature": 0.3,
        "stream": False,
    }

    try:
        resp = requests.post(
            f"{LLM_BASE_URL}/v1/chat/completions",
            json=payload,
            timeout=LLM_TIMEOUT,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        if text:
            return text
        logger.warning("LLM returned empty summary, using original excerpt")
    except Exception as exc:
        logger.warning("LLM summarization failed (%s), using original excerpt", exc)

    return original_excerpt
