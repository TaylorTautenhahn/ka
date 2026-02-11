from __future__ import annotations

import hmac
import hashlib
import io
import json
import os
import re
import secrets
import sqlite3
import time
import zipfile
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
import csv

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "recruitment.db")))
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", str(BASE_DIR / "uploads")))
PNM_UPLOADS_DIR = UPLOADS_DIR / "pnms"
MAX_PNM_PHOTO_BYTES = int(os.getenv("MAX_PNM_PHOTO_BYTES", str(4 * 1024 * 1024)))
PNM_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", str(UPLOADS_DIR / "backups")))
MAX_BACKUP_FILES = int(os.getenv("MAX_BACKUP_FILES", "30"))
SESSION_COOKIE = "rush_session"
HASH_SCHEME = os.getenv("HASH_SCHEME", "pbkdf2_sha256")
PASSWORD_ITERATIONS = int(os.getenv("PASSWORD_ITERATIONS", "260000"))
LEGACY_AUTH_SALT = os.getenv("LEGACY_AUTH_SALT", "kao-rush-v1")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "43200"))
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0").strip().lower() in {"1", "true", "yes"}
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "strict").strip().lower()
ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "*").split(",") if host.strip()]
LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", "300"))
LOGIN_MAX_FAILURES = int(os.getenv("LOGIN_MAX_FAILURES", "8"))
LOGIN_BLOCK_SECONDS = int(os.getenv("LOGIN_BLOCK_SECONDS", "600"))
HEAD_SEED_ACCESS_CODE = os.getenv("HEAD_SEED_ACCESS_CODE", "").strip()
HEAD_SEED_USERNAME = os.getenv("HEAD_SEED_USERNAME", "head.rush.officer").strip() or "head.rush.officer"
HEAD_SEED_FIRST_NAME = os.getenv("HEAD_SEED_FIRST_NAME", "Head").strip() or "Head"
HEAD_SEED_LAST_NAME = os.getenv("HEAD_SEED_LAST_NAME", "Officer").strip() or "Officer"
HEAD_SEED_PLEDGE_CLASS = os.getenv("HEAD_SEED_PLEDGE_CLASS", "Admin").strip() or "Admin"
AUTO_CREATE_HEAD_SEED = os.getenv("AUTO_CREATE_HEAD_SEED", "1").strip().lower() in {"1", "true", "yes"}

ROLE_HEAD = "Head Rush Officer"
ROLE_RUSH_OFFICER = "Rush Officer"
ROLE_RUSHER = "Rusher"
ALLOWED_ROLES = {ROLE_HEAD, ROLE_RUSH_OFFICER, ROLE_RUSHER}
RATING_FIELDS = [
    "good_with_girls",
    "will_make_it",
    "personable",
    "alcohol_control",
    "instagram_marketability",
]
ALLOWED_PHOTO_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

app = FastAPI(
    title="KA Recruitment Evaluation",
    description="Connected, role-aware recruitment evaluation platform.",
    version="1.0.0",
)
app.add_middleware(GZipMiddleware, minimum_size=512)
if ALLOWED_HOSTS != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

_LOGIN_GUARD = Lock()
_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
_LOGIN_BLOCKED_UNTIL: dict[str, float] = {}
GENERATED_HEAD_ACCESS_CODE: str | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_epoch() -> float:
    return time.time()


def normalize_samesite(value: str) -> str:
    if value in {"lax", "strict", "none"}:
        return value
    return "strict"


@app.middleware("http")
async def security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "manifest-src 'self'; "
        "worker-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'"
    )
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    return response


@contextmanager
def db_session() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def hash_access_code(access_code: str) -> str:
    access_code_norm = access_code.strip()
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        access_code_norm.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return f"{HASH_SCHEME}${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_access_code(access_code: str, stored: str) -> tuple[bool, bool]:
    """
    Returns tuple:
    - first: whether the supplied access code is valid
    - second: whether the stored hash should be upgraded to the current scheme
    """
    access_code_norm = access_code.strip()
    if stored.startswith(f"{HASH_SCHEME}$"):
        try:
            _, iteration_raw, salt_hex, digest_hex = stored.split("$", 3)
            iterations = int(iteration_raw)
            salt = bytes.fromhex(salt_hex)
        except (ValueError, TypeError):
            return False, False
        digest = hashlib.pbkdf2_hmac("sha256", access_code_norm.encode("utf-8"), salt, iterations).hex()
        valid = hmac.compare_digest(digest, digest_hex)
        needs_upgrade = valid and iterations < PASSWORD_ITERATIONS
        return valid, needs_upgrade

    # Legacy fallback support (single static-sha hash), upgraded on successful login.
    legacy = hashlib.sha256(f"{LEGACY_AUTH_SALT}:{access_code_norm}".encode("utf-8")).hexdigest()
    valid = hmac.compare_digest(legacy, stored)
    return valid, valid


def validate_access_code_strength(access_code: str) -> None:
    access_code_norm = access_code.strip()
    if len(access_code_norm) < 8:
        raise ValueError("Access code must be at least 8 characters.")
    if not re.search(r"[A-Za-z]", access_code_norm) or not re.search(r"[0-9]", access_code_norm):
        raise ValueError("Access code must include at least one letter and one number.")


def client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def assert_login_allowed(ip_address: str) -> None:
    now = now_epoch()
    with _LOGIN_GUARD:
        blocked_until = _LOGIN_BLOCKED_UNTIL.get(ip_address, 0)
        if blocked_until > now:
            retry_after = max(1, int(blocked_until - now))
            raise HTTPException(
                status_code=429,
                detail=f"Too many login attempts. Try again in {retry_after} seconds.",
            )


def record_login_failure(ip_address: str) -> None:
    now = now_epoch()
    with _LOGIN_GUARD:
        attempts = [ts for ts in _LOGIN_ATTEMPTS.get(ip_address, []) if now - ts <= LOGIN_WINDOW_SECONDS]
        attempts.append(now)
        _LOGIN_ATTEMPTS[ip_address] = attempts
        if len(attempts) >= LOGIN_MAX_FAILURES:
            _LOGIN_BLOCKED_UNTIL[ip_address] = now + LOGIN_BLOCK_SECONDS
            _LOGIN_ATTEMPTS[ip_address] = []


def record_login_success(ip_address: str) -> None:
    with _LOGIN_GUARD:
        _LOGIN_ATTEMPTS.pop(ip_address, None)
        _LOGIN_BLOCKED_UNTIL.pop(ip_address, None)


def normalize_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Name fields cannot be empty.")
    return value[0].upper() + value[1:].strip()


def normalize_interest(raw: str) -> str:
    token = raw.strip()
    if not token:
        raise ValueError("Interests cannot be empty.")
    if " " in token:
        raise ValueError("Interests must be one word with no spaces.")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", token):
        raise ValueError("Interests must start with a letter and contain only letters or numbers.")
    return token[0].upper() + token[1:].lower()


def parse_interests(payload: str | list[str]) -> list[str]:
    if isinstance(payload, str):
        raw_tokens = [part.strip() for part in re.split(r"[,;\n]+", payload) if part.strip()]
    else:
        raw_tokens = [str(part).strip() for part in payload if str(part).strip()]

    normalized: list[str] = []
    seen: set[str] = set()
    for token in raw_tokens:
        value = normalize_interest(token)
        key = value.lower()
        if key not in seen:
            seen.add(key)
            normalized.append(value)

    if not normalized:
        raise ValueError("Provide at least one interest.")
    return normalized


def encode_interests(interests: list[str]) -> tuple[str, str]:
    canonical = ",".join(interests)
    normalized = ",".join([interest.lower() for interest in interests])
    return canonical, normalized


def decode_interests(interests_csv: str) -> list[str]:
    if not interests_csv:
        return []
    return [item for item in interests_csv.split(",") if item]


def parse_interest_filter(raw_interest: str | None) -> set[str]:
    if raw_interest is None or not raw_interest.strip():
        return set()
    if "," not in raw_interest and ";" not in raw_interest and "\n" not in raw_interest:
        values = [raw_interest.strip()]
    else:
        values = [part.strip() for part in re.split(r"[,;\n]+", raw_interest) if part.strip()]
    return {normalize_interest(value).lower() for value in values}


