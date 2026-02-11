# KAO Rush Evaluation Web App

Production-focused recruitment evaluation platform with multi-organization support.

The app replaces spreadsheets with role-based visibility, accountability, meeting-ready context, and connected real-time updates across PNMs, members, ratings, lunches, photos, phone numbers, and officer assignments.

## Core Capabilities
- Individual authentication with Head Rush Officer approval workflow.
- Public self-registration limited to new Rush Officers using username + access code (emoji optional; PNM creation is post-login only).
- Multi-tenant organizations by URL path:
  - `/kappaalphaorder`
  - `/<org-slug>/meeting`
  - isolated SQLite DB + uploads per organization
- Platform admin console at `/platform` for:
  - creating organizations
  - assigning branding colors + logos
  - seeding tenant-specific Head login credentials
  - disabling tenant workspaces
- Role-aware visibility:
  - Head Rush Officer / Rush Officer can see rating ownership, comments, and deltas.
  - Rushers see overall PNM averages and only their own rating stats.
- Linked data integrity:
  - One active rating per member/PNM.
  - Rating updates require comment > 5 words.
  - Last-change-only tracking in `rating_changes`.
  - Lunch dedupe by `(pnm_id, user_id, lunch_date)`.
- Real-time propagation on write:
  - PNM weighted totals and category averages.
  - Member rating averages.
  - Member + PNM lunch stats.
- PNM photos (JPG/PNG/WEBP) with upload validation.
- PNM phone number tracking.
- Head-only assignment of PNMs to specific Rush Officers.
- Meeting View packet per rushee:
  - profile + photo
  - weighted summary and rating spread
  - lunch timeline
  - recommended member matches by shared interests/stereotype
- Admin Panel (Head only): remove rushees with safe cascading cleanup.
- Dedicated Meeting page tab with print-to-PDF workflow.
- Mobile route set with separate pages (not a long single scroll):
  - `/<org-slug>/mobile`
  - `/<org-slug>/mobile/pnms`
  - `/<org-slug>/mobile/create`
  - `/<org-slug>/mobile/members`
  - `/<org-slug>/mobile/meeting`
- iPhone contact export for PNMs as `.vcf` including name, phone, photo, and org field `PNM (<Fraternity Name>)`.
- Manual backup exports:
  - CSV archive export (zip)
  - SQLite snapshot export

## Security Hardening
- PBKDF2-SHA256 password hashing with per-user salt.
- Legacy hash upgrade path on successful login.
- Login rate limiting with temporary IP lockout.
- Session idle timeout enforcement.
- Security headers (CSP, HSTS on HTTPS, X-Frame-Options, etc.).
- Trusted host middleware support.
- API responses bypass service worker cache to prevent stale data.

## Long-Term Data Durability
- SQLite configured with WAL mode and busy timeout.
- Backup directory with rotating startup/manual snapshots.
- Production recommendation: persistent disk mount for database and uploads.

## Stack
- FastAPI
- SQLite
- Vanilla HTML/CSS/JavaScript
- PWA manifest + service worker
- Docker deployment support

## Data Model
- `users`
- `pnms`
- `ratings`
- `rating_changes`
- `lunches`
- `sessions`

## Local Run
1. Create and activate virtualenv:

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

## Seed Account Behavior
Head seed account is environment-driven and production-safe:
- No personal credentials are displayed in UI.
- If `HEAD_SEED_ACCESS_CODE` is not set on a fresh DB, a random bootstrap code is generated and printed once in startup logs.
- Existing seed user passwords are not overwritten unless `HEAD_SEED_ACCESS_CODE` is explicitly set.

## Docker Deploy (Recommended)

```bash
docker build -t kao-rush-app .
docker run -p 8000:8000 \
  -e SESSION_COOKIE_SECURE=1 \
  -e SESSION_COOKIE_SAMESITE=strict \
  -e HEAD_SEED_USERNAME=head.rush.officer \
  -e HEAD_SEED_ACCESS_CODE='set-a-strong-secret' \
  -e DB_PATH=/data/recruitment.db \
  -e UPLOADS_DIR=/data/uploads \
  -v $(pwd)/data:/data \
  kao-rush-app
```

