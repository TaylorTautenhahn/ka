# Security Best Practices Audit Report

Date: 2026-02-19
Scope: FastAPI backend (`app/main.py`), vanilla JS frontend (`app/static/js/*`), deployment config (`render.yaml`)

## Executive Summary
The application has solid foundations (parameterized SQL, password hashing with PBKDF2, HttpOnly session cookies, restrictive CSP, and role-based access checks). However, I found one critical data-exposure risk and several high/medium issues that should be addressed before calling the deployment fully secure.

Highest priorities:
1. Prevent backup databases from being reachable via the public `/uploads` static mount.
2. Enforce strict host validation (`ALLOWED_HOSTS`) instead of wildcard.
3. Add CSRF protections for cookie-authenticated state-changing endpoints.

---

## Critical Findings

### SBP-001: Public Backup Database Exposure Through Static Upload Mount
- Rule ID: FASTAPI-FILE-EXPOSURE-001
- Severity: **Critical**
- Location:
  - `app/main.py:63`
  - `app/main.py:67`
  - `app/main.py:308`
  - `app/main.py:1938`
  - `app/main.py:1941`
  - `app/main.py:1973`
  - `app/main.py:4977`
  - `render.yaml:30`
  - `render.yaml:31`
- Evidence:
  - App publicly serves entire uploads tree: `app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")`.
  - Backups are placed under upload-root by config/default:
    - code default: `BACKUP_DIR = ... (UPLOADS_DIR / "backups")`
    - deploy config: `BACKUP_DIR=/data/uploads/backups`
  - DB snapshots are written directly into `active_backup_dir()`.
  - Season archive uses a deterministic filename (`season-archive-latest.sqlite`).
- Impact:
  - Database snapshot files can become web-reachable if path is guessed/disclosed, exposing full recruitment data and hashed credentials.
- Fix:
  - Move backups outside the static upload root (`/data/backups`, not `/data/uploads/backups`).
  - Do not mount full `UPLOADS_DIR`; mount only specific safe subdirectories (e.g., PNM photos/logos) or enforce deny rules for `.sqlite`.
- Mitigation:
  - Immediately rotate any exposed credentials and session tokens if this path was ever accessible.
  - Reduce retention and randomize backup filenames further.
- False positive notes:
  - If edge/proxy blocks `/uploads/backups/*`, exposure is reduced; this was not visible in repo code.

---

## High Findings

### SBP-002: Host Header Validation Disabled by Wildcard Allowed Hosts
- Rule ID: FASTAPI-DEPLOY-TRUSTEDHOST-001
- Severity: **High**
- Location:
  - `app/main.py:82`
  - `app/main.py:305`
  - `app/main.py:306`
  - `app/main.py:4384`
  - `app/main.py:7105`
  - `render.yaml:20`
  - `render.yaml:21`
- Evidence:
  - `ALLOWED_HOSTS` default is `*`, and middleware only applies when list is not exactly `['*']`.
  - Deployment config sets `ALLOWED_HOSTS="*"`.
  - Absolute URLs are constructed from `request.base_url` for QR/calendar links.
- Impact:
  - Host-header poisoning can taint generated links and operational URLs, enabling phishing and cache poisoning scenarios.
- Fix:
  - Set explicit host allowlist (e.g., `ka-d6di.onrender.com` and production custom domain).
  - Keep `TrustedHostMiddleware` enabled in production.
- Mitigation:
  - Enforce canonical host redirects at edge/proxy.
- False positive notes:
  - Some managed platforms normalize Host upstream; verify Render ingress behavior for your service.

---

## Medium Findings

### SBP-003: Missing CSRF Protections for Cookie-Authenticated State-Changing Endpoints
- Rule ID: FASTAPI-CSRF-001
- Severity: **Medium**
- Location:
  - Cookie auth transport:
    - `app/main.py:5522`
    - `app/main.py:5526`
    - `app/main.py:4474`
    - `app/main.py:4478`
  - State-changing endpoints (examples):
    - `app/main.py:4963` (`/api/admin/season/reset`)
    - `app/main.py:5848` (`/api/pnms`)
    - `app/main.py:6572` (`/api/ratings`)
    - `app/main.py:6887` (`/api/lunches`)