def has_interest_match(normalized_csv: str, required: set[str]) -> bool:
    if not required:
        return True
    candidate = {item for item in normalized_csv.split(",") if item}
    return bool(candidate & required)


def role_weight(role: str) -> float:
    if role in {ROLE_RUSH_OFFICER, ROLE_HEAD}:
        return 0.6
    return 0.4


def score_total(payload: dict[str, int]) -> int:
    return (
        payload["good_with_girls"]
        + payload["will_make_it"]
        + payload["personable"]
        + payload["alcohol_control"]
        + payload["instagram_marketability"]
    )


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def pnm_code_base(first_name: str, last_name: str, first_event_date: str) -> str:
    prefix = (first_name[:1] + last_name[:2]).upper()
    prefix = (prefix + "XXX")[:3]
    dt = datetime.strptime(first_event_date, "%Y-%m-%d")
    return f"{prefix}{dt.strftime('%m%d%Y')}"


def ensure_unique_pnm_code(conn: sqlite3.Connection, pnm_id: int, code_base: str) -> str:
    code = code_base
    suffix = 2
    while True:
        row = conn.execute("SELECT id FROM pnms WHERE pnm_code = ? AND id != ?", (code, pnm_id)).fetchone()
        if not row:
            return code
        code = f"{code_base}{suffix}"
        suffix += 1


def verify_iso_date(value: str, label: str) -> str:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be in YYYY-MM-DD format.") from exc
    return value


def normalize_instagram_handle(value: str) -> str:
    handle = value.strip()
    if not handle:
        raise ValueError("Instagram handle is required.")
    if not handle.startswith("@"):
        handle = f"@{handle}"
    if not re.fullmatch(r"@[A-Za-z0-9._]{1,30}", handle):
        raise ValueError("Instagram handle must contain only letters, numbers, dots, or underscores.")
    return handle


def public_photo_url(photo_path: str | None) -> str | None:
    if not photo_path:
        return None
    if photo_path.startswith("/uploads/"):
        return photo_path
    return None


def photo_fs_path(photo_path: str | None) -> Path | None:
    if not photo_path or not photo_path.startswith("/uploads/pnms/"):
        return None
    name = Path(photo_path).name
    if not name:
        return None
    return PNM_UPLOADS_DIR / name


def remove_photo_if_present(photo_path: str | None) -> None:
    target = photo_fs_path(photo_path)
    if target and target.exists() and target.is_file():
        target.unlink(missing_ok=True)


def split_normalized_csv(value: str) -> set[str]:
    return {token for token in value.split(",") if token}


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def prune_backup_files(prefix: str) -> None:
    if not BACKUP_DIR.exists():
        return
    files = sorted(BACKUP_DIR.glob(f"{prefix}-*.sqlite"), key=lambda path: path.stat().st_mtime, reverse=True)
    for stale in files[MAX_BACKUP_FILES:]:
        stale.unlink(missing_ok=True)


def create_sqlite_snapshot(prefix: str = "snapshot") -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"{prefix}-{timestamp_slug()}.sqlite"
    source = sqlite3.connect(DB_PATH)
    destination = sqlite3.connect(backup_path)
    try:
        with destination:
            source.backup(destination)
    finally:
        destination.close()
        source.close()
    prune_backup_files(prefix)
    return backup_path


