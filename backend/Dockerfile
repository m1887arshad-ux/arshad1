# Bharat Biz-Agent Backend — Docker (mandatory)
# Exposes port 8000. FastAPI + Telegram bot in same container.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# SQLite DB path (persist via volume if needed)
ENV DATABASE_URL=sqlite:///./bharat.db

EXPOSE 8000

# Run FastAPI with uvicorn; Telegram bot starts inside app lifespan
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
