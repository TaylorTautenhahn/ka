# KAO Rush Evaluation App

Connected recruitment evaluation web app for Kappa Alpha Order. This replaces spreadsheet workflows with role-based visibility, accountability, and linked real-time scoring/lunch analytics.

## Stack
- FastAPI backend
- SQLite relational database
- HTML/CSS/JavaScript frontend
- PWA support (manifest + service worker)

## Core Behaviors Implemented
- Individual login with approved username format: `First Last - PledgeClass`
- Role model:
  - `Head Rush Officer`
  - `Rush Officer`
  - `Rusher`
- Head-only username approval queue
- Strict self-edit boundaries (no editing/deleting other users' or ratings data)
- PNM model with system `PNM_ID` and generated `PNM_Code`
- Dynamic `days_since_first_event`
- Rating categories and bounds:
  - Good with girls (0-10)
  - Will make it through process (0-10)
  - Personable (0-10)
  - Alcohol control (0-10)
  - Instagram marketability (0-5)
- One active rating per member/PNM
- Rating update rule: changed rating requires comment longer than 5 words
- Last-change tracking (`rating_changes` stores only most recent delta)
- Weighted aggregation (Rush Officer/Head = 0.6, Rusher = 0.4)
- Connected updates on rating write:
  - PNM category averages
  - PNM weighted total
  - Member average rating given
- Lunch logging with dedupe (`member + pnm + date` unique)
- Connected lunch updates:
  - Member total lunches + lunches/week
  - PNM total lunches
- Filtering/matching by interest, stereotype, or both
- Interest validation:
  - one word
  - first letter uppercase
  - no spaces
  - case-normalized matching
- Mobile-friendly and installable PWA-style frontend

## Data Tables
- `users`
- `pnms`
- `ratings`
- `rating_changes`
- `lunches`
- `sessions`

## Seed Account
On first boot, the app seeds a Head Rush Officer account:
- Username: `Head Officer - Admin`
- Access code: `KAO2026`

## Run Locally
1. Create and activate virtualenv:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
uvicorn app.main:app --reload
```

4. Open:

```text
http://127.0.0.1:8000
```

## API Surface (High-Level)
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/users`
- `PATCH /api/users/me`
- `GET /api/users/pending` (Head only)
- `POST /api/users/pending/{user_id}/approve` (Head only)
- `POST /api/pnms`
- `GET /api/pnms`
- `GET /api/pnms/{pnm_id}`
- `POST /api/ratings`
- `GET /api/pnms/{pnm_id}/ratings`
- `POST /api/lunches`
- `GET /api/pnms/{pnm_id}/lunches`
- `GET /api/matching`
- `GET /api/analytics/overview`
- `GET /api/interests`
- `GET /health`

## Notes
- Database file: `app/recruitment.db` (created automatically on startup).
- Excel is treated as seed input only; operational data is in SQLite.
