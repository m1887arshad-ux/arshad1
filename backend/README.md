# Bharat Biz-Agent Backend (PS-2)

> **Intelligent business assistant** for Indian SMBs — Hinglish voice-to-action via Telegram, with human-in-the-loop safety.

---

## 🎯 90-Second Demo Flow

```
1. Open Telegram, find your bot
2. Send: "Rahul ko 10 Paracetamol"
3. Bot asks: "Confirm invoice for Rahul - 10 Paracetamol = ₹60?"
4. Reply: "confirm"
5. Bot: "✅ Invoice DRAFT created! Approve from Dashboard."
6. Open Owner Dashboard (localhost:3000)
7. Click "Approve" on the pending action
8. Invoice is now EXECUTED and recorded
```

**Key insight**: The agent NEVER executes without owner approval. This is the "trust-first" architecture.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BHARAT BIZ-AGENT                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐ │
│  │  TELEGRAM   │───▶│     FSM     │───▶│    DECISION ENGINE      │ │
│  │   (Input)   │    │ (Stateful)  │    │  (Creates DRAFT only)   │ │
│  └─────────────┘    └──────┬──────┘    └───────────┬─────────────┘ │
│                            │                       │                │
│                    ┌───────▼───────┐               │                │
│                    │   GROQ LLM    │               │                │
│                    │ (Hinglish→    │               │                │
│                    │  Intent ONLY) │               │                │
│                    └───────────────┘               │                │
│                                                    │                │
│  ┌─────────────────────────────────────────────────▼──────────────┐│
│  │                         DATABASE                               ││
│  │  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────────┐ ││
│  │  │ Invoices │ │  Ledger  │ │ Inventory │ │   AgentAction    │ ││
│  │  │          │ │          │ │           │ │  status: DRAFT   │ ││
│  │  └──────────┘ └──────────┘ └───────────┘ └────────┬─────────┘ ││
│  └───────────────────────────────────────────────────┼────────────┘│
│                                                      │             │
│  ┌───────────────────────────────────────────────────▼───────────┐ │
│  │                    OWNER DASHBOARD                            │ │
│  │                                                               │ │
│  │    [📋 Pending Actions]  ──▶  [✅ APPROVE] / [❌ REJECT]     │ │
│  │                                      │                        │ │
│  │                                      ▼                        │ │
│  │                              ┌─────────────┐                  │ │
│  │                              │  EXECUTOR   │                  │ │
│  │                              │ (Runs ONLY  │                  │ │
│  │                              │  after      │                  │ │
│  │                              │  approval)  │                  │ │
│  │                              └─────────────┘                  │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                 PROACTIVE AGENT (Background)                  │ │
│  │  Scans ledger for overdue payments → Creates DRAFT reminders  │ │
│  │  (Owner must approve before any reminder is sent)             │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Safety Model: Draft → Approve → Execute

**THIS IS THE CORE INNOVATION.**

```
                     AI/LLM
                       │
                       ▼
            ┌─────────────────────┐
            │    INTENT ONLY      │  ← LLM extracts what user wants
            │  (No execution)     │
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │   CREATE DRAFT      │  ← Decision Engine validates
            │  AgentAction.DRAFT  │
            └──────────┬──────────┘
                       │
          ═════════════▼═════════════  ← HUMAN APPROVAL GATE
                       │
            ┌─────────────────────┐
            │   OWNER REVIEWS     │  ← Dashboard shows pending
            │   [APPROVE/REJECT]  │
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │      EXECUTE        │  ← Executor runs ONLY after approval
            │  (Update DB, etc.)  │
            └─────────────────────┘
```

**Why this matters:**
- AI hallucinations can't cause financial damage
- Prompt injection attacks can't trigger execution
- Owner maintains full control over all actions
- Full audit trail of all proposed and executed actions

---

## 🤖 FSM vs LLM: The Hybrid Approach

### Why FSM First?

| Aspect | FSM (Finite State Machine) | LLM (Groq) |
|--------|---------------------------|------------|
| Speed | <1ms | 300-2000ms |
| Reliability | 100% deterministic | Probabilistic |
| Cost | Free | API calls |
| Handles | Known patterns | Ambiguous Hinglish |

**Our approach:**
1. FSM handles multi-step flows (invoice creation)
2. LLM extracts intent from ambiguous messages
3. FSM manages conversation state (persisted to DB)
4. LLM output is VALIDATED before use

### FSM State Persistence

```python
# OLD (BROKEN): In-memory state lost on restart
FSM_STATE: Dict[int, dict] = {}  # ❌ Lost on server restart

# NEW (FIXED): Database-persisted state
class ConversationState(Base):  # ✅ Survives restarts
    chat_id = Column(String, unique=True)
    state = Column(String)  # "await_product", "await_quantity", etc.
    payload = Column(JSON)  # {"product": "Paracetamol", "quantity": 10}
```

### LLM Role: Intent Planner ONLY

```python
# What LLM does:
{
    "intent": "create_invoice",  # ← Extracted
    "product": "Paracetamol",    # ← Extracted
    "quantity": 10,              # ← Extracted
    "customer": "Rahul"          # ← Extracted
}

# What LLM does NOT do:
- Execute database operations
- Send messages to users
- Make financial decisions
- Access external services
```

