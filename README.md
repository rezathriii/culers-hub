# Culers Hub – Barça RSS → Telegram Bot

Polls four validated Barça news RSS feeds and pushes new articles to a Telegram channel.  
Each post includes the **source**, **title**, **summary**, and **image** (when available).

## Active feeds

| Source                  | URL                                    |
| ----------------------- | -------------------------------------- |
| Barca Universal         | https://barcauniversal.com/feed        |
| BarcaBlog               | https://barcablog.com/feed             |
| Barcelona Football Blog | https://barcelonafootballblog.com/feed |
| Barca News Network      | https://barcanewsnetwork.com/feed      |

> **Dropped feeds** (verified unavailable 2026-03-05):  
> Barca Blaugranes – both `/rss/current` and `/rss` return 404.  
> All About FC Barcelona – connection error (000).

---

## Quick start

### 1. Create a Telegram bot

1. Message [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token.
2. Add the bot as an **admin** of your channel (it needs permission to post messages).
3. Get your channel's chat ID:
   - Public channel: just use `@your_channel_username`.
   - Private channel: forward any channel message to [@userinfobot](https://t.me/userinfobot) to reveal the numeric ID (looks like `-1001234567890`).

### 2. Configure

```bash
cp .env.example .env
# Edit .env and fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
```

### 3. Deploy with Docker Compose

```bash
docker compose up -d --build
```

Logs:

```bash
docker compose logs -f
```

Stop:

```bash
docker compose down
```

---

## Configuration (`.env`)

| Variable                 | Required | Default | Description                  |
| ------------------------ | -------- | ------- | ---------------------------- |
| `TELEGRAM_BOT_TOKEN`     | ✅       | –       | Bot token from @BotFather    |
| `TELEGRAM_CHAT_ID`       | ✅       | –       | `@channelname` or numeric ID |
| `CHECK_INTERVAL_MINUTES` | ❌       | `30`    | How often to poll feeds      |

---

## Project layout

```
culers-hub/
├── app/
│   ├── config.py           # Env-var config + feed list
│   ├── storage.py          # SQLite deduplication
│   ├── feed_fetcher.py     # RSS parsing (title, summary, image)
│   ├── telegram_sender.py  # Telegram Bot API
│   └── main.py             # Scheduler loop
├── data/                   # Persisted DB (Docker volume)
├── .env                    # Your secrets (not committed)
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## How it works

1. On startup the bot verifies the Telegram token with `getMe`.
2. Every `CHECK_INTERVAL_MINUTES` it fetches all four feeds.
3. Each article is checked against a local SQLite database; already-sent articles are skipped.
4. New articles are sent to the channel:
   - **With image** → `sendPhoto` with caption (source + title + summary + link).
   - **Without image** → `sendMessage` with HTML-formatted text.
5. Sent article IDs are stored so they are never posted again.
