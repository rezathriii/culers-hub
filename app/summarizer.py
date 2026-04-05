"""
LLM-powered summarizer using the local llama-server (llama.cpp OpenAI-compatible API).
Falls back to the original RSS excerpt if the LLM call fails.
"""

import logging
import os
from typing import Optional

import requests
import yaml

logger = logging.getLogger(__name__)

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:9000")
LLM_ENABLED = os.getenv("LLM_ENABLED", "true").lower() in ("1", "true", "yes")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))
LLM_TRANSLATION_ENABLED = os.getenv("LLM_TRANSLATION_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
)
LLM_TRANSLATION_TIMEOUT = int(os.getenv("LLM_TRANSLATION_TIMEOUT", str(LLM_TIMEOUT)))
PROMPT_FILE = os.getenv("PROMPT_FILE", "/app/prompt.yaml")


def _load_system_prompt() -> str:
    """Load system prompt from YAML file with fallback to default."""
    try:
        with open(PROMPT_FILE) as fh:
            data = yaml.safe_load(fh)
            prompt = data.get("system_prompt", "").strip()
            if prompt:
                logger.info(f"Loaded system prompt from {PROMPT_FILE}")
                return prompt
    except Exception as exc:
        logger.warning(f"Failed to load prompt from {PROMPT_FILE}: {exc}. Using default.")

    # Fallback default prompt
    return (
        "You are a knowledgeable football news assistant. "
        "Given a news article title and excerpt, write an informative 4–5 sentence summary "
        "in English that captures the key details and context. "
        "Include the main event, relevant context, key figures involved, and significant developments. "
        "Be factual, balanced, and neutral. Do not add opinions or speculation. "
        "Do not repeat the title verbatim. Output only the summary, nothing else."
    )


_SYSTEM_PROMPT = _load_system_prompt()


def summarize(title: str, original_excerpt: str) -> str:
    """
    Generate a 4–5 sentence LLM summary of the article with detailed context.
    Returns the original excerpt unchanged if LLM is disabled or the call fails.
    """
    if not LLM_ENABLED:
        return original_excerpt

    user_msg = f"Title: {title}\n\nExcerpt: {original_excerpt}"

    payload = {
        "model": "local",
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
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


def translate_to_english(text: str) -> str:
    """
    Translate text to English using the local LLM endpoint.
    Returns original text if translation is disabled or the call fails.
    """
    if not text:
        return text
    if not LLM_TRANSLATION_ENABLED:
        return text

    payload = {
        "model": "local",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a professional translator for football news. "
                    "Translate the user text into fluent natural English. "
                    "Preserve names, numbers, and football entities accurately. "
                    "Do not add explanations. Output only translated text."
                ),
            },
            {"role": "user", "content": text},
        ],
        "max_tokens": 220,
        "temperature": 0.1,
        "stream": False,
    }

    try:
        resp = requests.post(
            f"{LLM_BASE_URL}/v1/chat/completions",
            json=payload,
            timeout=LLM_TRANSLATION_TIMEOUT,
        )
        resp.raise_for_status()
        translated = resp.json()["choices"][0]["message"]["content"].strip()
        if translated:
            return translated
        logger.warning("LLM returned empty translation, using original text")
    except Exception as exc:
        logger.warning("LLM translation failed (%s), using original text", exc)

    return text