---

## 💊 Pharmacy-Specific Features

### Prescription Compliance

```python
class Inventory(Base):
    item_name = Column(String)
    quantity = Column(Numeric)
    price = Column(Numeric)
    requires_prescription = Column(Boolean, default=False)  # ← COMPLIANCE
    disease = Column(String)  # What it treats
```

**Compliance enforcement:**
- If `requires_prescription=True`:
  - Invoice DRAFT is flagged with ⚠️ warning
  - Owner MUST verify prescription exists
  - This is a LEGAL requirement for controlled medicines

### Proactive Payment Reminders

```python
# Background scheduler (runs hourly)
async def scan_and_create_reminders():
    """
    Scans ledger for customers with unpaid invoices >30 days.
    Creates DRAFT reminder actions (NOT executed automatically).
    Owner reviews and approves reminders from Dashboard.
    """
```

**Example output:**
```
📋 Payment Reminder DRAFT Created
Customer: Ramesh
Overdue Amount: ₹1,500
Days Overdue: 45

[Approve Reminder] [Reject]
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend)
- Telegram Bot Token (from @BotFather)
- Groq API Key (free at console.groq.com)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your keys:
# - TELEGRAM_BOT_TOKEN=your_telegram_token
# - GROQ_API_KEY=your_groq_key

# Initialize database with sample data
python -c "from app.db.init_db import init_db; init_db()"

# Run server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd owner-frontend

# Install dependencies
npm install

# Run development server
npm run dev
# Opens at http://localhost:3000
```

### Link Telegram

1. Open Telegram, find your bot
2. Send `/start`
3. Note your Chat ID
4. In Dashboard → Settings → Add Chat ID
5. Now you can send commands!

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── agent/
│   │   ├── decision_engine.py    # Creates DRAFTs (never executes)
│   │   ├── executor.py           # Runs ONLY after approval
│   │   ├── intent_parser.py      # Rule-based parsing
│   │   └── proactive_scheduler.py # Background payment reminders
│   ├── api/routes/
│   │   ├── agent.py              # Approve/reject endpoints
│   │   ├── records.py            # Invoice/ledger APIs
│   │   └── settings.py           # Business config
│   ├── models/
│   │   ├── agent_action.py       # DRAFT → APPROVED → EXECUTED
│   │   ├── conversation_state.py # FSM persistence (NEW)
│   │   ├── inventory.py          # Stock + prescription flag
│   │   └── ...
│   ├── telegram/
│   │   ├── bot.py                # Telegram connection
│   │   └── handlers.py           # FSM-first message handling
│   └── main.py                   # FastAPI app + scheduler
├── ai/
│   ├── groq_client.py            # Groq API wrapper
│   ├── intent_parser.py          # LLM intent extraction
│   ├── prompts.py                # System prompts (constrained)
│   └── fallback.py               # Keyword fallback
└── requirements.txt
```

---

## 🔒 Security Considerations

| Threat | Mitigation |
|--------|------------|
| Prompt Injection | LLM output validated against Pydantic schema |
| Unauthorized Execution | JWT auth + owner approval required |
| Data Leakage | No sensitive data in LLM prompts |
| Session Hijacking | Chat ID verified per business |
| Replay Attacks | Actions have unique IDs + timestamps |

---

## 📊 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/agent/approve/{id}` | Approve DRAFT action |
| POST | `/api/agent/reject/{id}` | Reject DRAFT action |
| GET | `/api/agent/pending` | List pending DRAFTs |
| GET | `/api/records/invoices` | List invoices |
| GET | `/api/records/ledger` | List ledger entries |
| GET | `/api/settings/inventory` | Get stock levels |

---

## 🧪 Testing the Flow

### Test 1: Stock Check (No Approval Needed)
```
Telegram: "Paracetamol hai?"
Bot: "✅ Paracetamol: 500 units available"
```

### Test 2: Invoice Creation (Approval Needed)
```
Telegram: "Rahul ko 10 Dolo 650"
Bot: "📋 Invoice Summary
     Customer: Rahul
     Product: Dolo 650
     Quantity: 10
     
     'confirm' - Invoice banao
     'cancel' - Band karo"

Telegram: "confirm"
Bot: "✅ Invoice DRAFT created!
     Amount: ₹60.00
     📱 Approve from Owner Dashboard."

Dashboard: Click [Approve]
Bot: Action executed!
```

### Test 3: Prescription Drug
```
Telegram: "Rahul ko 5 Alprazolam"
Bot: "✅ Invoice DRAFT created!
     ⚠️ PRESCRIPTION REQUIRED — Owner must verify
     📱 Approve from Owner Dashboard."

Dashboard: Shows warning, owner verifies prescription, then approves
```

---

## 📝 License

MIT License - Built for PS-2 Hackathon

---

## 🙏 Credits

- **Groq** for free LLM API
- **python-telegram-bot** for Telegram integration
- **FastAPI** for blazing fast APIs
