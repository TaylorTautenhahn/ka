FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DB_PATH=/data/recruitment.db \
    SESSION_COOKIE_SECURE=1 \
    SESSION_COOKIE_SAMESITE=strict

WORKDIR /app

RUN adduser --disabled-password --gecos '' appuser

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY README.md ./README.md

RUN mkdir -p /data && chown -R appuser:appuser /data /app
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
