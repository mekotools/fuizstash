# MekoTools-Fuizstash — schlanker Behälter, ein Prozess, SQLite.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AGBLAGE_DATEN=/daten/fuizstash.db \
    FUIZ_KV=/daten/fuiz-kv.db

WORKDIR /opt/fuizstash

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN mkdir -p /daten && useradd -m -u 10001 ablage && chown -R ablage /daten
USER ablage

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/gesundheit', timeout=4).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
