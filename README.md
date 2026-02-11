# KAO Rush Evaluation Web App

Production-oriented recruitment evaluation platform for Kappa Alpha Order.

This app replaces spreadsheet workflows with role-based visibility, accountability, and connected real-time updates across PNMs, members, ratings, and lunches.

## What You Asked For
- Website-first architecture
- Easy deployment
- Mobile-friendly PWA installability
- Strong security defaults
- High-quality design and animation
- Real-time linked data behavior

## Implemented Capabilities
- Individual authentication with session cookies
- Head Rush Officer approval flow for new usernames
- Seeded Head Rush Officer account:
  - Username: `taylortaut`
  - Password: `Ttest123`
  - Configurable through environment variables
- Role visibility rules:
  - Head Rush Officer / Rush Officer can see who rated PNMs, comments, and deltas
  - Rushers can see PNM averages and only their own rating averages
- Data constraints:
  - One active rating per member per PNM
  - Rating updates require comment > 5 words
  - Last-change-only tracking (`rating_changes`)
  - Duplicate lunch prevention by `(member, pnm, date)`
- Auto-propagated updates on writes:
  - PNM weighted and category averages
  - Member rating averages
  - Member and PNM lunch stats
- Filtering and matching for PNMs + members:
  - Interest (ANY)
  - Stereotype
  - Combined
- PNM photo uploads (JPG/PNG/WEBP) with secure size/type validation
- Meeting View packet for any single rushee:
  - Profile + photo
  - Weighted snapshot
  - Ratings summary/history
  - Lunch timeline
  - Best member-fit matches by shared interests/stereotype
- Admin panel (Head Rush Officer): remove rushees safely
  - Cascades ratings/lunches for deleted rushees
  - Recalculates impacted member stats automatically
- Interest validation:
  - One word
  - No spaces
  - First letter uppercase (stored canonical + normalized)
- PNM code generation + dynamic days-since-first-event
- Installable PWA (manifest + service worker)
- Refined UI with animated counters, score bars, reveal transitions, selection states, and positive-delta celebration animation

## Security Hardening Included
- Password hashing: PBKDF2-SHA256 with per-user random salt
- Legacy hash upgrade on successful login (for compatibility)
- Login rate limiting by IP with temporary block window
- Session expiration enforcement with idle timeout (`SESSION_TTL_SECONDS`)
- HttpOnly cookie sessions
- Optional secure cookies via env (`SESSION_COOKIE_SECURE=1`)
- Strict/controlled SameSite cookie setting
- Response security headers:
  - Content-Security-Policy
  - HSTS (on HTTPS)
  - X-Frame-Options
  - X-Content-Type-Options
  - Referrer-Policy
  - Permissions-Policy
- Trusted host middleware support via `ALLOWED_HOSTS`
- Service worker bypasses `/api/*` caching to preserve data freshness

## Tech Stack
- FastAPI
- SQLite
- Vanilla HTML/CSS/JavaScript
- PWA manifest + service worker
- Docker-ready

## Data Model
- `users`
- `pnms`
- `ratings`
- `rating_changes`
- `lunches`
- `sessions`

## Local Run
1. Create and activate venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run app:

```bash
uvicorn app.main:app --reload
```

4. Open:

```text
http://127.0.0.1:8000
```

## Docker Deploy (Recommended)

Build and run:

```bash
docker build -t kao-rush-app .
docker run -p 8000:8000 \
  -e SESSION_COOKIE_SECURE=1 \
  -e SESSION_COOKIE_SAMESITE=strict \
  -e HEAD_SEED_USERNAME=taylortaut \
  -e HEAD_SEED_ACCESS_CODE=Ttest123 \
  -v $(pwd)/data:/data \
  kao-rush-app
```

Open `http://127.0.0.1:8000`.

## One-Click Style Platform Deploy
- `render.yaml` is included for Render deployment.
- `Procfile` is included for platforms that detect process commands.

## Environment Variables
- `DB_PATH` (default `app/recruitment.db` locally; Docker default `/data/recruitment.db`)
- `UPLOADS_DIR` (default `app/uploads` locally)
- `MAX_PNM_PHOTO_BYTES` (default `4194304` = 4MB)
- `SESSION_TTL_SECONDS` (default `43200`)
- `SESSION_COOKIE_SECURE` (`1` in production HTTPS)
- `SESSION_COOKIE_SAMESITE` (`strict`, `lax`, or `none`)
- `ALLOWED_HOSTS` (comma-separated hosts, default `*`)
- `PASSWORD_ITERATIONS` (default `260000`)
- `LOGIN_WINDOW_SECONDS` (default `300`)
- `LOGIN_MAX_FAILURES` (default `8`)
- `LOGIN_BLOCK_SECONDS` (default `600`)
- `HEAD_SEED_USERNAME` (default `taylortaut`)
- `HEAD_SEED_ACCESS_CODE` (default `Ttest123`)
- `HEAD_SEED_FIRST_NAME` (default `Taylor`)
- `HEAD_SEED_LAST_NAME` (default `Taut`)
- `HEAD_SEED_PLEDGE_CLASS` (default `Admin`)

## API Endpoints (High-Level)
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/users`
- `PATCH /api/users/me`
- `GET /api/users/pending` (Head only)
- `POST /api/users/pending/{user_id}/approve` (Head only)
- `POST /api/pnms`
- `POST /api/pnms/{pnm_id}/photo` (Officer+)
- `GET /api/pnms/{pnm_id}/meeting`
- `DELETE /api/pnms/{pnm_id}` (Head only)
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
