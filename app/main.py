from __future__ import annotations

import hmac
import hashlib
import io
import json
import base64
import os
import re
import secrets
import sqlite3
import time
import zipfile
import contextvars
from contextlib import contextmanager
from dataclasses import dataclass
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
TENANT_UPLOADS_ROOT = UPLOADS_DIR / "tenants"
TENANTS_DB_DIR = Path(os.getenv("TENANTS_DB_DIR", str(DB_PATH.parent / "tenants")))
MAX_PNM_PHOTO_BYTES = int(os.getenv("MAX_PNM_PHOTO_BYTES", str(4 * 1024 * 1024)))
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", str(UPLOADS_DIR / "backups")))
MAX_BACKUP_FILES = int(os.getenv("MAX_BACKUP_FILES", "30"))
SESSION_COOKIE = "rush_session"
PLATFORM_SESSION_COOKIE = "platform_session"
HASH_SCHEME = os.getenv("HASH_SCHEME", "pbkdf2_sha256")
PASSWORD_ITERATIONS = int(os.getenv("PASSWORD_ITERATIONS", "260000"))
LEGACY_AUTH_SALT = os.getenv("LEGACY_AUTH_SALT", "kao-rush-v1")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "43200"))
PLATFORM_SESSION_TTL_SECONDS = int(os.getenv("PLATFORM_SESSION_TTL_SECONDS", str(SESSION_TTL_SECONDS)))
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0").strip().lower() in {"1", "true", "yes"}
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "strict").strip().lower()
ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "*").split(",") if host.strip()]
LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", "300"))
LOGIN_MAX_FAILURES = int(os.getenv("LOGIN_MAX_FAILURES", "8"))
LOGIN_BLOCK_SECONDS = int(os.getenv("LOGIN_BLOCK_SECONDS", "600"))
PLATFORM_DB_PATH = Path(os.getenv("PLATFORM_DB_PATH", str(DB_PATH.parent / "platform.db")))
DEFAULT_TENANT_SLUG = os.getenv("DEFAULT_TENANT_SLUG", "kappaalphaorder").strip().lower() or "kappaalphaorder"
DEFAULT_TENANT_NAME = os.getenv("DEFAULT_TENANT_NAME", "Kappa Alpha Order").strip() or "Kappa Alpha Order"
PLATFORM_ADMIN_USERNAME = os.getenv("PLATFORM_ADMIN_USERNAME", "taylortaut").strip() or "taylortaut"
PLATFORM_ADMIN_ACCESS_CODE = os.getenv("PLATFORM_ADMIN_ACCESS_CODE", "").strip()
HEAD_SEED_ACCESS_CODE = os.getenv("HEAD_SEED_ACCESS_CODE", "").strip()
HEAD_SEED_USERNAME = os.getenv("HEAD_SEED_USERNAME", "head.rush.officer").strip() or "head.rush.officer"
HEAD_SEED_FIRST_NAME = os.getenv("HEAD_SEED_FIRST_NAME", "Head").strip() or "Head"
HEAD_SEED_LAST_NAME = os.getenv("HEAD_SEED_LAST_NAME", "Officer").strip() or "Officer"
HEAD_SEED_PLEDGE_CLASS = os.getenv("HEAD_SEED_PLEDGE_CLASS", "Admin").strip() or "Admin"
AUTO_CREATE_HEAD_SEED = os.getenv("AUTO_CREATE_HEAD_SEED", "1").strip().lower() in {"1", "true", "yes"}

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
TENANT_UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
TENANTS_DB_DIR.mkdir(parents=True, exist_ok=True)

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
GENERATED_PLATFORM_ADMIN_ACCESS_CODE: str | None = None


@dataclass(frozen=True)
class TenantContext:
    slug: str
    display_name: str
    chapter_name: str
    logo_path: str | None
    theme_primary: str
    theme_secondary: str
    db_path: Path
    pnm_uploads_dir: Path
    backup_dir: Path


CURRENT_TENANT: contextvars.ContextVar[TenantContext | None] = contextvars.ContextVar("current_tenant", default=None)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_epoch() -> float:
    return time.time()


def normalize_samesite(value: str) -> str:
    if value in {"lax", "strict", "none"}:
        return value
    return "strict"


def normalize_slug(value: str) -> str:
    slug = value.strip().lower()
    if not re.fullmatch(r"[a-z0-9-]{3,64}", slug):
        raise ValueError("Slug must use lowercase letters, numbers, and hyphens only.")
    return slug


def normalize_theme_color(value: str, fallback: str) -> str:
    raw = value.strip() if value else fallback
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", raw):
        return fallback
    return raw.lower()


def default_tenant_db_path(slug: str) -> Path:
    if slug == DEFAULT_TENANT_SLUG:
        return DB_PATH
    return TENANTS_DB_DIR / f"{slug}.db"


@contextmanager
def platform_db_session() -> sqlite3.Connection:
    PLATFORM_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(PLATFORM_DB_PATH)
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


def current_tenant() -> TenantContext:
    tenant = CURRENT_TENANT.get()
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant context missing.")
    return tenant


def active_db_path() -> Path:
    tenant = CURRENT_TENANT.get()
    if tenant:
        return tenant.db_path
    return DB_PATH


def active_backup_dir() -> Path:
    tenant = CURRENT_TENANT.get()
    if tenant:
        return tenant.backup_dir
    return BACKUP_DIR


def active_pnm_uploads_dir() -> Path:
    tenant = CURRENT_TENANT.get()
    if tenant:
        return tenant.pnm_uploads_dir
    return UPLOADS_DIR / "pnms"


def tenant_logo_public_path(slug: str, extension: str) -> str:
    return f"/uploads/tenants/{slug}/branding/logo{extension}"


