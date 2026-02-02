# Bharat Biz-Agent — Owner Control Panel

Owner-facing frontend for the Bharat Biz-Agent product. This is the **Owner Control Panel** (not the WhatsApp interface, agent brain, or analytics).

## Tech stack

- **Next.js** (App Router)
- **React** + **TypeScript**
- **Tailwind CSS**
- **Fetch** (no MUI, AntD, or ShadCN)

## Design

- Minimal, trust-first, clarity over beauty
- Table-based layouts, large buttons, calm spacing

## Pages

| Route | Description |
|-------|-------------|
| `/login` | Email + password login (JWT). Register link. Redirects to dashboard if already logged in. |
| `/setup` | Step-based business setup wizard. Calls backend `POST /business/setup`; requires login. |
| `/dashboard` | List of recent agent actions with status badges (Pending / Approved / Executed). Click to view action. |
| `/approve/[id]` | Detailed action approval page. Approve / Reject buttons. No extra UI noise. |
| `/records` | Tabs: Invoices \| Ledger \| Inventory. Simple tables, read-only views. |
| `/settings` | Toggles: Language, Agent enable/disable, Approval requirement (and WhatsApp notifications). |

## Backend integration

- **Fully integrated** with the FastAPI backend in `../backend`.
- `lib/api.ts` uses `fetch()` to `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).
- All requests send `Authorization: Bearer <JWT>` when the user is logged in.
- On 401, the frontend clears the token and redirects to `/login`. On 404 “Business not set up”, redirects to `/setup`.
- Copy `.env.example` to `.env.local` and set `NEXT_PUBLIC_API_URL` if the backend runs on another host/port.

## Folder structure

```
owner-frontend/
├── app/
│   ├── login/page.tsx
│   ├── setup/page.tsx
│   ├── dashboard/page.tsx
│   ├── approve/[id]/page.tsx
│   ├── records/page.tsx
│   └── settings/page.tsx
├── components/
│   ├── Table.tsx
│   ├── ActionCard.tsx
│   ├── StatusBadge.tsx
│   ├── PrimaryButton.tsx
│   └── OwnerShell.tsx
├── lib/
│   └── api.ts
├── styles/
│   └── globals.css
└── README.md
```

## Run locally

1. **Start the backend** (from repo root):
   ```bash
   cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000
   ```
2. **Start the frontend**:
   ```bash
   npm install
   npm run dev
   ```
3. Open [http://localhost:3000](http://localhost:3000). Root redirects to `/login`.
4. **Register** (Create account) or **Log in** with email + password. After login, go to **Setup** if prompted, then **Dashboard**.

## Build

```bash
npm run build
npm start
```

## Demo Walkthrough

1. Open http://localhost:3000
2. Click "Create account" → Enter email/password → Register
3. Login with credentials
4. Complete 3-step business setup wizard
5. Dashboard shows "Human Approval Required" banner
6. When Telegram messages create drafts, they appear as "Pending"
7. Click "Review" on any pending action
8. See action details with confirmation dialog
9. Click "Approve" → Confirm → Action executes
10. Navigate to Records to see created invoices/ledger

## Features

- ✅ Loading states on all pages
- ✅ Empty states when no data
- ✅ Confirmation dialogs for approve/reject
- ✅ Clear status labels (DRAFT/Pending, APPROVED, EXECUTED)
- ✅ Trust messaging ("Human Approval Required")
- ✅ Safety warnings for disabled controls

## Trust & approval

- **Dashboard**: Shows recent agent actions; "Review" only for Pending items (links to `/approve/[id]`).
- **Approve page**: Owner sees action details and agent explanation, then Approve or Reject with confirmation.
- **Settings**: "Require approval for all invoices" shows warning when disabled; all changes logged.
