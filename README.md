# Culers Hub

A self-hosted Telegram bot that tracks Barca news from RSS feeds and posts updates to a Telegram channel.

## What it does

Every `CHECK_INTERVAL_MINUTES`, the bot:

1. Fetches all configured feeds from `feeds.yaml`.
2. Cleans and summarizes articles (optional local LLM).
3. Deduplicates by previously sent IDs and cross-source title similarity.
4. Sends new items to Telegram with image when available.

## Requirements

- Docker + Docker Compose
- Telegram bot token from @BotFather
- Telegram channel/group where bot is admin
- Optional llama.cpp server for summaries

## Setup

1. Copy env file:

```bash
cp .env.example .env
```

2. Fill required vars in `.env`:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

3. Start bot:

```bash
docker compose up -d --build
```

4. Watch logs:

```bash
docker compose logs -f rss-bot
```

## Configuration

Key variables in `.env`:

- `CHECK_INTERVAL_MINUTES` default `30`
- `MAX_ARTICLE_AGE_HOURS` default `1` (`0` disables age filter)
- `SEND_INTERVAL_SECONDS` default `60`
- `LLM_ENABLED` default `true`
- `LLM_BASE_URL` default `http://localhost:9000`
- `LLM_TIMEOUT` default `30`

## Feeds

Edit `feeds.yaml` and restart the container to change sources.

## Project layout

```text
culers-hub/
├── app/
│   ├── config.py
│   ├── storage.py
│   ├── feed_fetcher.py
│   ├── summarizer.py
│   ├── telegram_sender.py
│   └── main.py
├── feeds.yaml
├── prompt.yaml
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```
