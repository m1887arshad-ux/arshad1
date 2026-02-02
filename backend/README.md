# Bharat Biz-Agent Backend (PS-2)

**Central authority** connecting: **Telegram** (user interaction), **Owner Website** (approval & control), **Database** (source of truth).

## Problem in simple words (PS-2)

Small business owners get requests over WhatsApp/Telegram (e.g. “Rahul ko 500 ka bill bana do”). They want an **agent** that turns these into **actions** (e.g. draft invoice) but **never executes** without owner approval. This backend:

- Receives commands from **Telegram**
- Converts them into **structured action drafts** (rule-based, no AI)
- Stores drafts in the **database**
- Exposes drafts to the **Owner Website**
- **Executes** actions **only after** the owner approves

So: **Draft → Approve → Execute**. No autonomy. Trust-first.

## Why Telegram is used

Telegram is the **input channel** for business commands (e.g. Hinglish “500 ka invoice Rahul”). The backend parses these with **rule-based patterns** (regex/keywords), creates a **DRAFT** action, and replies: “Action drafted. Please approve from Owner Dashboard.” The owner then approves or rejects on the Owner Website. Execution (e.g. creating the invoice) happens only after approval.

## Draft → Approve → Execute flow

1. **Telegram**: User sends e.g. “Rahul ko 500 ka bill bana do”.
2. **Backend**: Rule-based parser extracts intent + entities → creates `AgentAction` with status `DRAFT`.
3. **Owner Website**: Owner sees “Recent Agent Actions”, clicks **Review** → sees details → **Approve** or **Reject**.
4. **Backend**: On **Approve**, backend executes (e.g. create invoice, update ledger) and sets status `EXECUTED`. On **Reject**, status `REJECTED`; no DB change.
5. All actions are **logged** for trust and visibility.

## Why this is NOT a chatbot

This is **not** a conversational AI. There is **no LLM, no AI**. The “agent” is **rule-based** only: it matches patterns (e.g. “X ko Y ka bill”) and creates a structured draft. No autonomy: **every** action requires owner approval. The backend is a **control panel bridge**: Telegram in, drafts out, owner decides, then execution.

## How trust & safety is enforced

- **JWT authentication** for Owner Website; only the owner can approve/reject.
- **No execution from Telegram**; Telegram only creates DRAFTs.
- **Owner approval required** for every action; no silent execution.
- **All actions logged** in DB (status: DRAFT / APPROVED / REJECTED / EXECUTED).
- **Permission checks**: only the business owner can approve actions for their business.
- **Clear comments** in code where safety/trust decisions are made.

## Tech stack

- **FastAPI** (Python)
- **SQLAlchemy** ORM, **SQLite** (local-first, hackathon-safe)
- **JWT** authentication
- **python-telegram-bot**
- **Docker** (mandatory)

## Run locally (without Docker)

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Unix: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000  
- Docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health

**Telegram**: Set `TELEGRAM_BOT_TOKEN` in env (from BotFather). If unset, the app still runs; the bot is simply not started.

**Database**: SQLite file `./bharat.db` is created on first run. Delete to reset.

## Demo Steps (Fresh Start)

1. **Delete `bharat.db`** (if exists) to start fresh
2. **Start backend**: `uvicorn app.main:app --reload --port 8000`
3. **Start frontend**: `cd owner-frontend && npm run dev`
4. **Register**: Go to http://localhost:3000 → Click "Create account" → Enter email/password
5. **Login**: Use credentials to log in
6. **Setup Business**: Complete the 3-step wizard (Business name, Owner name, Language)
7. **Dashboard**: See "Human Approval Required" message, empty actions list
8. **Create Test Action** (via Telegram or API):
   - Telegram: Send "Rahul ko 500 ka bill bana do" to your bot
   - API: POST to `/agent/actions` (or use Swagger)
9. **Review Action**: Dashboard shows pending action → Click "Review"
10. **Approve/Reject**: Confirm approval → Action executed → Invoice created
11. **Check Records**: Navigate to Records → See invoice in list

## Full stack (frontend + backend)

1. Start backend: `cd backend && uvicorn app.main:app --reload --port 8000`
2. Start Owner frontend: `cd owner-frontend && npm run dev`
3. Open http://localhost:3000 → Login (register first) → Setup business → Dashboard. Frontend calls backend at `http://localhost:8000` (set `NEXT_PUBLIC_API_URL` in frontend if needed).

## Run with Docker

```bash
cd backend
docker build -t bharat-backend .
docker run -p 8000:8000 -e TELEGRAM_BOT_TOKEN=your_token -e SECRET_KEY=your_secret bharat-backend
```

Optional: mount a volume for DB persistence:

```bash
docker run -p 8000:8000 -v $(pwd)/data:/app -e TELEGRAM_BOT_TOKEN=your_token bharat-backend
```

(Ensure `DATABASE_URL` points to a path inside `/app` if you mount data.)

## API summary (Owner Website)

| Method | Endpoint | Description |
|--------|----------|--------------|
| POST | /auth/register | Register owner (email, password) |
| POST | /auth/login | Login → JWT |
| GET | /auth/me | Current user (Bearer JWT) |
| POST | /business/setup | Create/update business |
| GET | /business | Get business |
| GET | /agent/actions | Recent agent actions |
| GET | /agent/actions/{id} | Action detail |
| POST | /agent/actions/{id}/approve | Approve → execute |
| POST | /agent/actions/{id}/reject | Reject |
| GET | /records/invoices | Invoices (read-only) |
| GET | /records/ledger | Ledger (read-only) |
| GET | /records/inventory | Inventory (read-only) |

## AI future hooks (comment only)

In `app/agent/intent_parser.py` a comment states:  
*“LLM-based Hinglish understanding will be added here later.”*  
No AI libraries are imported; no models are loaded. The backend is **hackathon-ready** and runs without AI.