- Evidence:
  - Session cookies are used for auth, but there is no CSRF token check or global unsafe-method Origin/Referer validation middleware.
- Impact:
  - If browser sends cookies in a forged request context (especially same-site or relaxed cookie settings), privileged actions can be triggered without user intent.
- Fix:
  - Add CSRF defense for unsafe methods:
    - double-submit token or synchronizer token pattern, and/or
    - strict Origin/Referer validation middleware.
- Mitigation:
  - Keep `SameSite=Strict` and `Secure` enforced for all environments serving real users.
- False positive notes:
  - `SameSite=Strict` lowers classic cross-site risk, but does not fully replace explicit CSRF controls.

### SBP-004: Login Throttle Uses Spoofable `X-Forwarded-For`
- Rule ID: FASTAPI-AUTH-RATELIMIT-001
- Severity: **Medium**
- Location:
  - `app/main.py:1481`
  - `app/main.py:1482`
  - `app/main.py:1490`
- Evidence:
  - Rate-limit key uses `x-forwarded-for` directly if present.
- Impact:
  - Attackers can spoof source IP to bypass throttling or trigger lockouts on chosen usernames/IP buckets.
- Fix:
  - Only trust forwarded client IP from known proxy chain (or use proxy middleware that sanitizes this).
  - Consider adding per-account and global attempt counters independent of client IP.
- Mitigation:
  - Keep low lockout windows and monitor login failures server-side.
- False positive notes:
  - If your ingress strips and rewrites `X-Forwarded-For`, risk is reduced.

### SBP-005: CSV Formula Injection Risk in Backup Export
- Rule ID: FASTAPI-OUTPUT-CSV-001
- Severity: **Medium**
- Location:
  - `app/main.py:2000`
  - `app/main.py:2003`
- Evidence:
  - Raw user-controlled strings are written into CSV cells without formula-neutralization.
- Impact:
  - Opening exports in spreadsheet software can execute attacker-crafted formulas (`=`, `+`, `-`, `@` prefixes), enabling data exfiltration/social-engineering payloads.
- Fix:
  - Neutralize leading formula characters when serializing CSV values (prefix with `'` or space).
- Mitigation:
  - Open CSVs in safe viewers; disable external links/macros for operational users.
- False positive notes:
  - Risk materializes primarily when CSV is opened in spreadsheet software.

---

## Low Findings

### SBP-006: Bootstrap Credential Secrets Printed to Logs When Env Vars Missing
- Rule ID: FASTAPI-SECRETS-LOGGING-001
- Severity: **Low**
- Location:
  - `app/main.py:2239`
  - `app/main.py:2242`
  - `app/main.py:3284`
  - `app/main.py:3287`
- Evidence:
  - Startup code prints generated bootstrap passwords to stdout when seed env vars are absent.
- Impact:
  - Secrets may leak to log aggregators and broaden credential exposure.
- Fix:
  - In production, fail startup when bootstrap secrets are unset (or print only non-sensitive warning).
- Mitigation:
  - Restrict log access and rotate any bootstrap credentials seen in logs.
- False positive notes:
  - If env vars are always set in production, this path is dormant.

---

## What I Did Not Find
- No SQL injection patterns in app queries (parameterized SQL used throughout reviewed code).
- No obvious command injection or unsafe deserialization patterns in backend.
- Frontend code heavily uses `escapeHtml(...)` around `innerHTML` templating; no high-confidence DOM XSS sink was confirmed in sampled paths.

## Recommended Remediation Order
1. Fix backup exposure path (`SBP-001`) and rotate credentials/sessions if needed.
2. Enforce strict host allowlist (`SBP-002`).
3. Add CSRF protection layer (`SBP-003`).
4. Harden login throttling source-IP trust (`SBP-004`).
5. Add CSV formula neutralization in exports (`SBP-005`).
6. Remove secret logging fallback (`SBP-006`).
