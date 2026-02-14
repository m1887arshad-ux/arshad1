# Bharat Biz-Agent

AI-powered business assistant for Indian SMBs. Manages customer interactions, inventory, invoicing, and ledgers via Telegram in Hinglish.

## Quick Start

```bash
docker build -t bharat-biz .
docker run -p 8000:8000 bharat-biz
```

Access: http://localhost:8000/docs

## Features

- **Conversational AI**: Hinglish (Hindi + English) support
- **Business Operations**: Customer, inventory, invoicing, ledger management
- **Human-in-Loop**: Draft → Approve → Execute pipeline
- **Multi-Channel**: Telegram bot, web dashboard, REST API
- **Security**: JWT auth, rate limiting, encryption

## Tech Stack

- Backend: FastAPI + SQLAlchemy + SQLite
- Frontend: Next.js + TypeScript + Tailwind
- DevOps: Docker + Uvicorn
- AI: Groq/LLaMA + Keyword fallback

## Environment Variables

- `SECRET_KEY` - JWT signing (auto-generated if missing)
- `TELEGRAM_BOT_TOKEN` - Bot integration
- `GROQ_API_KEY` - AI parsing
- `DATABASE_URL` - Database path

All optional; container works without them.

## Running with Env Vars

```bash
docker run -p 8000:8000 \
  -e SECRET_KEY="your-secret-key" \
  -e TELEGRAM_BOT_TOKEN="your-bot-token" \
  -e GROQ_API_KEY="your-groq-key" \
  bharat-biz
```

## Deployment

- Full stack: `docker-compose up -d`
- Single container: `docker run -p 8000:8000 bharat-biz`
- Docs: `DOCKER_DEPLOYMENT.md`

## Development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_server.py
```

## Database

SQLite by default. Schema: Users, Businesses, Customers, Inventory, Invoices, Ledger, AgentActions, ConversationState

## Safety Model

Customer Request → AI Parses Intent → Creates DRAFT → Owner Approves → Execute

**Key**: Agent creates drafts, never executes autonomously.

## Documentation

- Deployment: `DOCKER_DEPLOYMENT.md`
- API: http://localhost:8000/docs (after running)

## Status

✅ Production-ready for hackathon evaluation