def tenant_logo_fs_dir(slug: str) -> Path:
    return TENANT_UPLOADS_ROOT / slug / "branding"


def tenant_context_from_row(row: sqlite3.Row) -> TenantContext:
    slug = row["slug"]
    db_path = Path(row["db_path"])
    return TenantContext(
        slug=slug,
        display_name=row["display_name"],
        chapter_name=row["chapter_name"] or "",
        logo_path=row["logo_path"],
        theme_primary=normalize_theme_color(row["theme_primary"] or "", "#8a1538"),
        theme_secondary=normalize_theme_color(row["theme_secondary"] or "", "#c99a2b"),
        db_path=db_path,
        pnm_uploads_dir=TENANT_UPLOADS_ROOT / slug / "pnms",
        backup_dir=TENANT_UPLOADS_ROOT / slug / "backups",
    )


def platform_user_payload(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "username": row["username"],
        "last_login_at": row["last_login_at"],
        "created_at": row["created_at"],
    }


def list_tenants_rows() -> list[sqlite3.Row]:
    with platform_db_session() as conn:
        return conn.execute(
            """
            SELECT *
            FROM tenants
            WHERE is_active = 1
            ORDER BY display_name ASC
            """
        ).fetchall()


def fetch_tenant_row(slug: str) -> sqlite3.Row | None:
    with platform_db_session() as conn:
        return conn.execute(
            "SELECT * FROM tenants WHERE slug = ? AND is_active = 1",
            (slug,),
        ).fetchone()


def require_tenant_exists(slug: str) -> sqlite3.Row:
    row = fetch_tenant_row(slug)
    if not row:
        raise HTTPException(status_code=404, detail="Organization not found.")
    return row


def app_config_for_tenant(tenant: TenantContext) -> dict[str, str | None]:
    return {
        "base_path": f"/{tenant.slug}",
        "api_base": f"/{tenant.slug}/api",
        "meeting_base": f"/{tenant.slug}/meeting",
        "platform_base": "/platform",
        "mobile_base": f"/{tenant.slug}/mobile",
        "tenant_slug": tenant.slug,
        "tenant_name": tenant.display_name,
        "chapter_name": tenant.chapter_name,
        "logo_path": tenant.logo_path,
        "theme_primary": tenant.theme_primary,
        "theme_secondary": tenant.theme_secondary,
    }


def vcard_escape(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("\n", "\\n")
    escaped = escaped.replace(";", "\\;").replace(",", "\\,")
    return escaped


def fold_vcard_line(line: str, limit: int = 75) -> str:
    if len(line) <= limit:
        return line
    chunks = [line[:limit]]
    remainder = line[limit:]
    while remainder:
        chunks.append(f" {remainder[:limit-1]}")
        remainder = remainder[limit - 1 :]
    return "\r\n".join(chunks)


def build_pnm_vcard(row: sqlite3.Row, tenant_name: str) -> str:
    first_name = row["first_name"] or ""
    last_name = row["last_name"] or ""
    full_name = f"{first_name} {last_name}".strip() or row["pnm_code"]
    org_name = f"PNM ({tenant_name})"
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        fold_vcard_line(f"N:{vcard_escape(last_name)};{vcard_escape(first_name)};;;"),
        fold_vcard_line(f"FN:{vcard_escape(full_name)}"),
        fold_vcard_line(f"ORG:{vcard_escape(org_name)}"),
    ]

    phone = (row["phone_number"] or "").strip()
    if phone:
        lines.append(fold_vcard_line(f"TEL;TYPE=CELL:{vcard_escape(phone)}"))

    ig = (row["instagram_handle"] or "").strip()
    if ig:
        ig_name = ig[1:] if ig.startswith("@") else ig
        lines.append(fold_vcard_line(f"item1.URL:https://instagram.com/{vcard_escape(ig_name)}"))
        lines.append("item1.X-ABLabel:Instagram")

    photo_path = row["photo_path"]
    fs_path = photo_fs_path(photo_path)
    if fs_path and fs_path.exists() and fs_path.is_file():
        raw = fs_path.read_bytes()
        photo_type = "JPEG"
        suffix = fs_path.suffix.lower()
        if suffix == ".png":
            photo_type = "PNG"
        elif suffix == ".webp":
            photo_type = "WEBP"
        encoded = base64.b64encode(raw).decode("ascii")
        lines.append(fold_vcard_line(f"PHOTO;ENCODING=b;TYPE={photo_type}:{encoded}"))

    lines.append("END:VCARD")
    return "\r\n".join(lines)