## Render Deploy Notes
- `render.yaml` included.
- Add persistent disk mounted at `/data`.
- Set env vars:
  - `HEAD_SEED_ACCESS_CODE` (required secret)
  - `DB_PATH=/data/recruitment.db`
  - `UPLOADS_DIR=/data/uploads`
  - `SESSION_COOKIE_SECURE=1`
  - `ALLOWED_HOSTS=<your-domain>`
  - `PLATFORM_ADMIN_ACCESS_CODE=<strong-secret>`

## Environment Variables
- `DB_PATH` (default `app/recruitment.db`)
- `UPLOADS_DIR` (default `app/uploads`)
- `BACKUP_DIR` (default `app/uploads/backups`)
- `MAX_BACKUP_FILES` (default `30`)
- `MAX_PNM_PHOTO_BYTES` (default `4194304`)
- `SESSION_TTL_SECONDS` (default `43200`)
- `SESSION_COOKIE_SECURE` (default `0`; set `1` on HTTPS)
- `SESSION_COOKIE_SAMESITE` (default `strict`)
- `ALLOWED_HOSTS` (default `*`)
- `PASSWORD_ITERATIONS` (default `260000`)
- `LOGIN_WINDOW_SECONDS` (default `300`)
- `LOGIN_MAX_FAILURES` (default `8`)
- `LOGIN_BLOCK_SECONDS` (default `600`)
- `PLATFORM_DB_PATH` (default `<db-dir>/platform.db`)
- `TENANTS_DB_DIR` (default `<db-dir>/tenants`)
- `DEFAULT_TENANT_SLUG` (default `kappaalphaorder`)
- `DEFAULT_TENANT_NAME` (default `Kappa Alpha Order`)
- `PLATFORM_ADMIN_USERNAME` (default `taylortaut`)
- `PLATFORM_ADMIN_ACCESS_CODE` (no default)
- `AUTO_CREATE_HEAD_SEED` (default `1`)
- `HEAD_SEED_USERNAME` (default `head.rush.officer`)
- `HEAD_SEED_ACCESS_CODE` (no default)
- `HEAD_SEED_FIRST_NAME` (default `Head`)
- `HEAD_SEED_LAST_NAME` (default `Officer`)
- `HEAD_SEED_PLEDGE_CLASS` (default `Admin`)

## API Endpoints (High-Level)
Tenant-scoped endpoints are available at:
- `/<org-slug>/api/...` (recommended)
- `/api/...` (defaults to `DEFAULT_TENANT_SLUG`)

Tenant APIs:
- `POST /<org-slug>/api/auth/register`
- `POST /<org-slug>/api/auth/login`
- `POST /<org-slug>/api/auth/logout`
- `GET /<org-slug>/api/auth/me`
- `GET /api/users`
- `PATCH /api/users/me`
- `GET /api/users/pending` (Head only)
- `POST /api/users/pending/{user_id}/approve` (Head only)
- `POST /api/pnms`
- `GET /api/pnms`
- `GET /api/pnms/{pnm_id}`
- `POST /api/pnms/{pnm_id}/assign` (Head only)
- `POST /api/pnms/{pnm_id}/photo` (Officer+)
- `GET /api/pnms/{pnm_id}/meeting`
- `DELETE /api/pnms/{pnm_id}` (Head only)
- `POST /api/ratings`
- `GET /api/pnms/{pnm_id}/ratings`
- `POST /api/lunches`
- `GET /api/pnms/{pnm_id}/lunches`
- `GET /api/matching`
- `GET /api/analytics/overview`
- `GET /api/interests`
- `GET /api/export/csv` (Head only)
- `GET /api/export/sqlite` (Head only)
- `GET /api/export/contacts.vcf`
- `GET /health`

Platform admin APIs:
- `POST /platform/api/auth/login`
- `POST /platform/api/auth/logout`
- `GET /platform/api/auth/me`
- `GET /platform/api/tenants`
- `POST /platform/api/tenants`
- `POST /platform/api/tenants/{slug}/logo`
- `DELETE /platform/api/tenants/{slug}`
