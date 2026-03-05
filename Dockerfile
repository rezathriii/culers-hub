FROM python:3.12-slim

# Security: run as non-root
RUN addgroup --system bot && adduser --system --ingroup bot bot

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

# Ensure /data is writable by the bot user (volume will be mounted here)
RUN mkdir -p /data && chown bot:bot /data

USER bot

CMD ["python", "main.py"]