def current_platform_admin(request: Request) -> sqlite3.Row:
    token = request.cookies.get(PLATFORM_SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")

    with platform_db_session() as conn:
        row = conn.execute(
            """
            SELECT pa.*, ps.last_seen_at
            FROM platform_sessions ps
            JOIN platform_admins pa ON pa.id = ps.admin_id
            WHERE ps.token = ?
            """,
            (token,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.")

        try:
            last_seen_dt = datetime.fromisoformat(row["last_seen_at"])
        except (TypeError, ValueError):
            conn.execute("DELETE FROM platform_sessions WHERE token = ?", (token,))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.")
        if (datetime.now(timezone.utc) - last_seen_dt).total_seconds() > PLATFORM_SESSION_TTL_SECONDS:
            conn.execute("DELETE FROM platform_sessions WHERE token = ?", (token,))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.")

        conn.execute("UPDATE platform_sessions SET last_seen_at = ? WHERE token = ?", (now_iso(), token))
        return row


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


@app.middleware("http")
async def tenant_resolution(request: Request, call_next):  # type: ignore[no-untyped-def]
    path = request.scope.get("path", "/")
    bypass_prefixes = ("/static", "/uploads", "/platform", "/health")
    if path == "/" or path.startswith(bypass_prefixes):
        return await call_next(request)

    token = None
    resolved_row: sqlite3.Row | None = None
    rewritten_path = path

    if path.startswith("/api/") or path == "/api":
        resolved_row = fetch_tenant_row(DEFAULT_TENANT_SLUG)
    else:
        trimmed = path.strip("/")
        first = trimmed.split("/", 1)[0].lower() if trimmed else ""
        if first:
            candidate = fetch_tenant_row(first)
            if candidate:
                resolved_row = candidate
                remainder = trimmed[len(first):].lstrip("/")
                rewritten_path = f"/{remainder}" if remainder else "/"

    if not resolved_row:
        return await call_next(request)

    tenant = tenant_context_from_row(resolved_row)
    request.state.tenant = tenant
    token = CURRENT_TENANT.set(tenant)
    original_path = request.scope.get("path", "/")
    request.scope["path"] = rewritten_path
    try:
        return await call_next(request)
    finally:
        request.scope["path"] = original_path
        if token is not None:
            CURRENT_TENANT.reset(token)


@contextmanager
def db_session(db_path: Path | None = None) -> sqlite3.Connection:
    target = db_path if db_path else active_db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
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


def normalize_phone_number(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""
    if not re.fullmatch(r"[0-9+(). -]{7,22}", raw):
        raise ValueError("Phone number contains invalid characters.")
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 7:
        raise ValueError("Phone number must include at least 7 digits.")
    return raw


def public_photo_url(photo_path: str | None) -> str | None:
    if not photo_path:
        return None
    if photo_path.startswith("/uploads/"):
        return photo_path
    return None


def photo_fs_path(photo_path: str | None) -> Path | None:
    tenant = CURRENT_TENANT.get()
    if not photo_path:
        return None
    name = Path(photo_path).name
    if not name:
        return None
    if tenant and photo_path.startswith(f"/uploads/tenants/{tenant.slug}/pnms/"):
        return active_pnm_uploads_dir() / name
    if photo_path.startswith("/uploads/pnms/"):
        return UPLOADS_DIR / "pnms" / name
    return None


def remove_photo_if_present(photo_path: str | None) -> None:
    target = photo_fs_path(photo_path)
    if target and target.exists() and target.is_file():
        target.unlink(missing_ok=True)


def split_normalized_csv(value: str) -> set[str]:
    return {token for token in value.split(",") if token}


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def prune_backup_files(prefix: str) -> None:
    backup_dir = active_backup_dir()
    if not backup_dir.exists():
        return
    files = sorted(backup_dir.glob(f"{prefix}-*.sqlite"), key=lambda path: path.stat().st_mtime, reverse=True)
    for stale in files[MAX_BACKUP_FILES:]:
        stale.unlink(missing_ok=True)


def create_sqlite_snapshot(prefix: str = "snapshot") -> Path:
    backup_dir = active_backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{prefix}-{timestamp_slug()}.sqlite"
    source = sqlite3.connect(active_db_path())
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
    db_path = active_db_path()
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
            f"Database path: {db_path}\n"
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
            phone_number TEXT NOT NULL DEFAULT '',
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
            assigned_officer_id INTEGER REFERENCES users(id),
            assigned_by INTEGER REFERENCES users(id),
            assigned_at TEXT,
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
        CREATE INDEX IF NOT EXISTS idx_pnms_assigned_officer ON pnms(assigned_officer_id);
        """
    )


def ensure_schema_upgrades(conn: sqlite3.Connection) -> None:
    pnm_columns = {row["name"] for row in conn.execute("PRAGMA table_info(pnms)").fetchall()}
    if "phone_number" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN phone_number TEXT NOT NULL DEFAULT ''")
    if "photo_path" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN photo_path TEXT")
    if "photo_uploaded_at" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN photo_uploaded_at TEXT")
    if "photo_uploaded_by" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN photo_uploaded_by INTEGER REFERENCES users(id)")
    if "assigned_officer_id" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN assigned_officer_id INTEGER REFERENCES users(id)")
    if "assigned_by" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN assigned_by INTEGER REFERENCES users(id)")
    if "assigned_at" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN assigned_at TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pnms_assigned_officer ON pnms(assigned_officer_id)")


def ensure_seed_data(
    conn: sqlite3.Connection,
    *,
    seed_username: str | None = None,
    seed_access_code: str | None = None,
    seed_first_name: str | None = None,
    seed_last_name: str | None = None,
    seed_pledge_class: str | None = None,
) -> None:
    if not AUTO_CREATE_HEAD_SEED:
        return

    username = (seed_username or HEAD_SEED_USERNAME).strip() or HEAD_SEED_USERNAME
    first_name = (seed_first_name or HEAD_SEED_FIRST_NAME).strip() or HEAD_SEED_FIRST_NAME
    last_name = (seed_last_name or HEAD_SEED_LAST_NAME).strip() or HEAD_SEED_LAST_NAME
    pledge_class = (seed_pledge_class or HEAD_SEED_PLEDGE_CLASS).strip() or HEAD_SEED_PLEDGE_CLASS
    access_code = seed_access_code if seed_access_code is not None else HEAD_SEED_ACCESS_CODE

    interests, interests_norm = encode_interests(["Leadership", "Recruitment"])
    created_at = now_iso()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
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
        if access_code:
            conn.execute(
                "UPDATE users SET access_code_hash = ?, updated_at = ? WHERE id = ?",
                (hash_access_code(access_code), now_iso(), existing["id"]),
            )
        return

    seed_access_code = access_code if access_code else resolve_seed_access_code()
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
            username,
            first_name,
            last_name,
            pledge_class,
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


def resolve_platform_admin_access_code() -> str:
    global GENERATED_PLATFORM_ADMIN_ACCESS_CODE
    if PLATFORM_ADMIN_ACCESS_CODE:
        return PLATFORM_ADMIN_ACCESS_CODE
    if GENERATED_PLATFORM_ADMIN_ACCESS_CODE:
        return GENERATED_PLATFORM_ADMIN_ACCESS_CODE
    GENERATED_PLATFORM_ADMIN_ACCESS_CODE = secrets.token_urlsafe(16)
    print(
        "[startup] PLATFORM_ADMIN_ACCESS_CODE not provided. Generated bootstrap platform admin credentials:\n"
        f"          username={PLATFORM_ADMIN_USERNAME}\n"
        f"          access_code={GENERATED_PLATFORM_ADMIN_ACCESS_CODE}\n"
        "          Set PLATFORM_ADMIN_ACCESS_CODE in production to disable random generation."
    )
    return GENERATED_PLATFORM_ADMIN_ACCESS_CODE


def setup_platform_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS platform_admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            access_code_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_login_at TEXT
        );

        CREATE TABLE IF NOT EXISTS platform_sessions (
            token TEXT PRIMARY KEY,
            admin_id INTEGER NOT NULL REFERENCES platform_admins(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            chapter_name TEXT NOT NULL DEFAULT '',
            logo_path TEXT,
            theme_primary TEXT NOT NULL DEFAULT '#8a1538',
            theme_secondary TEXT NOT NULL DEFAULT '#c99a2b',
            db_path TEXT NOT NULL,
            head_seed_username TEXT NOT NULL,
            head_seed_first_name TEXT NOT NULL,
            head_seed_last_name TEXT NOT NULL,
            head_seed_pledge_class TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(slug);
        """
    )


def ensure_platform_admin_seed(conn: sqlite3.Connection) -> None:
    created_at = now_iso()
    seed_access_code = resolve_platform_admin_access_code()
    existing = conn.execute("SELECT id FROM platform_admins WHERE username = ?", (PLATFORM_ADMIN_USERNAME,)).fetchone()
    if existing:
        if PLATFORM_ADMIN_ACCESS_CODE:
            conn.execute(
                "UPDATE platform_admins SET access_code_hash = ?, updated_at = ? WHERE id = ?",
                (hash_access_code(seed_access_code), created_at, existing["id"]),
            )
        return

    conn.execute(
        """
        INSERT INTO platform_admins (username, access_code_hash, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        """,
        (PLATFORM_ADMIN_USERNAME, hash_access_code(seed_access_code), created_at, created_at),
    )


def ensure_default_tenant_record(conn: sqlite3.Connection) -> sqlite3.Row:
    created_at = now_iso()
    default_db_path = default_tenant_db_path(DEFAULT_TENANT_SLUG)
    row = conn.execute("SELECT * FROM tenants WHERE slug = ?", (DEFAULT_TENANT_SLUG,)).fetchone()
    if row:
        conn.execute(
            """
            UPDATE tenants
            SET
                display_name = ?,
                db_path = ?,
                head_seed_username = ?,
                head_seed_first_name = ?,
                head_seed_last_name = ?,
                head_seed_pledge_class = ?,
                is_active = 1,
                updated_at = ?
            WHERE slug = ?
            """,
            (
                DEFAULT_TENANT_NAME,
                str(default_db_path),
                HEAD_SEED_USERNAME,
                HEAD_SEED_FIRST_NAME,
                HEAD_SEED_LAST_NAME,
                HEAD_SEED_PLEDGE_CLASS,
                created_at,
                DEFAULT_TENANT_SLUG,
            ),
        )
        return conn.execute("SELECT * FROM tenants WHERE slug = ?", (DEFAULT_TENANT_SLUG,)).fetchone()

    conn.execute(
        """
        INSERT INTO tenants (
            slug,
            display_name,
            chapter_name,
            logo_path,
            theme_primary,
            theme_secondary,
            db_path,
            head_seed_username,
            head_seed_first_name,
            head_seed_last_name,
            head_seed_pledge_class,
            created_at,
            updated_at,
            is_active
        )
        VALUES (?, ?, ?, NULL, '#8a1538', '#c99a2b', ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            DEFAULT_TENANT_SLUG,
            DEFAULT_TENANT_NAME,
            "KAO",
            str(default_db_path),
            HEAD_SEED_USERNAME,
            HEAD_SEED_FIRST_NAME,
            HEAD_SEED_LAST_NAME,
            HEAD_SEED_PLEDGE_CLASS,
            created_at,
            created_at,
        ),
    )
    return conn.execute("SELECT * FROM tenants WHERE slug = ?", (DEFAULT_TENANT_SLUG,)).fetchone()


def initialize_tenant_datastore(row: sqlite3.Row, seed_access_code: str | None = None) -> None:
    ctx = tenant_context_from_row(row)
    ctx.pnm_uploads_dir.mkdir(parents=True, exist_ok=True)
    ctx.backup_dir.mkdir(parents=True, exist_ok=True)
    with db_session(ctx.db_path) as tenant_conn:
        setup_schema(tenant_conn)
        ensure_schema_upgrades(tenant_conn)
        ensure_seed_data(
            tenant_conn,
            seed_username=row["head_seed_username"],
            seed_access_code=seed_access_code,
            seed_first_name=row["head_seed_first_name"],
            seed_last_name=row["head_seed_last_name"],
            seed_pledge_class=row["head_seed_pledge_class"],
        )


def bootstrap_platform_and_tenants() -> None:
    PLATFORM_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    TENANTS_DB_DIR.mkdir(parents=True, exist_ok=True)
    TENANT_UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    with platform_db_session() as conn:
        setup_platform_schema(conn)
        ensure_platform_admin_seed(conn)
        ensure_default_tenant_record(conn)
        tenant_rows = conn.execute("SELECT * FROM tenants WHERE is_active = 1").fetchall()

    for row in tenant_rows:
        seed_access = HEAD_SEED_ACCESS_CODE if row["slug"] == DEFAULT_TENANT_SLUG else None
        initialize_tenant_datastore(row, seed_access_code=seed_access)


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


def pnm_payload(
    row: sqlite3.Row,
    own_rating: dict[str, Any] | None,
    assigned_officer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    days_since_event = (date.today() - date.fromisoformat(row["first_event_date"])).days
    return {
        "pnm_id": row["id"],
        "pnm_code": row["pnm_code"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "class_year": row["class_year"],
        "hometown": row["hometown"],
        "phone_number": row["phone_number"] if "phone_number" in row.keys() else "",
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
        "assigned_officer_id": row["assigned_officer_id"] if "assigned_officer_id" in row.keys() else None,
        "assigned_officer": assigned_officer,
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


def assigned_officer_payload_from_row(row: sqlite3.Row) -> dict[str, Any] | None:
    keys = set(row.keys())
    if "assigned_officer_id" not in keys or row["assigned_officer_id"] is None:
        return None
    username = row["assigned_officer_username"] if "assigned_officer_username" in keys else None
    role = row["assigned_officer_role"] if "assigned_officer_role" in keys else ROLE_RUSH_OFFICER
    emoji = row["assigned_officer_emoji"] if "assigned_officer_emoji" in keys else None
    return {
        "user_id": row["assigned_officer_id"],
        "username": username,
        "role": role,
        "emoji": emoji,
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
    phone_number: str = Field(default="", max_length=32)
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


class AssignOfficerRequest(BaseModel):
    officer_user_id: int | None = None


class PlatformLoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=120)
    access_code: str = Field(..., min_length=8, max_length=128)


class TenantCreateRequest(BaseModel):
    slug: str
    display_name: str = Field(..., min_length=3, max_length=120)
    chapter_name: str = Field(..., min_length=2, max_length=24)
    head_seed_username: str = Field(..., min_length=3, max_length=120)
    head_seed_first_name: str = Field(..., min_length=1, max_length=48)
    head_seed_last_name: str = Field(..., min_length=1, max_length=48)
    head_seed_pledge_class: str = Field(..., min_length=1, max_length=24)
    head_seed_access_code: str = Field(..., min_length=8, max_length=128)
    theme_primary: str | None = None
    theme_secondary: str | None = None


@app.on_event("startup")
def startup() -> None:
    bootstrap_platform_and_tenants()
    default_row = fetch_tenant_row(DEFAULT_TENANT_SLUG)
    if default_row:
        tenant = tenant_context_from_row(default_row)
        token = CURRENT_TENANT.set(tenant)
        try:
            if tenant.db_path.exists():
                try:
                    create_sqlite_snapshot(prefix="startup")
                except Exception:
                    print("[startup] warning: unable to create startup snapshot.")
        finally:
            CURRENT_TENANT.reset(token)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    tenant = getattr(request.state, "tenant", None)
    if tenant:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "tenant": tenant,
                "app_config": app_config_for_tenant(tenant),
            },
        )

    tenants = [tenant_context_from_row(row) for row in list_tenants_rows()]
    return templates.TemplateResponse(
        "platform_home.html",
        {
            "request": request,
            "tenants": tenants,
            "default_slug": DEFAULT_TENANT_SLUG,
        },
    )


@app.get("/meeting", response_class=HTMLResponse)
async def meeting_page(request: Request) -> HTMLResponse:
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization context required.")
    return templates.TemplateResponse(
        "meeting.html",
        {
            "request": request,
            "tenant": tenant,
            "app_config": app_config_for_tenant(tenant),
        },
    )


@app.get("/mobile", response_class=HTMLResponse)
async def mobile_home_page(request: Request) -> HTMLResponse:
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization context required.")
    return templates.TemplateResponse(
        "mobile_home.html",
        {
            "request": request,
            "tenant": tenant,
            "app_config": app_config_for_tenant(tenant),
            "mobile_page": "home",
        },
    )


@app.get("/mobile/pnms", response_class=HTMLResponse)
async def mobile_pnms_page(request: Request) -> HTMLResponse:
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization context required.")
    return templates.TemplateResponse(
        "mobile_pnms.html",
        {
            "request": request,
            "tenant": tenant,
            "app_config": app_config_for_tenant(tenant),
            "mobile_page": "pnms",
        },
    )


@app.get("/mobile/create", response_class=HTMLResponse)
async def mobile_create_page(request: Request) -> HTMLResponse:
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization context required.")
    return templates.TemplateResponse(
        "mobile_create.html",
        {
            "request": request,
            "tenant": tenant,
            "app_config": app_config_for_tenant(tenant),
            "mobile_page": "create",
        },
    )


@app.get("/mobile/members", response_class=HTMLResponse)
async def mobile_members_page(request: Request) -> HTMLResponse:
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization context required.")
    return templates.TemplateResponse(
        "mobile_members.html",
        {
            "request": request,
            "tenant": tenant,
            "app_config": app_config_for_tenant(tenant),
            "mobile_page": "members",
        },
    )


@app.get("/mobile/meeting", response_class=HTMLResponse)
async def mobile_meeting_page(request: Request) -> HTMLResponse:
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization context required.")
    return templates.TemplateResponse(
        "mobile_meeting.html",
        {
            "request": request,
            "tenant": tenant,
            "app_config": app_config_for_tenant(tenant),
            "mobile_page": "meeting",
        },
    )


@app.get("/platform", response_class=HTMLResponse)
async def platform_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("platform_admin.html", {"request": request})


def tenant_admin_payload(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "slug": row["slug"],
        "display_name": row["display_name"],
        "chapter_name": row["chapter_name"],
        "logo_path": row["logo_path"],
        "theme_primary": row["theme_primary"],
        "theme_secondary": row["theme_secondary"],
        "db_path": row["db_path"],
        "head_seed_username": row["head_seed_username"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@app.post("/platform/api/auth/login")
def platform_login(payload: PlatformLoginRequest, request: Request, response: Response) -> dict[str, Any]:
    ip_address = client_ip(request)
    assert_login_allowed(ip_address)

    with platform_db_session() as conn:
        row = conn.execute("SELECT * FROM platform_admins WHERE username = ?", (payload.username.strip(),)).fetchone()
        if not row:
            record_login_failure(ip_address)
            raise HTTPException(status_code=401, detail="Invalid username or access code.")

        password_ok, needs_upgrade = verify_access_code(payload.access_code, row["access_code_hash"])
        if not password_ok:
            record_login_failure(ip_address)
            raise HTTPException(status_code=401, detail="Invalid username or access code.")

        token = secrets.token_urlsafe(32)
        now = now_iso()
        conn.execute(
            "INSERT INTO platform_sessions (token, admin_id, created_at, last_seen_at) VALUES (?, ?, ?, ?)",
            (token, row["id"], now, now),
        )
        conn.execute("UPDATE platform_admins SET last_login_at = ?, updated_at = ? WHERE id = ?", (now, now, row["id"]))
        if needs_upgrade:
            conn.execute(
                "UPDATE platform_admins SET access_code_hash = ?, updated_at = ? WHERE id = ?",
                (hash_access_code(payload.access_code), now_iso(), row["id"]),
            )

    response.set_cookie(
        key=PLATFORM_SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite=normalize_samesite(SESSION_COOKIE_SAMESITE),
        max_age=PLATFORM_SESSION_TTL_SECONDS,
        secure=SESSION_COOKIE_SECURE,
        path="/",
    )
    record_login_success(ip_address)
    return {"admin": platform_user_payload(row), "message": "Platform admin logged in."}


@app.post("/platform/api/auth/logout")
def platform_logout(request: Request, response: Response) -> dict[str, str]:
    token = request.cookies.get(PLATFORM_SESSION_COOKIE)
    if token:
        with platform_db_session() as conn:
            conn.execute("DELETE FROM platform_sessions WHERE token = ?", (token,))
    response.delete_cookie(
        key=PLATFORM_SESSION_COOKIE,
        path="/",
        secure=SESSION_COOKIE_SECURE,
        samesite=normalize_samesite(SESSION_COOKIE_SAMESITE),
    )
    return {"message": "Logged out."}


@app.get("/platform/api/auth/me")
def platform_auth_me(admin: sqlite3.Row = Depends(current_platform_admin)) -> dict[str, Any]:
    return {"authenticated": True, "admin": platform_user_payload(admin)}


@app.get("/platform/api/tenants")
def platform_list_tenants(_: sqlite3.Row = Depends(current_platform_admin)) -> dict[str, Any]:
    with platform_db_session() as conn:
        rows = conn.execute("SELECT * FROM tenants ORDER BY display_name ASC").fetchall()
    return {"tenants": [tenant_admin_payload(row) for row in rows]}


@app.post("/platform/api/tenants")
def platform_create_tenant(payload: TenantCreateRequest, _: sqlite3.Row = Depends(current_platform_admin)) -> dict[str, Any]:
    slug = normalize_slug(payload.slug)
    display_name = payload.display_name.strip()
    chapter_name = payload.chapter_name.strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="Display name is required.")
    if not chapter_name:
        raise HTTPException(status_code=400, detail="Chapter name is required.")

    theme_primary = normalize_theme_color(payload.theme_primary or "", "#8a1538")
    theme_secondary = normalize_theme_color(payload.theme_secondary or "", "#c99a2b")
    head_username = payload.head_seed_username.strip()
    if not head_username:
        raise HTTPException(status_code=400, detail="Head username is required.")
    try:
        validate_access_code_strength(payload.head_seed_access_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    tenant_db_path = default_tenant_db_path(slug)
    created_at = now_iso()
    with platform_db_session() as conn:
        existing = conn.execute("SELECT id FROM tenants WHERE slug = ?", (slug,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Organization slug already exists.")
        conn.execute(
            """
            INSERT INTO tenants (
                slug,
                display_name,
                chapter_name,
                logo_path,
                theme_primary,
                theme_secondary,
                db_path,
                head_seed_username,
                head_seed_first_name,
                head_seed_last_name,
                head_seed_pledge_class,
                created_at,
                updated_at,
                is_active
            )
            VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                slug,
                display_name,
                chapter_name,
                theme_primary,
                theme_secondary,
                str(tenant_db_path),
                head_username,
                normalize_name(payload.head_seed_first_name),
                normalize_name(payload.head_seed_last_name),
                payload.head_seed_pledge_class.strip(),
                created_at,
                created_at,
            ),
        )
        row = conn.execute("SELECT * FROM tenants WHERE slug = ?", (slug,)).fetchone()

    initialize_tenant_datastore(row, seed_access_code=payload.head_seed_access_code.strip())
    return {"tenant": tenant_admin_payload(row), "message": "Organization created."}


@app.post("/platform/api/tenants/{slug}/logo")
async def platform_upload_tenant_logo(
    slug: str,
    logo: UploadFile = File(...),
    _: sqlite3.Row = Depends(current_platform_admin),
) -> dict[str, Any]:
    normalized_slug = normalize_slug(slug)
    row = require_tenant_exists(normalized_slug)

    content_type = (logo.content_type or "").lower().strip()
    extension = ALLOWED_PHOTO_TYPES.get(content_type)
    if extension is None:
        raise HTTPException(status_code=400, detail="Unsupported logo type. Use JPG, PNG, or WEBP.")

    content = await logo.read(MAX_PNM_PHOTO_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Logo file cannot be empty.")
    if len(content) > MAX_PNM_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail=f"Logo too large. Max size is {MAX_PNM_PHOTO_BYTES // (1024 * 1024)} MB.")

    logo_dir = tenant_logo_fs_dir(normalized_slug)
    logo_dir.mkdir(parents=True, exist_ok=True)
    for prior in logo_dir.glob("logo.*"):
        prior.unlink(missing_ok=True)
    target = logo_dir / f"logo{extension}"
    target.write_bytes(content)
    public_path = tenant_logo_public_path(normalized_slug, extension)

    with platform_db_session() as conn:
        conn.execute("UPDATE tenants SET logo_path = ?, updated_at = ? WHERE slug = ?", (public_path, now_iso(), normalized_slug))
        refreshed = conn.execute("SELECT * FROM tenants WHERE slug = ?", (normalized_slug,)).fetchone()
    return {"tenant": tenant_admin_payload(refreshed), "message": "Logo uploaded."}


@app.delete("/platform/api/tenants/{slug}")
def platform_disable_tenant(slug: str, _: sqlite3.Row = Depends(current_platform_admin)) -> dict[str, str]:
    normalized_slug = normalize_slug(slug)
    if normalized_slug == DEFAULT_TENANT_SLUG:
        raise HTTPException(status_code=400, detail="Default organization cannot be disabled.")
    with platform_db_session() as conn:
        row = conn.execute("SELECT id FROM tenants WHERE slug = ?", (normalized_slug,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Organization not found.")
        conn.execute("UPDATE tenants SET is_active = 0, updated_at = ? WHERE slug = ?", (now_iso(), normalized_slug))
    return {"message": "Organization disabled."}


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


@app.get("/api/export/contacts.vcf")
def export_contacts_vcf(_: sqlite3.Row = Depends(current_user)) -> Response:
    tenant = CURRENT_TENANT.get()
    if tenant is None:
        default_row = require_tenant_exists(DEFAULT_TENANT_SLUG)
        tenant = tenant_context_from_row(default_row)

    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT first_name, last_name, pnm_code, phone_number, instagram_handle, photo_path
            FROM pnms
            ORDER BY last_name ASC, first_name ASC
            """
        ).fetchall()

    cards = [build_pnm_vcard(row, tenant.display_name) for row in rows]
    payload = ("\r\n".join(cards) + ("\r\n" if cards else "")).encode("utf-8")
    filename = f"pnm-contacts-{tenant.slug}-{timestamp_slug()}.vcf"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=payload, media_type="text/vcard; charset=utf-8", headers=headers)


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
        phone_number = normalize_phone_number(payload.phone_number)
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
                phone_number,
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
            VALUES ('TBD', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                first_name,
                last_name,
                payload.class_year,
                hometown,
                phone_number,
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

    return {"pnm": pnm_payload(row, own_rating=None, assigned_officer=None)}


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
            """
            SELECT
                p.*,
                ao.id AS assigned_officer_id,
                ao.username AS assigned_officer_username,
                ao.role AS assigned_officer_role,
                ao.emoji AS assigned_officer_emoji
            FROM pnms p
            LEFT JOIN users ao ON ao.id = p.assigned_officer_id
            ORDER BY p.weighted_total DESC, p.last_name ASC, p.first_name ASC
            """
        ).fetchall()

    filtered = []
    for row in rows:
        if normalized_stereotype and row["stereotype"].lower() != normalized_stereotype:
            continue
        if not has_interest_match(row["interests_norm"], interest_filter):
            continue
        filtered.append(
            pnm_payload(
                row,
                own_rating_by_pnm.get(row["id"]),
                assigned_officer=assigned_officer_payload_from_row(row),
            )
        )

    return {"pnms": filtered}


@app.get("/api/pnms/{pnm_id}")
def get_pnm(pnm_id: int, user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT
                p.*,
                ao.id AS assigned_officer_id,
                ao.username AS assigned_officer_username,
                ao.role AS assigned_officer_role,
                ao.emoji AS assigned_officer_emoji
            FROM pnms p
            LEFT JOIN users ao ON ao.id = p.assigned_officer_id
            WHERE p.id = ?
            """,
            (pnm_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="PNM not found.")
        own = fetch_own_rating(conn, pnm_id, user["id"])
    return {"pnm": pnm_payload(row, own, assigned_officer=assigned_officer_payload_from_row(row))}


@app.post("/api/pnms/{pnm_id}/assign")
def assign_pnm_officer(
    pnm_id: int,
    payload: AssignOfficerRequest,
    head_user: sqlite3.Row = Depends(require_head),
) -> dict[str, Any]:
    with db_session() as conn:
        pnm_row = conn.execute("SELECT * FROM pnms WHERE id = ?", (pnm_id,)).fetchone()
        if not pnm_row:
            raise HTTPException(status_code=404, detail="PNM not found.")

        assigned_user_id: int | None = payload.officer_user_id
        if assigned_user_id is not None:
            officer = conn.execute(
                "SELECT id, username, role, emoji FROM users WHERE id = ? AND is_approved = 1",
                (assigned_user_id,),
            ).fetchone()
            if not officer:
                raise HTTPException(status_code=404, detail="Rush Officer not found.")
            if officer["role"] != ROLE_RUSH_OFFICER:
                raise HTTPException(status_code=400, detail="Assignment target must be a Rush Officer.")
        else:
            officer = None

        now = now_iso()
        conn.execute(
            """
            UPDATE pnms
            SET assigned_officer_id = ?, assigned_by = ?, assigned_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                assigned_user_id,
                head_user["id"] if assigned_user_id is not None else None,
                now if assigned_user_id is not None else None,
                now,
                pnm_id,
            ),
        )

        refreshed = conn.execute(
            """
            SELECT
                p.*,
                ao.id AS assigned_officer_id,
                ao.username AS assigned_officer_username,
                ao.role AS assigned_officer_role,
                ao.emoji AS assigned_officer_emoji
            FROM pnms p
            LEFT JOIN users ao ON ao.id = p.assigned_officer_id
            WHERE p.id = ?
            """,
            (pnm_id,),
        ).fetchone()
        own = fetch_own_rating(conn, pnm_id, head_user["id"])

    return {
        "message": "PNM assignment updated.",
        "pnm": pnm_payload(refreshed, own, assigned_officer=assigned_officer_payload_from_row(refreshed)),
    }


@app.post("/api/pnms/{pnm_id}/photo")
async def upload_pnm_photo(
    pnm_id: int,
    photo: UploadFile = File(...),
    user: sqlite3.Row = Depends(require_officer),
) -> dict[str, Any]:
    tenant = current_tenant()
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
    uploads_dir = active_pnm_uploads_dir()
    uploads_dir.mkdir(parents=True, exist_ok=True)
    target_path = uploads_dir / filename
    public_path = f"/uploads/tenants/{tenant.slug}/pnms/{filename}"
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

            refreshed = conn.execute(
                """
                SELECT
                    p.*,
                    ao.id AS assigned_officer_id,
                    ao.username AS assigned_officer_username,
                    ao.role AS assigned_officer_role,
                    ao.emoji AS assigned_officer_emoji
                FROM pnms p
                LEFT JOIN users ao ON ao.id = p.assigned_officer_id
                WHERE p.id = ?
                """,
                (pnm_id,),
            ).fetchone()
            own = fetch_own_rating(conn, pnm_id, user["id"])
    except Exception:
        target_path.unlink(missing_ok=True)
        raise

    if old_photo_path and old_photo_path != public_path:
        remove_photo_if_present(old_photo_path)

    return {
        "message": "PNM photo uploaded.",
        "pnm": pnm_payload(refreshed, own, assigned_officer=assigned_officer_payload_from_row(refreshed)),
    }


@app.get("/api/pnms/{pnm_id}/meeting")
def pnm_meeting_view(pnm_id: int, user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    with db_session() as conn:
        pnm_row = conn.execute(
            """
            SELECT
                p.*,
                ao.id AS assigned_officer_id,
                ao.username AS assigned_officer_username,
                ao.role AS assigned_officer_role,
                ao.emoji AS assigned_officer_emoji
            FROM pnms p
            LEFT JOIN users ao ON ao.id = p.assigned_officer_id
            WHERE p.id = ?
            """,
            (pnm_id,),
        ).fetchone()
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
        "pnm": pnm_payload(pnm_row, own, assigned_officer=assigned_officer_payload_from_row(pnm_row)),
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

        updated_pnm = conn.execute(
            """
            SELECT
                p.*,
                ao.id AS assigned_officer_id,
                ao.username AS assigned_officer_username,
                ao.role AS assigned_officer_role,
                ao.emoji AS assigned_officer_emoji
            FROM pnms p
            LEFT JOIN users ao ON ao.id = p.assigned_officer_id
            WHERE p.id = ?
            """,
            (payload.pnm_id,),
        ).fetchone()
        updated_user = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()

    return {
        "rating": rating_payload(updated_rating),
        "change": change_event,
        "pnm": pnm_payload(
            updated_pnm,
            rating_payload(updated_rating),
            assigned_officer=assigned_officer_payload_from_row(updated_pnm),
        ),
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
        refreshed_pnm = conn.execute(
            """
            SELECT
                p.*,
                ao.id AS assigned_officer_id,
                ao.username AS assigned_officer_username,
                ao.role AS assigned_officer_role,
                ao.emoji AS assigned_officer_emoji
            FROM pnms p
            LEFT JOIN users ao ON ao.id = p.assigned_officer_id
            WHERE p.id = ?
            """,
            (payload.pnm_id,),
        ).fetchone()

    return {
        "message": "Lunch logged.",
        "member": user_payload(refreshed_user, refreshed_user["role"], refreshed_user["id"]),
        "pnm": pnm_payload(
            refreshed_pnm,
            own_rating=None,
            assigned_officer=assigned_officer_payload_from_row(refreshed_pnm),
        ),
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
            """
            SELECT
                p.*,
                ao.id AS assigned_officer_id,
                ao.username AS assigned_officer_username,
                ao.role AS assigned_officer_role,
                ao.emoji AS assigned_officer_emoji
            FROM pnms p
            LEFT JOIN users ao ON ao.id = p.assigned_officer_id
            ORDER BY p.weighted_total DESC, p.last_name ASC, p.first_name ASC
            """
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
        pnms.append(
            pnm_payload(
                row,
                own_rating_by_pnm.get(row["id"]),
                assigned_officer=assigned_officer_payload_from_row(row),
            )
        )

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