def csv_bytes_from_rows(columns: list[str], rows: list[dict[str, Any]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({column: row.get(column) for column in columns})
    return buffer.getvalue().encode("utf-8")


def build_csv_backup_archive() -> tuple[bytes, str]:
    with db_session() as conn:
        users_rows = [dict(row) for row in conn.execute(
            """
            SELECT
                id,
                username,
                first_name,
                last_name,
                pledge_class,
                role,
                emoji,
                stereotype,
                interests,
                interests_norm,
                is_approved,
                approved_by,
                approved_at,
                created_at,
                updated_at,
                last_login_at,
                total_lunches,
                lunches_per_week,
                rating_count,
                avg_rating_given
            FROM users
            ORDER BY id ASC
            """
        ).fetchall()]
        pnm_rows = [dict(row) for row in conn.execute("SELECT * FROM pnms ORDER BY id ASC").fetchall()]
        rating_rows = [dict(row) for row in conn.execute("SELECT * FROM ratings ORDER BY id ASC").fetchall()]
        rating_change_rows = [dict(row) for row in conn.execute("SELECT * FROM rating_changes ORDER BY id ASC").fetchall()]
        lunch_rows = [dict(row) for row in conn.execute("SELECT * FROM lunches ORDER BY id ASC").fetchall()]

    export_ts = timestamp_slug()
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("users.csv", csv_bytes_from_rows(list(users_rows[0].keys()) if users_rows else [
            "id",
            "username",
            "first_name",
            "last_name",
            "pledge_class",
            "role",
            "emoji",
            "stereotype",
            "interests",
            "interests_norm",
            "is_approved",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
            "last_login_at",
            "total_lunches",
            "lunches_per_week",
            "rating_count",
            "avg_rating_given",
        ], users_rows))
        zf.writestr("pnms.csv", csv_bytes_from_rows(list(pnm_rows[0].keys()) if pnm_rows else [
            "id",
            "pnm_code",
            "first_name",
            "last_name",
            "class_year",
            "hometown",
            "instagram_handle",
            "first_event_date",
            "interests",
            "interests_norm",
            "stereotype",
            "photo_path",
            "photo_uploaded_at",
            "photo_uploaded_by",
            "lunch_stats",
            "total_lunches",
            "rating_count",
            "avg_good_with_girls",
            "avg_will_make_it",
            "avg_personable",
            "avg_alcohol_control",
            "avg_instagram_marketability",
            "weighted_total",
            "created_by",
            "created_at",
            "updated_at",
        ], pnm_rows))
        zf.writestr("ratings.csv", csv_bytes_from_rows(list(rating_rows[0].keys()) if rating_rows else [
            "id",
            "pnm_id",
            "user_id",
            "good_with_girls",
            "will_make_it",
            "personable",
            "alcohol_control",
            "instagram_marketability",
            "total_score",
            "comment",
            "created_at",
            "updated_at",
        ], rating_rows))
        zf.writestr("rating_changes.csv", csv_bytes_from_rows(list(rating_change_rows[0].keys()) if rating_change_rows else [
            "id",
            "rating_id",
            "pnm_id",
            "user_id",
            "old_total",
            "new_total",
            "delta_total",
            "old_payload",
            "new_payload",
            "comment",
            "changed_at",
        ], rating_change_rows))
        zf.writestr("lunches.csv", csv_bytes_from_rows(list(lunch_rows[0].keys()) if lunch_rows else [
            "id",
            "pnm_id",
            "user_id",
            "lunch_date",
            "notes",
            "created_at",
        ], lunch_rows))
        readme = (
            "KAO Rush Backup Export\n"
            f"Generated (UTC): {datetime.now(timezone.utc).isoformat()}\n"
            f"Database path: {DB_PATH}\n"
            "Contains: users.csv, pnms.csv, ratings.csv, rating_changes.csv, lunches.csv\n"
            "Access code hashes are intentionally excluded from users.csv for security.\n"
        )
        zf.writestr("README.txt", readme.encode("utf-8"))
    return archive.getvalue(), export_ts


def resolve_seed_access_code() -> str:
    global GENERATED_HEAD_ACCESS_CODE
    if HEAD_SEED_ACCESS_CODE:
        return HEAD_SEED_ACCESS_CODE
    if GENERATED_HEAD_ACCESS_CODE:
        return GENERATED_HEAD_ACCESS_CODE
    GENERATED_HEAD_ACCESS_CODE = secrets.token_urlsafe(14)
    print(
        "[startup] HEAD_SEED_ACCESS_CODE not provided. Generated bootstrap credentials for first login:\n"
        f"          username={HEAD_SEED_USERNAME}\n"
        f"          access_code={GENERATED_HEAD_ACCESS_CODE}\n"
        "          Set HEAD_SEED_ACCESS_CODE in production to disable random generation."
    )
    return GENERATED_HEAD_ACCESS_CODE


def recalc_member_rating_stats(conn: sqlite3.Connection, user_id: int) -> None:
    stats = conn.execute(
        "SELECT COUNT(*) AS c, COALESCE(AVG(total_score), 0) AS avg_total FROM ratings WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.execute(
        "UPDATE users SET rating_count = ?, avg_rating_given = ?, updated_at = ? WHERE id = ?",
        (int(stats["c"]), float(stats["avg_total"]), now_iso(), user_id),
    )


def recalc_member_lunch_stats(conn: sqlite3.Connection, user_id: int) -> None:
    total_row = conn.execute("SELECT COUNT(*) AS c FROM lunches WHERE user_id = ?", (user_id,)).fetchone()
    week_row = conn.execute(
        "SELECT COUNT(*) AS c FROM lunches WHERE user_id = ? AND lunch_date >= date('now', '-6 day')",
        (user_id,),
    ).fetchone()
    conn.execute(
        "UPDATE users SET total_lunches = ?, lunches_per_week = ?, updated_at = ? WHERE id = ?",
        (int(total_row["c"]), float(week_row["c"]), now_iso(), user_id),
    )


def recalc_pnm_lunch_stats(conn: sqlite3.Connection, pnm_id: int) -> None:
    row = conn.execute("SELECT COUNT(*) AS c FROM lunches WHERE pnm_id = ?", (pnm_id,)).fetchone()
    conn.execute(
        "UPDATE pnms SET total_lunches = ?, updated_at = ? WHERE id = ?",
        (int(row["c"]), now_iso(), pnm_id),
    )


def recalc_pnm_rating_stats(conn: sqlite3.Connection, pnm_id: int) -> None:
    rows = conn.execute(
        """
        SELECT
            r.good_with_girls,
            r.will_make_it,
            r.personable,
            r.alcohol_control,
            r.instagram_marketability,
            r.total_score,
            u.role
        FROM ratings r
        JOIN users u ON u.id = r.user_id
        WHERE r.pnm_id = ?
        """,
        (pnm_id,),
    ).fetchall()

    if not rows:
        conn.execute(
            """
            UPDATE pnms
            SET
                rating_count = 0,
                avg_good_with_girls = 0,
                avg_will_make_it = 0,
                avg_personable = 0,
                avg_alcohol_control = 0,
                avg_instagram_marketability = 0,
                weighted_total = 0,
                updated_at = ?
            WHERE id = ?
            """,
            (now_iso(), pnm_id),
        )
        return

    weighted_totals = {
        "good_with_girls": 0.0,
        "will_make_it": 0.0,
        "personable": 0.0,
        "alcohol_control": 0.0,
        "instagram_marketability": 0.0,
        "total_score": 0.0,
    }
    total_weight = 0.0

    for row in rows:
        weight = role_weight(row["role"])
        total_weight += weight
        weighted_totals["good_with_girls"] += row["good_with_girls"] * weight
        weighted_totals["will_make_it"] += row["will_make_it"] * weight
        weighted_totals["personable"] += row["personable"] * weight
        weighted_totals["alcohol_control"] += row["alcohol_control"] * weight
        weighted_totals["instagram_marketability"] += row["instagram_marketability"] * weight
        weighted_totals["total_score"] += row["total_score"] * weight

    if total_weight == 0:
        avg_good = avg_will = avg_personable = avg_alcohol = avg_ig = avg_total = 0.0
    else:
        avg_good = weighted_totals["good_with_girls"] / total_weight
        avg_will = weighted_totals["will_make_it"] / total_weight
        avg_personable = weighted_totals["personable"] / total_weight
        avg_alcohol = weighted_totals["alcohol_control"] / total_weight
        avg_ig = weighted_totals["instagram_marketability"] / total_weight
        avg_total = weighted_totals["total_score"] / total_weight

    conn.execute(
        """
        UPDATE pnms
        SET
            rating_count = ?,
            avg_good_with_girls = ?,
            avg_will_make_it = ?,
            avg_personable = ?,
            avg_alcohol_control = ?,
            avg_instagram_marketability = ?,
            weighted_total = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            len(rows),
            float(avg_good),
            float(avg_will),
            float(avg_personable),
            float(avg_alcohol),
            float(avg_ig),
            float(avg_total),
            now_iso(),
            pnm_id,
        ),
    )


def setup_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            pledge_class TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('Head Rush Officer', 'Rush Officer', 'Rusher')),
            emoji TEXT,
            stereotype TEXT NOT NULL,
            interests TEXT NOT NULL,
            interests_norm TEXT NOT NULL,
            access_code_hash TEXT NOT NULL,
            is_approved INTEGER NOT NULL DEFAULT 0,
            approved_by INTEGER REFERENCES users(id),
            approved_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_login_at TEXT,
            total_lunches INTEGER NOT NULL DEFAULT 0,
            lunches_per_week REAL NOT NULL DEFAULT 0,
            rating_count INTEGER NOT NULL DEFAULT 0,
            avg_rating_given REAL NOT NULL DEFAULT 0,
            CHECK (
                (role = 'Rush Officer' AND emoji IS NOT NULL AND length(trim(emoji)) > 0)
                OR (role != 'Rush Officer' AND (emoji IS NULL OR length(trim(emoji)) = 0))
            )
        );

        CREATE TABLE IF NOT EXISTS pnms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pnm_code TEXT NOT NULL UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            class_year TEXT NOT NULL CHECK (class_year IN ('F', 'S', 'J')),
            hometown TEXT NOT NULL,
            instagram_handle TEXT NOT NULL,
            first_event_date TEXT NOT NULL,
            interests TEXT NOT NULL,
            interests_norm TEXT NOT NULL,
            stereotype TEXT NOT NULL,
            photo_path TEXT,
            photo_uploaded_at TEXT,
            photo_uploaded_by INTEGER REFERENCES users(id),
            lunch_stats TEXT NOT NULL DEFAULT '',
            total_lunches INTEGER NOT NULL DEFAULT 0,
            rating_count INTEGER NOT NULL DEFAULT 0,
            avg_good_with_girls REAL NOT NULL DEFAULT 0,
            avg_will_make_it REAL NOT NULL DEFAULT 0,
            avg_personable REAL NOT NULL DEFAULT 0,
            avg_alcohol_control REAL NOT NULL DEFAULT 0,
            avg_instagram_marketability REAL NOT NULL DEFAULT 0,
            weighted_total REAL NOT NULL DEFAULT 0,
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pnm_id INTEGER NOT NULL REFERENCES pnms(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            good_with_girls INTEGER NOT NULL CHECK (good_with_girls BETWEEN 0 AND 10),
            will_make_it INTEGER NOT NULL CHECK (will_make_it BETWEEN 0 AND 10),
            personable INTEGER NOT NULL CHECK (personable BETWEEN 0 AND 10),
            alcohol_control INTEGER NOT NULL CHECK (alcohol_control BETWEEN 0 AND 10),
            instagram_marketability INTEGER NOT NULL CHECK (instagram_marketability BETWEEN 0 AND 5),
            total_score INTEGER NOT NULL CHECK (total_score BETWEEN 0 AND 45),
            comment TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (pnm_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS rating_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rating_id INTEGER NOT NULL UNIQUE REFERENCES ratings(id) ON DELETE CASCADE,
            pnm_id INTEGER NOT NULL REFERENCES pnms(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            old_total INTEGER NOT NULL,
            new_total INTEGER NOT NULL,
            delta_total INTEGER NOT NULL,
            old_payload TEXT NOT NULL,
            new_payload TEXT NOT NULL,
            comment TEXT NOT NULL,
            changed_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS lunches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pnm_id INTEGER NOT NULL REFERENCES pnms(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            lunch_date TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            UNIQUE (pnm_id, user_id, lunch_date)
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_users_stereotype ON users(stereotype);
        CREATE INDEX IF NOT EXISTS idx_users_interests ON users(interests_norm);
        CREATE INDEX IF NOT EXISTS idx_pnms_stereotype ON pnms(stereotype);
        CREATE INDEX IF NOT EXISTS idx_pnms_interests ON pnms(interests_norm);
        CREATE INDEX IF NOT EXISTS idx_ratings_pnm ON ratings(pnm_id);
        CREATE INDEX IF NOT EXISTS idx_ratings_user ON ratings(user_id);
        CREATE INDEX IF NOT EXISTS idx_lunches_pnm ON lunches(pnm_id);
        CREATE INDEX IF NOT EXISTS idx_lunches_user ON lunches(user_id);
        """
    )


def ensure_schema_upgrades(conn: sqlite3.Connection) -> None:
    pnm_columns = {row["name"] for row in conn.execute("PRAGMA table_info(pnms)").fetchall()}
    if "photo_path" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN photo_path TEXT")
    if "photo_uploaded_at" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN photo_uploaded_at TEXT")
    if "photo_uploaded_by" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN photo_uploaded_by INTEGER REFERENCES users(id)")


def ensure_seed_data(conn: sqlite3.Connection) -> None:
    if not AUTO_CREATE_HEAD_SEED:
        return

    interests, interests_norm = encode_interests(["Leadership", "Recruitment"])
    created_at = now_iso()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (HEAD_SEED_USERNAME,)).fetchone()
    if existing:
        conn.execute(
            """
            UPDATE users
            SET
                role = ?,
                is_approved = 1,
                approved_at = COALESCE(approved_at, ?),
                updated_at = ?
            WHERE id = ?
            """,
            (
                ROLE_HEAD,
                created_at,
                created_at,
                existing["id"],
            ),
        )
        if HEAD_SEED_ACCESS_CODE:
            conn.execute(
                "UPDATE users SET access_code_hash = ?, updated_at = ? WHERE id = ?",
                (hash_access_code(HEAD_SEED_ACCESS_CODE), now_iso(), existing["id"]),
            )
        return

    seed_access_code = resolve_seed_access_code()
    conn.execute(
        """
        INSERT INTO users (
            username,
            first_name,
            last_name,
            pledge_class,
            role,
            emoji,
            stereotype,
            interests,
            interests_norm,
            access_code_hash,
            is_approved,
            approved_at,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, 1, ?, ?, ?)
        """,
        (
            HEAD_SEED_USERNAME,
            HEAD_SEED_FIRST_NAME,
            HEAD_SEED_LAST_NAME,
            HEAD_SEED_PLEDGE_CLASS,
            ROLE_HEAD,
            "Strategist",
            interests,
            interests_norm,
            hash_access_code(seed_access_code),
            created_at,
            created_at,
            created_at,
        ),
    )


def user_payload(row: sqlite3.Row, viewer_role: str, viewer_id: int) -> dict[str, Any]:
    can_view_rating_stats = viewer_role in {ROLE_HEAD, ROLE_RUSH_OFFICER} or row["id"] == viewer_id
    payload = {
        "user_id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "emoji": row["emoji"] if row["role"] == ROLE_RUSH_OFFICER else None,
        "stereotype": row["stereotype"],
        "interests": decode_interests(row["interests"]),
        "is_approved": bool(row["is_approved"]),
        "total_lunches": int(row["total_lunches"]),
        "lunches_per_week": round(float(row["lunches_per_week"]), 2),
    }
    if can_view_rating_stats:
        payload["rating_count"] = int(row["rating_count"])
        payload["avg_rating_given"] = round(float(row["avg_rating_given"]), 2)
    else:
        payload["rating_count"] = None
        payload["avg_rating_given"] = None
    return payload


def pnm_payload(row: sqlite3.Row, own_rating: dict[str, Any] | None) -> dict[str, Any]:
    days_since_event = (date.today() - date.fromisoformat(row["first_event_date"])).days
    return {
        "pnm_id": row["id"],
        "pnm_code": row["pnm_code"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "class_year": row["class_year"],
        "hometown": row["hometown"],
        "instagram_handle": row["instagram_handle"],
        "first_event_date": row["first_event_date"],
        "days_since_first_event": days_since_event,
        "interests": decode_interests(row["interests"]),
        "stereotype": row["stereotype"],
        "photo_url": public_photo_url(row["photo_path"]),
        "photo_uploaded_at": row["photo_uploaded_at"],
        "lunch_stats": row["lunch_stats"],
        "total_lunches": int(row["total_lunches"]),
        "rating_count": int(row["rating_count"]),
        "avg_good_with_girls": round(float(row["avg_good_with_girls"]), 2),
        "avg_will_make_it": round(float(row["avg_will_make_it"]), 2),
        "avg_personable": round(float(row["avg_personable"]), 2),
        "avg_alcohol_control": round(float(row["avg_alcohol_control"]), 2),
        "avg_instagram_marketability": round(float(row["avg_instagram_marketability"]), 2),
        "weighted_total": round(float(row["weighted_total"]), 2),
        "own_rating": own_rating,
    }


def rating_payload(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "rating_id": row["id"],
        "pnm_id": row["pnm_id"],
        "user_id": row["user_id"],
        "good_with_girls": row["good_with_girls"],
        "will_make_it": row["will_make_it"],
        "personable": row["personable"],
        "alcohol_control": row["alcohol_control"],
        "instagram_marketability": row["instagram_marketability"],
        "total_score": row["total_score"],
        "comment": row["comment"],
        "updated_at": row["updated_at"],
        "created_at": row["created_at"],
    }


def fetch_own_rating(conn: sqlite3.Connection, pnm_id: int, user_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM ratings WHERE pnm_id = ? AND user_id = ?",
        (pnm_id, user_id),
    ).fetchone()
    if not row:
        return None
    return rating_payload(row)


def current_user(request: Request) -> sqlite3.Row:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")

    with db_session() as conn:
        row = conn.execute(
            """
            SELECT u.*, s.last_seen_at, s.created_at AS session_created_at
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.")

        try:
            last_seen_dt = datetime.fromisoformat(row["last_seen_at"])
        except (TypeError, ValueError):
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.")
        if (datetime.now(timezone.utc) - last_seen_dt).total_seconds() > SESSION_TTL_SECONDS:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.")

        conn.execute("UPDATE sessions SET last_seen_at = ? WHERE token = ?", (now_iso(), token))
        return row


def require_head(user: sqlite3.Row = Depends(current_user)) -> sqlite3.Row:
    if user["role"] != ROLE_HEAD:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Head Rush Officer permission required.")
    return user


def require_officer(user: sqlite3.Row = Depends(current_user)) -> sqlite3.Row:
    if user["role"] not in {ROLE_HEAD, ROLE_RUSH_OFFICER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Rush Officer permission required.")
    return user


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    emoji: str | None = None
    access_code: str = Field(..., min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        username = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]{3,64}", username):
            raise ValueError("Username may only include letters, numbers, dots, underscores, and hyphens.")
        return username

    @field_validator("emoji")
    @classmethod
    def normalize_optional_emoji(cls, value: str | None) -> str | None:
        if value is None:
            return None
        emoji = value.strip()
        return emoji or None


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=120)
    access_code: str = Field(..., min_length=8, max_length=128)


class SelfUpdateRequest(BaseModel):
    stereotype: str | None = Field(default=None, min_length=1, max_length=48)
    interests: str | list[str] | None = None
    emoji: str | None = None


class PNMCreateRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=48)
    last_name: str = Field(..., min_length=1, max_length=48)
    class_year: str
    hometown: str = Field(..., min_length=1, max_length=80)
    instagram_handle: str = Field(..., min_length=1, max_length=80)
    first_event_date: str
    interests: str | list[str]
    stereotype: str = Field(..., min_length=1, max_length=48)
    lunch_stats: str = Field(default="", max_length=256)

    @field_validator("class_year")
    @classmethod
    def validate_class_year(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"F", "S", "J"}:
            raise ValueError("Class year must be F, S, or J.")
        return normalized

    @field_validator("first_event_date")
    @classmethod
    def validate_first_event_date(cls, value: str) -> str:
        return verify_iso_date(value, "First event date")


class RatingUpsertRequest(BaseModel):
    pnm_id: int
    good_with_girls: int = Field(..., ge=0, le=10)
    will_make_it: int = Field(..., ge=0, le=10)
    personable: int = Field(..., ge=0, le=10)
    alcohol_control: int = Field(..., ge=0, le=10)
    instagram_marketability: int = Field(..., ge=0, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class LunchCreateRequest(BaseModel):
    pnm_id: int
    lunch_date: str
    notes: str = Field(default="", max_length=500)

    @field_validator("lunch_date")
    @classmethod
    def validate_lunch_date(cls, value: str) -> str:
        return verify_iso_date(value, "Lunch date")


@app.on_event("startup")
def startup() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    PNM_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    with db_session() as conn:
        setup_schema(conn)
        ensure_schema_upgrades(conn)
        ensure_seed_data(conn)
    if DB_PATH.exists():
        try:
            create_sqlite_snapshot(prefix="startup")
        except Exception:
            # Snapshot should not block app startup.
            print("[startup] warning: unable to create startup snapshot.")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/service-worker.js", include_in_schema=False)
async def service_worker() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "service-worker.js", media_type="application/javascript")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/export/csv")
def export_csv_backup(_: sqlite3.Row = Depends(require_head)) -> Response:
    archive_bytes, slug = build_csv_backup_archive()
    filename = f"kao-rush-backup-{slug}.zip"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=archive_bytes, media_type="application/zip", headers=headers)


@app.get("/api/export/sqlite")
def export_sqlite_backup(_: sqlite3.Row = Depends(require_head)) -> FileResponse:
    snapshot = create_sqlite_snapshot(prefix="manual")
    return FileResponse(
        snapshot,
        media_type="application/x-sqlite3",
        filename=snapshot.name,
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/auth/register")
def register(payload: RegisterRequest) -> dict[str, str]:
    try:
        validate_access_code_strength(payload.access_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    username = payload.username.strip()
    parts = [token for token in re.split(r"[._-]+", username) if token]
    first_name = normalize_name((parts[0] if parts else "Rush")[:48])
    last_name = normalize_name((parts[1] if len(parts) > 1 else "Officer")[:48])
    pledge_class = "Open"
    stereotype = "Unassigned"
    interests_csv, interests_norm = encode_interests(["Recruitment"])
    emoji = payload.emoji if payload.emoji else "🛡️"

    with db_session() as conn:
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Username already exists.")

        created_at = now_iso()
        try:
            conn.execute(
                """
                INSERT INTO users (
                    username,
                    first_name,
                    last_name,
                    pledge_class,
                    role,
                    emoji,
                    stereotype,
                    interests,
                    interests_norm,
                    access_code_hash,
                    is_approved,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    username,
                    first_name,
                    last_name,
                    pledge_class,
                    ROLE_RUSH_OFFICER,
                    emoji,
                    stereotype,
                    interests_csv,
                    interests_norm,
                    hash_access_code(payload.access_code),
                    created_at,
                    created_at,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=400, detail=f"Could not register user: {exc}") from exc

    return {
        "message": "Registration submitted. Head Rush Officer approval is required before login.",
        "username": username,
    }


@app.post("/api/auth/login")
def login(payload: LoginRequest, request: Request, response: Response) -> dict[str, Any]:
    ip_address = client_ip(request)
    assert_login_allowed(ip_address)

    with db_session() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (payload.username.strip(),)).fetchone()
        if not row:
            record_login_failure(ip_address)
            raise HTTPException(status_code=401, detail="Invalid username or access code.")

        password_ok, needs_upgrade = verify_access_code(payload.access_code, row["access_code_hash"])
        if not password_ok:
            record_login_failure(ip_address)
            raise HTTPException(status_code=401, detail="Invalid username or access code.")

        if not bool(row["is_approved"]):
            raise HTTPException(status_code=403, detail="Username pending Head Rush Officer approval.")

        token = secrets.token_urlsafe(32)
        now = now_iso()
        conn.execute("INSERT INTO sessions (token, user_id, created_at, last_seen_at) VALUES (?, ?, ?, ?)", (token, row["id"], now, now))
        conn.execute("UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?", (now, now, row["id"]))
        if needs_upgrade:
            conn.execute(
                "UPDATE users SET access_code_hash = ?, updated_at = ? WHERE id = ?",
                (hash_access_code(payload.access_code), now_iso(), row["id"]),
            )

        response.set_cookie(
            key=SESSION_COOKIE,
            value=token,
            httponly=True,
            samesite=normalize_samesite(SESSION_COOKIE_SAMESITE),
            max_age=SESSION_TTL_SECONDS,
            secure=SESSION_COOKIE_SECURE,
            path="/",
        )
        record_login_success(ip_address)

        return {
            "user": user_payload(row, row["role"], row["id"]),
            "message": "Logged in.",
        }


@app.post("/api/auth/logout")
def logout(request: Request, response: Response) -> dict[str, str]:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        with db_session() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        secure=SESSION_COOKIE_SECURE,
        samesite=normalize_samesite(SESSION_COOKIE_SAMESITE),
    )
    return {"message": "Logged out."}


@app.get("/api/auth/me")
def auth_me(user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    return {
        "authenticated": True,
        "user": user_payload(user, user["role"], user["id"]),
    }


@app.get("/api/users/pending")
def pending_users(_: sqlite3.Row = Depends(require_head)) -> dict[str, Any]:
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT id, username, role, stereotype, interests, created_at
            FROM users
            WHERE is_approved = 0
            ORDER BY created_at ASC
            """
        ).fetchall()

    return {
        "pending": [
            {
                "user_id": row["id"],
                "username": row["username"],
                "role": row["role"],
                "stereotype": row["stereotype"],
                "interests": decode_interests(row["interests"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    }


@app.post("/api/users/pending/{user_id}/approve")
def approve_user(user_id: int, approver: sqlite3.Row = Depends(require_head)) -> dict[str, str]:
    with db_session() as conn:
        row = conn.execute("SELECT id, is_approved FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found.")
        if bool(row["is_approved"]):
            return {"message": "User already approved."}

        conn.execute(
            "UPDATE users SET is_approved = 1, approved_by = ?, approved_at = ?, updated_at = ? WHERE id = ?",
            (approver["id"], now_iso(), now_iso(), user_id),
        )

    return {"message": "User approved."}


@app.get("/api/users")
def list_users(
    interest: str | None = None,
    stereotype: str | None = None,
    user: sqlite3.Row = Depends(current_user),
) -> dict[str, Any]:
    try:
        interest_filter = parse_interest_filter(interest)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    normalized_stereotype = stereotype.strip().lower() if stereotype else None

    with db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE is_approved = 1 ORDER BY role ASC, username ASC"
        ).fetchall()

    filtered = []
    for row in rows:
        if normalized_stereotype and row["stereotype"].lower() != normalized_stereotype:
            continue
        if not has_interest_match(row["interests_norm"], interest_filter):
            continue
        filtered.append(user_payload(row, user["role"], user["id"]))

    return {"users": filtered}


@app.patch("/api/users/me")
def update_self(payload: SelfUpdateRequest, user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    if payload.stereotype is None and payload.interests is None and payload.emoji is None:
        raise HTTPException(status_code=400, detail="No changes provided.")

    with db_session() as conn:
        existing = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="User not found.")

        stereotype_value = existing["stereotype"]
        interests_csv = existing["interests"]
        interests_norm = existing["interests_norm"]
        emoji_value = existing["emoji"]

        if payload.stereotype is not None:
            stereotype = payload.stereotype.strip()
            if not stereotype:
                raise HTTPException(status_code=400, detail="Stereotype cannot be empty.")
            stereotype_value = stereotype

        if payload.interests is not None:
            try:
                interests = parse_interests(payload.interests)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            interests_csv, interests_norm = encode_interests(interests)

        if payload.emoji is not None:
            if user["role"] != ROLE_RUSH_OFFICER:
                raise HTTPException(status_code=400, detail="Only Rush Officers can set emoji identifiers.")
            if not payload.emoji.strip():
                raise HTTPException(status_code=400, detail="Emoji cannot be empty for Rush Officers.")
            emoji_value = payload.emoji.strip()

        conn.execute(
            """
            UPDATE users
            SET stereotype = ?, interests = ?, interests_norm = ?, emoji = ?, updated_at = ?
            WHERE id = ?
            """,
            (stereotype_value, interests_csv, interests_norm, emoji_value, now_iso(), user["id"]),
        )
        refreshed = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()

    return {"user": user_payload(refreshed, refreshed["role"], refreshed["id"])}


@app.post("/api/pnms")
def create_pnm(payload: PNMCreateRequest, user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    try:
        interests = parse_interests(payload.interests)
        instagram_handle = normalize_instagram_handle(payload.instagram_handle)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    interests_csv, interests_norm = encode_interests(interests)
    created_at = now_iso()
    first_name = normalize_name(payload.first_name)
    last_name = normalize_name(payload.last_name)
    stereotype = payload.stereotype.strip()
    hometown = payload.hometown.strip()
    if not stereotype:
        raise HTTPException(status_code=400, detail="Stereotype is required.")
    if not hometown:
        raise HTTPException(status_code=400, detail="Hometown is required.")

    with db_session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO pnms (
                pnm_code,
                first_name,
                last_name,
                class_year,
                hometown,
                instagram_handle,
                first_event_date,
                interests,
                interests_norm,
                stereotype,
                lunch_stats,
                created_by,
                created_at,
                updated_at
            )
            VALUES ('TBD', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                first_name,
                last_name,
                payload.class_year,
                hometown,
                instagram_handle,
                payload.first_event_date,
                interests_csv,
                interests_norm,
                stereotype,
                payload.lunch_stats.strip(),
                user["id"],
                created_at,
                created_at,
            ),
        )
        pnm_id = int(cursor.lastrowid)

        base = pnm_code_base(first_name, last_name, payload.first_event_date)
        code = ensure_unique_pnm_code(conn, pnm_id, base)
        conn.execute("UPDATE pnms SET pnm_code = ?, updated_at = ? WHERE id = ?", (code, now_iso(), pnm_id))

        row = conn.execute("SELECT * FROM pnms WHERE id = ?", (pnm_id,)).fetchone()

    return {"pnm": pnm_payload(row, own_rating=None)}


@app.get("/api/pnms")
def list_pnms(
    interest: str | None = None,
    stereotype: str | None = None,
    user: sqlite3.Row = Depends(current_user),
) -> dict[str, Any]:
    try:
        interest_filter = parse_interest_filter(interest)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    normalized_stereotype = stereotype.strip().lower() if stereotype else None

    with db_session() as conn:
        own_rows = conn.execute(
            "SELECT * FROM ratings WHERE user_id = ?",
            (user["id"],),
        ).fetchall()
        own_rating_by_pnm = {row["pnm_id"]: rating_payload(row) for row in own_rows}

        rows = conn.execute(
            "SELECT * FROM pnms ORDER BY weighted_total DESC, last_name ASC, first_name ASC"
        ).fetchall()

    filtered = []
    for row in rows:
        if normalized_stereotype and row["stereotype"].lower() != normalized_stereotype:
            continue
        if not has_interest_match(row["interests_norm"], interest_filter):
            continue
        filtered.append(pnm_payload(row, own_rating_by_pnm.get(row["id"])))

    return {"pnms": filtered}


@app.get("/api/pnms/{pnm_id}")
def get_pnm(pnm_id: int, user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM pnms WHERE id = ?", (pnm_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="PNM not found.")
        own = fetch_own_rating(conn, pnm_id, user["id"])
    return {"pnm": pnm_payload(row, own)}


@app.post("/api/pnms/{pnm_id}/photo")
async def upload_pnm_photo(
    pnm_id: int,
    photo: UploadFile = File(...),
    user: sqlite3.Row = Depends(require_officer),
) -> dict[str, Any]:
    content_type = (photo.content_type or "").lower().strip()
    extension = ALLOWED_PHOTO_TYPES.get(content_type)
    if extension is None:
        raise HTTPException(status_code=400, detail="Unsupported image type. Use JPG, PNG, or WEBP.")

    content = await photo.read(MAX_PNM_PHOTO_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Image file cannot be empty.")
    if len(content) > MAX_PNM_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail=f"Image too large. Max size is {MAX_PNM_PHOTO_BYTES // (1024 * 1024)} MB.")

    filename = f"pnm-{pnm_id}-{secrets.token_hex(10)}{extension}"
    target_path = PNM_UPLOADS_DIR / filename
    public_path = f"/uploads/pnms/{filename}"
    old_photo_path: str | None = None

    try:
        target_path.write_bytes(content)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Unable to save photo: {exc}") from exc

    try:
        with db_session() as conn:
            row = conn.execute("SELECT * FROM pnms WHERE id = ?", (pnm_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="PNM not found.")
            old_photo_path = row["photo_path"]

            now = now_iso()
            conn.execute(
                """
                UPDATE pnms
                SET photo_path = ?, photo_uploaded_at = ?, photo_uploaded_by = ?, updated_at = ?
                WHERE id = ?
                """,
                (public_path, now, user["id"], now, pnm_id),
            )

            refreshed = conn.execute("SELECT * FROM pnms WHERE id = ?", (pnm_id,)).fetchone()
            own = fetch_own_rating(conn, pnm_id, user["id"])
    except Exception:
        target_path.unlink(missing_ok=True)
        raise

    if old_photo_path and old_photo_path != public_path:
        remove_photo_if_present(old_photo_path)

    return {
        "message": "PNM photo uploaded.",
        "pnm": pnm_payload(refreshed, own),
    }


@app.get("/api/pnms/{pnm_id}/meeting")
def pnm_meeting_view(pnm_id: int, user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    with db_session() as conn:
        pnm_row = conn.execute("SELECT * FROM pnms WHERE id = ?", (pnm_id,)).fetchone()
        if not pnm_row:
            raise HTTPException(status_code=404, detail="PNM not found.")

        own = fetch_own_rating(conn, pnm_id, user["id"])
        rating_rows = conn.execute(
            """
            SELECT
                r.*,
                u.username,
                u.role,
                u.emoji,
                rc.old_total,
                rc.new_total,
                rc.delta_total,
                rc.comment AS delta_comment,
                rc.changed_at
            FROM ratings r
            JOIN users u ON u.id = r.user_id
            LEFT JOIN rating_changes rc ON rc.rating_id = r.id
            WHERE r.pnm_id = ?
            ORDER BY r.total_score DESC, r.updated_at DESC
            """,
            (pnm_id,),
        ).fetchall()

        lunch_rows = conn.execute(
            """
            SELECT l.lunch_date, l.notes, l.created_at, u.username, u.role
            FROM lunches l
            JOIN users u ON u.id = l.user_id
            WHERE l.pnm_id = ?
            ORDER BY l.lunch_date DESC, l.created_at DESC
            LIMIT 40
            """,
            (pnm_id,),
        ).fetchall()

        members = conn.execute(
            """
            SELECT id, username, role, emoji, stereotype, interests, interests_norm, total_lunches, lunches_per_week
            FROM users
            WHERE is_approved = 1
            ORDER BY username ASC
            """
        ).fetchall()

    can_view_identity = user["role"] in {ROLE_HEAD, ROLE_RUSH_OFFICER}
    ratings: list[dict[str, Any]] = []
    score_values: list[int] = []
    for row in rating_rows:
        entry = {
            "rating_id": row["id"],
            "from_me": row["user_id"] == user["id"],
            "total_score": int(row["total_score"]),
            "good_with_girls": int(row["good_with_girls"]),
            "will_make_it": int(row["will_make_it"]),
            "personable": int(row["personable"]),
            "alcohol_control": int(row["alcohol_control"]),
            "instagram_marketability": int(row["instagram_marketability"]),
            "updated_at": row["updated_at"],
            "last_change": (
                {
                    "old_total": row["old_total"],
                    "new_total": row["new_total"],
                    "delta_total": row["delta_total"],
                    "comment": row["delta_comment"],
                    "changed_at": row["changed_at"],
                }
                if row["changed_at"]
                else None
            ),
        }
        if can_view_identity:
            entry["rater"] = {"username": row["username"], "role": row["role"], "emoji": row["emoji"]}
            entry["comment"] = row["comment"]
        elif row["user_id"] == user["id"]:
            entry["comment"] = row["comment"]
        ratings.append(entry)
        score_values.append(int(row["total_score"]))

    pnm_interest_norm = split_normalized_csv(pnm_row["interests_norm"])
    pnm_stereotype_norm = pnm_row["stereotype"].strip().lower()
    matches: list[dict[str, Any]] = []
    for member in members:
        member_interest_norm = split_normalized_csv(member["interests_norm"])
        shared_norm = sorted(pnm_interest_norm & member_interest_norm)
        stereotype_match = member["stereotype"].strip().lower() == pnm_stereotype_norm
        fit_score = len(shared_norm) * 2 + (1 if stereotype_match else 0)
        if fit_score <= 0:
            continue
        shared_display = []
        member_interests_display = decode_interests(member["interests"])
        for interest in member_interests_display:
            if interest.lower() in shared_norm:
                shared_display.append(interest)

        matches.append(
            {
                "user_id": member["id"],
                "username": member["username"],
                "role": member["role"],
                "emoji": member["emoji"] if member["role"] == ROLE_RUSH_OFFICER else None,
                "stereotype": member["stereotype"],
                "shared_interests": shared_display,
                "stereotype_match": stereotype_match,
                "fit_score": fit_score,
                "lunches_per_week": round(float(member["lunches_per_week"]), 2),
            }
        )

    matches.sort(key=lambda item: (item["fit_score"], item["lunches_per_week"]), reverse=True)
    summary = {
        "ratings_count": len(score_values),
        "highest_rating_total": max(score_values) if score_values else None,
        "lowest_rating_total": min(score_values) if score_values else None,
        "weighted_total": round(float(pnm_row["weighted_total"]), 2),
        "total_lunches": int(pnm_row["total_lunches"]),
    }

    return {
        "pnm": pnm_payload(pnm_row, own),
        "can_view_rater_identity": can_view_identity,
        "summary": summary,
        "ratings": ratings,
        "lunches": [
            {
                "lunch_date": row["lunch_date"],
                "notes": row["notes"],
                "created_at": row["created_at"],
                "username": row["username"],
                "role": row["role"],
            }
            for row in lunch_rows
        ],
        "matches": matches[:10],
    }


@app.delete("/api/pnms/{pnm_id}")
def delete_pnm(pnm_id: int, _: sqlite3.Row = Depends(require_head)) -> dict[str, str]:
    with db_session() as conn:
        row = conn.execute("SELECT id, pnm_code, first_name, last_name, photo_path FROM pnms WHERE id = ?", (pnm_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="PNM not found.")

        rating_users = conn.execute("SELECT DISTINCT user_id FROM ratings WHERE pnm_id = ?", (pnm_id,)).fetchall()
        lunch_users = conn.execute("SELECT DISTINCT user_id FROM lunches WHERE pnm_id = ?", (pnm_id,)).fetchall()
        affected_users = {int(item["user_id"]) for item in rating_users + lunch_users}
        photo_path = row["photo_path"]
        display_name = f"{row['first_name']} {row['last_name']}"

        conn.execute("DELETE FROM pnms WHERE id = ?", (pnm_id,))
        for user_id in affected_users:
            recalc_member_rating_stats(conn, user_id)
            recalc_member_lunch_stats(conn, user_id)

    remove_photo_if_present(photo_path)
    return {"message": f"Deleted PNM {display_name} ({row['pnm_code']})."}


@app.post("/api/ratings")
def upsert_rating(payload: RatingUpsertRequest, user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    score_data = {
        "good_with_girls": payload.good_with_girls,
        "will_make_it": payload.will_make_it,
        "personable": payload.personable,
        "alcohol_control": payload.alcohol_control,
        "instagram_marketability": payload.instagram_marketability,
    }
    new_total = score_total(score_data)

    with db_session() as conn:
        pnm_row = conn.execute("SELECT id FROM pnms WHERE id = ?", (payload.pnm_id,)).fetchone()
        if not pnm_row:
            raise HTTPException(status_code=404, detail="PNM not found.")

        existing = conn.execute(
            "SELECT * FROM ratings WHERE pnm_id = ? AND user_id = ?",
            (payload.pnm_id, user["id"]),
        ).fetchone()

        now = now_iso()
        change_event: dict[str, Any] | None = None

        if existing:
            old_payload = {
                "good_with_girls": existing["good_with_girls"],
                "will_make_it": existing["will_make_it"],
                "personable": existing["personable"],
                "alcohol_control": existing["alcohol_control"],
                "instagram_marketability": existing["instagram_marketability"],
                "total_score": existing["total_score"],
            }
            changed = any(old_payload[field] != score_data[field] for field in RATING_FIELDS)

            if changed:
                comment = (payload.comment or "").strip()
                if count_words(comment) <= 5:
                    raise HTTPException(
                        status_code=400,
                        detail="Updating an existing rating requires a comment longer than 5 words.",
                    )
            else:
                comment = existing["comment"]

            conn.execute(
                """
                UPDATE ratings
                SET
                    good_with_girls = ?,
                    will_make_it = ?,
                    personable = ?,
                    alcohol_control = ?,
                    instagram_marketability = ?,
                    total_score = ?,
                    comment = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    payload.good_with_girls,
                    payload.will_make_it,
                    payload.personable,
                    payload.alcohol_control,
                    payload.instagram_marketability,
                    new_total,
                    comment,
                    now,
                    existing["id"],
                ),
            )

            if changed:
                new_payload = {
                    "good_with_girls": payload.good_with_girls,
                    "will_make_it": payload.will_make_it,
                    "personable": payload.personable,
                    "alcohol_control": payload.alcohol_control,
                    "instagram_marketability": payload.instagram_marketability,
                    "total_score": new_total,
                }
                delta_total = new_total - int(existing["total_score"])
                conn.execute(
                    """
                    INSERT INTO rating_changes (
                        rating_id,
                        pnm_id,
                        user_id,
                        old_total,
                        new_total,
                        delta_total,
                        old_payload,
                        new_payload,
                        comment,
                        changed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(rating_id) DO UPDATE SET
                        pnm_id = excluded.pnm_id,
                        user_id = excluded.user_id,
                        old_total = excluded.old_total,
                        new_total = excluded.new_total,
                        delta_total = excluded.delta_total,
                        old_payload = excluded.old_payload,
                        new_payload = excluded.new_payload,
                        comment = excluded.comment,
                        changed_at = excluded.changed_at
                    """,
                    (
                        existing["id"],
                        payload.pnm_id,
                        user["id"],
                        int(existing["total_score"]),
                        new_total,
                        delta_total,
                        json.dumps(old_payload),
                        json.dumps(new_payload),
                        comment,
                        now,
                    ),
                )
                change_event = {
                    "old_total": int(existing["total_score"]),
                    "new_total": new_total,
                    "delta_total": delta_total,
                    "comment": comment,
                    "changed_at": now,
                }
        else:
            conn.execute(
                """
                INSERT INTO ratings (
                    pnm_id,
                    user_id,
                    good_with_girls,
                    will_make_it,
                    personable,
                    alcohol_control,
                    instagram_marketability,
                    total_score,
                    comment,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.pnm_id,
                    user["id"],
                    payload.good_with_girls,
                    payload.will_make_it,
                    payload.personable,
                    payload.alcohol_control,
                    payload.instagram_marketability,
                    new_total,
                    (payload.comment or "").strip(),
                    now,
                    now,
                ),
            )

        recalc_pnm_rating_stats(conn, payload.pnm_id)
        recalc_member_rating_stats(conn, user["id"])

        updated_rating = conn.execute(
            "SELECT * FROM ratings WHERE pnm_id = ? AND user_id = ?",
            (payload.pnm_id, user["id"]),
        ).fetchone()

        updated_pnm = conn.execute("SELECT * FROM pnms WHERE id = ?", (payload.pnm_id,)).fetchone()
        updated_user = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()

    return {
        "rating": rating_payload(updated_rating),
        "change": change_event,
        "pnm": pnm_payload(updated_pnm, rating_payload(updated_rating)),
        "member": user_payload(updated_user, updated_user["role"], updated_user["id"]),
    }


@app.get("/api/pnms/{pnm_id}/ratings")
def pnm_ratings(pnm_id: int, user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    with db_session() as conn:
        target = conn.execute("SELECT id FROM pnms WHERE id = ?", (pnm_id,)).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="PNM not found.")

        rows = conn.execute(
            """
            SELECT
                r.*,
                u.username,
                u.role,
                u.emoji,
                rc.old_total,
                rc.new_total,
                rc.delta_total,
                rc.comment AS delta_comment,
                rc.changed_at
            FROM ratings r
            JOIN users u ON u.id = r.user_id
            LEFT JOIN rating_changes rc ON rc.rating_id = r.id
            WHERE r.pnm_id = ?
            ORDER BY r.total_score DESC, r.updated_at DESC
            """,
            (pnm_id,),
        ).fetchall()

    can_view_identity = user["role"] in {ROLE_HEAD, ROLE_RUSH_OFFICER}
    response_rows: list[dict[str, Any]] = []

    for row in rows:
        entry = {
            "rating_id": row["id"],
            "pnm_id": row["pnm_id"],
            "from_me": row["user_id"] == user["id"],
            "good_with_girls": row["good_with_girls"],
            "will_make_it": row["will_make_it"],
            "personable": row["personable"],
            "alcohol_control": row["alcohol_control"],
            "instagram_marketability": row["instagram_marketability"],
            "total_score": row["total_score"],
            "updated_at": row["updated_at"],
        }

        if can_view_identity:
            entry["rater"] = {
                "username": row["username"],
                "role": row["role"],
                "emoji": row["emoji"],
            }
            entry["comment"] = row["comment"]
            entry["last_change"] = (
                {
                    "old_total": row["old_total"],
                    "new_total": row["new_total"],
                    "delta_total": row["delta_total"],
                    "comment": row["delta_comment"],
                    "changed_at": row["changed_at"],
                }
                if row["changed_at"]
                else None
            )
        else:
            if row["user_id"] == user["id"]:
                entry["comment"] = row["comment"]
                entry["last_change"] = (
                    {
                        "old_total": row["old_total"],
                        "new_total": row["new_total"],
                        "delta_total": row["delta_total"],
                        "comment": row["delta_comment"],
                        "changed_at": row["changed_at"],
                    }
                    if row["changed_at"]
                    else None
                )

        response_rows.append(entry)

    return {
        "can_view_rater_identity": can_view_identity,
        "ratings": response_rows,
    }


@app.post("/api/lunches")
def create_lunch(payload: LunchCreateRequest, user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    with db_session() as conn:
        pnm = conn.execute("SELECT id FROM pnms WHERE id = ?", (payload.pnm_id,)).fetchone()
        if not pnm:
            raise HTTPException(status_code=404, detail="PNM not found.")

        try:
            conn.execute(
                "INSERT INTO lunches (pnm_id, user_id, lunch_date, notes, created_at) VALUES (?, ?, ?, ?, ?)",
                (payload.pnm_id, user["id"], payload.lunch_date, payload.notes.strip(), now_iso()),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(
                status_code=409,
                detail="Duplicate lunch log for this member, PNM, and date is not allowed.",
            ) from exc

        recalc_member_lunch_stats(conn, user["id"])
        recalc_pnm_lunch_stats(conn, payload.pnm_id)

        refreshed_user = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
        refreshed_pnm = conn.execute("SELECT * FROM pnms WHERE id = ?", (payload.pnm_id,)).fetchone()

    return {
        "message": "Lunch logged.",
        "member": user_payload(refreshed_user, refreshed_user["role"], refreshed_user["id"]),
        "pnm": pnm_payload(refreshed_pnm, own_rating=None),
    }


@app.get("/api/pnms/{pnm_id}/lunches")
def pnm_lunches(pnm_id: int, _: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    with db_session() as conn:
        target = conn.execute("SELECT id FROM pnms WHERE id = ?", (pnm_id,)).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="PNM not found.")

        rows = conn.execute(
            """
            SELECT l.lunch_date, l.notes, l.created_at, u.username
            FROM lunches l
            JOIN users u ON u.id = l.user_id
            WHERE l.pnm_id = ?
            ORDER BY l.lunch_date DESC, l.created_at DESC
            LIMIT 50
            """,
            (pnm_id,),
        ).fetchall()

    return {
        "lunches": [
            {
                "lunch_date": row["lunch_date"],
                "notes": row["notes"],
                "created_at": row["created_at"],
                "username": row["username"],
            }
            for row in rows
        ]
    }


@app.get("/api/matching")
def matching(
    interest: str | None = None,
    stereotype: str | None = None,
    user: sqlite3.Row = Depends(current_user),
) -> dict[str, Any]:
    try:
        interest_filter = parse_interest_filter(interest)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    normalized_stereotype = stereotype.strip().lower() if stereotype else None

    with db_session() as conn:
        own_rows = conn.execute("SELECT * FROM ratings WHERE user_id = ?", (user["id"],)).fetchall()
        own_rating_by_pnm = {row["pnm_id"]: rating_payload(row) for row in own_rows}

        pnm_rows = conn.execute(
            "SELECT * FROM pnms ORDER BY weighted_total DESC, last_name ASC, first_name ASC"
        ).fetchall()
        user_rows = conn.execute(
            "SELECT * FROM users WHERE is_approved = 1 ORDER BY username ASC"
        ).fetchall()

    pnms = []
    for row in pnm_rows:
        if normalized_stereotype and row["stereotype"].lower() != normalized_stereotype:
            continue
        if not has_interest_match(row["interests_norm"], interest_filter):
            continue
        pnms.append(pnm_payload(row, own_rating_by_pnm.get(row["id"])))

    members = []
    for row in user_rows:
        if normalized_stereotype and row["stereotype"].lower() != normalized_stereotype:
            continue
        if not has_interest_match(row["interests_norm"], interest_filter):
            continue
        members.append(user_payload(row, user["role"], user["id"]))

    return {
        "filters": {
            "interest": sorted(list(interest_filter)),
            "stereotype": stereotype.strip() if stereotype else "",
        },
        "pnms": pnms,
        "members": members,
    }


@app.get("/api/analytics/overview")
def analytics_overview(user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    with db_session() as conn:
        top_pnms = conn.execute(
            """
            SELECT id, pnm_code, first_name, last_name, weighted_total, rating_count, total_lunches
            FROM pnms
            ORDER BY weighted_total DESC, rating_count DESC
            LIMIT 10
            """
        ).fetchall()

        members = conn.execute(
            "SELECT * FROM users WHERE is_approved = 1 ORDER BY rating_count DESC, total_lunches DESC LIMIT 15"
        ).fetchall()

    return {
        "top_pnms": [
            {
                "pnm_id": row["id"],
                "pnm_code": row["pnm_code"],
                "name": f"{row['first_name']} {row['last_name']}",
                "weighted_total": round(float(row["weighted_total"]), 2),
                "rating_count": int(row["rating_count"]),
                "total_lunches": int(row["total_lunches"]),
            }
            for row in top_pnms
        ],
        "member_participation": [user_payload(row, user["role"], user["id"]) for row in members],
    }


@app.get("/api/interests")
def list_interests(_: sqlite3.Row = Depends(current_user)) -> dict[str, list[str]]:
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT interests FROM users WHERE is_approved = 1
            UNION ALL
            SELECT interests FROM pnms
            """
        ).fetchall()

    values: set[str] = set()
    for row in rows:
        for interest in decode_interests(row["interests"]):
            values.add(interest)

    return {"interests": sorted(values)}
