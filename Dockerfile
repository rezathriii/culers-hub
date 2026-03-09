FROM python:3.12-slim

RUN addgroup --system bot && adduser --system --ingroup bot bot

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

COPY feeds.yaml /app/feeds.yaml

RUN mkdir -p /data && chown bot:bot /data

USER bot

CMD ["python", "main.py"]
