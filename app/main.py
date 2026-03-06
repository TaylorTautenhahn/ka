from __future__ import annotations

import hmac
import hashlib
import html
import ipaddress
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
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any
import csv

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator, model_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware
from urllib.error import HTTPError, URLError
from urllib.request import Request as URLRequest, urlopen

try:
    import segno
except Exception:  # pragma: no cover - optional dependency in local dev before install
    segno = None

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency
    Image = None


BASE_DIR = Path(__file__).resolve().parent


def resolve_data_root() -> Path:
    configured = os.getenv("DATA_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser()

    data_mount = Path("/data")
    if data_mount.exists() and data_mount.is_dir() and os.access(data_mount, os.W_OK):
        return data_mount / "ka-rush"

    return BASE_DIR


DATA_ROOT = resolve_data_root()
DB_PATH = Path(os.getenv("DB_PATH", str(DATA_ROOT / "recruitment.db")))
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", str(DATA_ROOT / "uploads")))
TENANT_UPLOADS_ROOT = UPLOADS_DIR / "tenants"
TENANTS_DB_DIR = Path(os.getenv("TENANTS_DB_DIR", str(DATA_ROOT / "tenants")))
MAX_PNM_PHOTO_BYTES = int(os.getenv("MAX_PNM_PHOTO_BYTES", str(4 * 1024 * 1024)))
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", str(DATA_ROOT / "backups")))
MAX_BACKUP_FILES = int(os.getenv("MAX_BACKUP_FILES", "30"))
SESSION_COOKIE = "rush_session"
PLATFORM_SESSION_COOKIE = "platform_session"
CSRF_COOKIE = "bb_csrf_token"
CSRF_HEADER = "x-csrf-token"
HASH_SCHEME = os.getenv("HASH_SCHEME", "pbkdf2_sha256")
PASSWORD_ITERATIONS = int(os.getenv("PASSWORD_ITERATIONS", "260000"))
LEGACY_AUTH_SALT = os.getenv("LEGACY_AUTH_SALT", "kao-rush-v1")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "43200"))
SESSION_REMEMBER_TTL_SECONDS = int(os.getenv("SESSION_REMEMBER_TTL_SECONDS", str(60 * 60 * 24 * 30)))
PLATFORM_SESSION_TTL_SECONDS = int(os.getenv("PLATFORM_SESSION_TTL_SECONDS", str(SESSION_TTL_SECONDS)))
PLATFORM_SESSION_REMEMBER_TTL_SECONDS = int(
    os.getenv("PLATFORM_SESSION_REMEMBER_TTL_SECONDS", str(60 * 60 * 24 * 14))
)
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0").strip().lower() in {"1", "true", "yes"}
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "strict").strip().lower()
ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,::1").split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [origin.strip().rstrip("/") for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]
ENFORCE_CSRF = os.getenv("ENFORCE_CSRF", "1").strip().lower() in {"1", "true", "yes"}
TRUST_X_FORWARDED_FOR = os.getenv("TRUST_X_FORWARDED_FOR", "0").strip().lower() in {"1", "true", "yes"}
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
ENABLE_API_DOCS = os.getenv("ENABLE_API_DOCS", "0").strip().lower() in {"1", "true", "yes"}
LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", "300"))
LOGIN_MAX_FAILURES = int(os.getenv("LOGIN_MAX_FAILURES", "8"))
LOGIN_BLOCK_SECONDS = int(os.getenv("LOGIN_BLOCK_SECONDS", "600"))
REQUIRE_PERSISTENT_DATA = os.getenv("REQUIRE_PERSISTENT_DATA", "0").strip().lower() in {"1", "true", "yes"}
PLATFORM_DB_PATH = Path(os.getenv("PLATFORM_DB_PATH", str(DATA_ROOT / "platform.db")))
DEFAULT_TENANT_SLUG = os.getenv("DEFAULT_TENANT_SLUG", "kappaalphaorder").strip().lower() or "kappaalphaorder"
DEFAULT_TENANT_NAME = os.getenv("DEFAULT_TENANT_NAME", "Kappa Alpha Order").strip() or "Kappa Alpha Order"
DEMO_ENABLED = os.getenv("DEMO_ENABLED", "1").strip().lower() in {"1", "true", "yes"}
DEMO_AUTO_LOGIN = os.getenv("DEMO_AUTO_LOGIN", "1").strip().lower() in {"1", "true", "yes"}
DEMO_TENANT_SLUG_RAW = os.getenv("DEMO_TENANT_SLUG", "bidboarddemo").strip().lower() or "bidboarddemo"
DEMO_TENANT_NAME = os.getenv("DEMO_TENANT_NAME", "BidBoard Demo").strip() or "BidBoard Demo"
DEMO_TENANT_CHAPTER_NAME = os.getenv("DEMO_TENANT_CHAPTER_NAME", "Demo").strip() or "Demo"
DEMO_HEAD_USERNAME = os.getenv("DEMO_HEAD_USERNAME", "demohead").strip() or "demohead"
DEMO_HEAD_FIRST_NAME = os.getenv("DEMO_HEAD_FIRST_NAME", "Demo").strip() or "Demo"
DEMO_HEAD_LAST_NAME = os.getenv("DEMO_HEAD_LAST_NAME", "Head").strip() or "Head"
DEMO_HEAD_PLEDGE_CLASS = os.getenv("DEMO_HEAD_PLEDGE_CLASS", "Demo").strip() or "Demo"
DEMO_HEAD_ACCESS_CODE = os.getenv("DEMO_HEAD_ACCESS_CODE", "DemoHead123!").strip() or "DemoHead123!"
PLATFORM_ADMIN_USERNAME = os.getenv("PLATFORM_ADMIN_USERNAME", "taylortaut").strip() or "taylortaut"
PLATFORM_ADMIN_ACCESS_CODE = os.getenv("PLATFORM_ADMIN_ACCESS_CODE", "").strip()
HEAD_SEED_ACCESS_CODE = os.getenv("HEAD_SEED_ACCESS_CODE", "").strip()
HEAD_SEED_USERNAME = os.getenv("HEAD_SEED_USERNAME", "chapteradmin").strip() or "chapteradmin"
HEAD_SEED_FIRST_NAME = os.getenv("HEAD_SEED_FIRST_NAME", "Head").strip() or "Head"
HEAD_SEED_LAST_NAME = os.getenv("HEAD_SEED_LAST_NAME", "Officer").strip() or "Officer"
HEAD_SEED_PLEDGE_CLASS = os.getenv("HEAD_SEED_PLEDGE_CLASS", "Admin").strip() or "Admin"
AUTO_CREATE_HEAD_SEED = os.getenv("AUTO_CREATE_HEAD_SEED", "1").strip().lower() in {"1", "true", "yes"}
CALENDAR_TIMEZONE = os.getenv("CALENDAR_TIMEZONE", "America/Chicago").strip() or "America/Chicago"
MAX_GOOGLE_FORM_IMPORT_BYTES = int(os.getenv("MAX_GOOGLE_FORM_IMPORT_BYTES", str(3 * 1024 * 1024)))
INSTAGRAM_AVATAR_TIMEOUT_SECONDS = float(os.getenv("INSTAGRAM_AVATAR_TIMEOUT_SECONDS", "4.0"))
INSTAGRAM_PROFILE_HTML_MAX_BYTES = int(os.getenv("INSTAGRAM_PROFILE_HTML_MAX_BYTES", "1200000"))
INSTAGRAM_API_RESPONSE_MAX_BYTES = int(os.getenv("INSTAGRAM_API_RESPONSE_MAX_BYTES", "1200000"))
INSTAGRAM_WEB_APP_ID = os.getenv("INSTAGRAM_WEB_APP_ID", "936619743392459").strip() or "936619743392459"
SEASON_RESET_CONFIRMATION_PHRASE = os.getenv("SEASON_RESET_CONFIRMATION_PHRASE", "RESET RUSH SEASON").strip() or "RESET RUSH SEASON"
SEASON_ARCHIVE_FILENAME = "season-archive-latest.sqlite"
VCARD_PHOTO_MAX_BYTES = int(os.getenv("VCARD_PHOTO_MAX_BYTES", str(550_000)))

DATA_ROOT.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
TENANT_UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
TENANTS_DB_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

ROLE_HEAD = "Head Rush Officer"
ROLE_RUSH_OFFICER = "Rush Officer"
ROLE_RUSHER = "Rusher"
ALLOWED_ROLES = {ROLE_HEAD, ROLE_RUSH_OFFICER, ROLE_RUSHER}
ROLE_SORT_ORDER: dict[str, int] = {
    ROLE_HEAD: 0,
    ROLE_RUSH_OFFICER: 1,
    ROLE_RUSHER: 2,
}
ONBOARDING_TUTORIAL_MODES = {"quick", "guided", "advanced"}
ONBOARDING_DEFAULT_MODE = "guided"
ONBOARDING_TUTORIAL_VERSION = 1
UNSAFE_HTTP_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
DEFAULT_RUSH_OFFICER_EMOJI = "⭐"
RUSH_EVENT_TYPES = {
    "official",
    "roundtable",
    "mixer",
    "philanthropy",
    "brotherhood",
    "interview",
    "meeting",
    "social",
    "other",
}
ENGAGEMENT_EVENT_TYPES = {
    "lunch",
    "rush_event",
    "meeting",
    "follow_up",
}
ENGAGEMENT_EVENT_STATUSES = {
    "planned",
    "attended",
    "no_show",
    "cancelled",
}
ASSIGNMENT_STATUSES = {
    "unassigned",
    "assigned",
    "in_progress",
    "completed",
    "needs_help",
}
ASSIGNMENT_STATUS_LABELS: dict[str, str] = {
    "unassigned": "Unassigned",
    "assigned": "Assigned",
    "in_progress": "In Progress",
    "completed": "Completed",
    "needs_help": "Needs Help",
}
ASSIGNMENT_DUE_SOON_DAYS = int(os.getenv("ASSIGNMENT_DUE_SOON_DAYS", "2"))
ASSIGNMENT_DEFAULT_PRIORITY = int(os.getenv("ASSIGNMENT_DEFAULT_PRIORITY", "3"))
ASSIGNMENT_MAX_PRIORITY = int(os.getenv("ASSIGNMENT_MAX_PRIORITY", "5"))
OFFICER_CAPACITY_TARGET = int(os.getenv("OFFICER_CAPACITY_TARGET", "8"))
PNM_FUNNEL_STAGES = (
    "sourced",
    "engaged",
    "evaluated",
    "discussed",
    "bid",
    "accepted",
    "declined",
)
WEEKLY_GOAL_METRIC_TYPES = {
    "manual",
    "ratings_submitted",
    "lunches_logged",
    "pnms_created",
    "chat_messages",
    "rush_events_created",
}
WEEKLY_GOAL_METRIC_LABELS: dict[str, str] = {
    "manual": "Manual Progress",
    "ratings_submitted": "Ratings Submitted",
    "lunches_logged": "Lunches Logged",
    "pnms_created": "PNMs Added",
    "chat_messages": "Chat Messages",
    "rush_events_created": "Rush Events Created",
}
DEFAULT_WEEKLY_GOAL_METRIC = "manual"
RATING_FIELDS = [
    "good_with_girls",
    "will_make_it",
    "personable",
    "alcohol_control",
    "instagram_marketability",
]
RATING_FIELD_LIMITS: dict[str, int] = {
    "good_with_girls": 10,
    "will_make_it": 10,
    "personable": 10,
    "alcohol_control": 10,
    "instagram_marketability": 5,
}
PNM_AVERAGE_COLUMN_BY_FIELD: dict[str, str] = {
    "good_with_girls": "avg_good_with_girls",
    "will_make_it": "avg_will_make_it",
    "personable": "avg_personable",
    "alcohol_control": "avg_alcohol_control",
    "instagram_marketability": "avg_instagram_marketability",
}
DEFAULT_RATING_CRITERIA: list[dict[str, Any]] = [
    {
        "field": "good_with_girls",
        "label": "Good with girls",
        "short_label": "Girls",
        "max": 10,
    },
    {
        "field": "will_make_it",
        "label": "Will make it through process",
        "short_label": "Process",
        "max": 10,
    },
    {
        "field": "personable",
        "label": "Personable",
        "short_label": "Personable",
        "max": 10,
    },
    {
        "field": "alcohol_control",
        "label": "Alcohol control",
        "short_label": "Alcohol",
        "max": 10,
    },
    {
        "field": "instagram_marketability",
        "label": "Instagram marketability",
        "short_label": "IG",
        "max": 5,
    },
]
DEFAULT_INTEREST_TAG_SUGGESTIONS = [
    "Leadership",
    "Academics",
    "Career",
    "Community",
    "Culture",
    "Service",
    "Sports",
    "Fitness",
    "Finance",
    "Business",
    "Outdoors",
    "Music",
    "Technology",
    "Wellness",
    "Faith",
    "Philanthropy",
    "Gaming",
    "Travel",
    "Food",
    "Fashion",
    "Entrepreneurship",
]
DEFAULT_STEREOTYPE_TAG_SUGGESTIONS = [
    "Leader",
    "Connector",
    "Scholar",
    "Athlete",
    "Social",
    "Creative",
    "Mentor",
    "Builder",
]
DEFAULT_THEME_PRIMARY = "#8a1538"
DEFAULT_THEME_SECONDARY = "#c99a2b"
DEFAULT_THEME_TERTIARY = "#1d7a4b"
DEFAULT_ORG_TYPE = "Fraternity"
ALLOWED_PHOTO_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
GOOGLE_FORM_TEMPLATE_COLUMNS = [
    "First Name",
    "Last Name",
    "Class Year (F/S/J)",
    "Hometown",
    "Phone Number",
    "Instagram Handle",
]
HTTP_USER_AGENT = os.getenv("HTTP_USER_AGENT", "Mozilla/5.0").strip() or "Mozilla/5.0"
ALLOWED_REMOTE_FETCH_HOSTS = {
    "instagram.com",
    "www.instagram.com",
    "i.instagram.com",
    "unavatar.io",
}
ALLOWED_REMOTE_FETCH_HOST_SUFFIXES = (
    ".instagram.com",
    ".cdninstagram.com",
    ".fbcdn.net",
)
GOOGLE_FORM_COLUMN_ALIASES = {
    "first_name": {
        "first name",
        "firstname",
        "first",
        "what is your first name",
    },
    "last_name": {
        "last name",
        "lastname",
        "last",
        "what is your last name",
    },
    "full_name": {
        "name",
        "full name",
        "fullname",
        "your name",
    },
    "class_year": {
        "class year",
        "classyear",
        "year",
        "classification",
        "grade",
        "what is your class year",
    },
    "hometown": {
        "hometown",
        "home town",
        "city",
        "where are you from",
    },
    "phone_number": {
        "phone",
        "phone number",
        "phonenumber",
        "mobile",
        "cell",
    },
    "instagram_handle": {
        "instagram",
        "instagram handle",
        "instagramhandle",
        "ig",
        "ig handle",
        "instagram username",
    },
}
US_STATE_CODE_TO_NAME: dict[str, str] = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
}
US_STATE_NAME_TO_CODE: dict[str, str] = {name.lower(): code for code, name in US_STATE_CODE_TO_NAME.items()}
US_STATE_NAME_TO_CODE.update(
    {
        "district columbia": "DC",
        "washington dc": "DC",
        "washington d c": "DC",
    }
)
US_STATE_NAMES_DESC: tuple[str, ...] = tuple(
    sorted(US_STATE_NAME_TO_CODE.keys(), key=lambda item: (-len(item), item))
)

app = FastAPI(
    title="KA Recruitment Evaluation",
    description="Connected, role-aware recruitment evaluation platform.",
    version="1.0.0",
    docs_url="/docs" if ENABLE_API_DOCS else None,
    redoc_url="/redoc" if ENABLE_API_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_API_DOCS else None,
)
app.add_middleware(GZipMiddleware, minimum_size=512)
if ALLOWED_HOSTS != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/uploads/tenants", StaticFiles(directory=TENANT_UPLOADS_ROOT), name="tenant_uploads")
LEGACY_PNM_UPLOADS_DIR = UPLOADS_DIR / "pnms"
LEGACY_PNM_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads/pnms", StaticFiles(directory=LEGACY_PNM_UPLOADS_DIR), name="legacy_pnm_uploads")
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
    org_type: str
    setup_tagline: str
    logo_path: str | None
    theme_primary: str
    theme_secondary: str
    theme_tertiary: str
    role_weight_officer: float
    role_weight_rusher: float
    rating_criteria: tuple[dict[str, Any], ...]
    rating_total_max: int
    default_interest_tags: tuple[str, ...]
    default_stereotype_tags: tuple[str, ...]
    db_path: Path
    pnm_uploads_dir: Path
    backup_dir: Path
    calendar_share_token: str


CURRENT_TENANT: contextvars.ContextVar[TenantContext | None] = contextvars.ContextVar("current_tenant", default=None)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_epoch() -> float:
    return time.time()


def uses_data_mount(path: Path) -> bool:
    raw = str(path.expanduser())
    return raw == "/data" or raw.startswith("/data/")


def collect_storage_warnings() -> list[str]:
    warnings: list[str] = []
    if not os.getenv("DATA_ROOT") and not os.getenv("DB_PATH") and DATA_ROOT == BASE_DIR:
        warnings.append(
            "Using local app directory for SQLite storage. Configure persistent DATA_ROOT/DB_PATH/UPLOADS_DIR in production."
        )
    if os.getenv("RENDER") and not uses_data_mount(DATA_ROOT):
        warnings.append(f"Render detected but DATA_ROOT is {DATA_ROOT} (expected /data or /data/*).")
    if uses_data_mount(DATA_ROOT):
        data_mount = Path("/data")
        if not data_mount.exists():
            warnings.append("DATA_ROOT targets /data but /data does not exist. Persistent disk may not be mounted.")
        elif not os.access(data_mount, os.W_OK):
            warnings.append("DATA_ROOT targets /data but /data is not writable.")
    if ALLOWED_HOSTS == ["*"]:
        warnings.append("ALLOWED_HOSTS is wildcard '*'. Configure explicit hostnames in production.")
    return warnings


def enforce_persistent_storage_if_required() -> None:
    if not REQUIRE_PERSISTENT_DATA:
        return

    issues: list[str] = []
    required_paths = {
        "DATA_ROOT": DATA_ROOT,
        "DB_PATH": DB_PATH,
        "PLATFORM_DB_PATH": PLATFORM_DB_PATH,
        "TENANTS_DB_DIR": TENANTS_DB_DIR,
        "UPLOADS_DIR": UPLOADS_DIR,
        "BACKUP_DIR": BACKUP_DIR,
    }
    for key, path in required_paths.items():
        if not uses_data_mount(path):
            issues.append(f"{key}={path} is not under /data")

    data_mount = Path("/data")
    if not data_mount.exists():
        issues.append("/data mount does not exist")
    elif not os.access(data_mount, os.W_OK):
        issues.append("/data mount is not writable")

    if issues:
        raise RuntimeError(
            "Persistent storage requirement failed. "
            + " | ".join(issues)
            + " | Mount a Render disk at /data and set DATA_ROOT=/data."
        )


def enforce_host_configuration_if_required() -> None:
    if ALLOWED_HOSTS != ["*"]:
        return
    if os.getenv("RENDER") or REQUIRE_PERSISTENT_DATA:
        raise RuntimeError(
            "Unsafe host configuration: ALLOWED_HOSTS='*' is not allowed in production. "
            "Set explicit hostnames, e.g. ALLOWED_HOSTS=ka-d6di.onrender.com,localhost,127.0.0.1."
        )


def production_bootstrap_mode() -> bool:
    return bool(os.getenv("RENDER")) or REQUIRE_PERSISTENT_DATA


def require_bootstrap_secret_configured(
    secret_value: str | None,
    *,
    env_name: str,
    principal_label: str,
    production_mode: bool | None = None,
) -> None:
    if (secret_value or "").strip():
        return
    should_enforce = production_bootstrap_mode() if production_mode is None else production_mode
    if not should_enforce:
        return
    raise RuntimeError(
        f"{principal_label} bootstrap secret is required for fresh production startup. "
        f"Set {env_name} before deploying a new datastore."
    )


def normalize_samesite(value: str) -> str:
    if value in {"lax", "strict", "none"}:
        return value
    return "strict"


def should_use_secure_cookie(request: Request) -> bool:
    if SESSION_COOKIE_SECURE:
        return True
    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    if forwarded_proto == "https":
        return True
    return request.url.scheme == "https"


def request_forwarded_proto(request: Request) -> str:
    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    if forwarded_proto in {"http", "https"}:
        return forwarded_proto
    return request.url.scheme.lower()


def request_host(request: Request) -> str:
    host = (request.headers.get("host") or "").split(",")[0].strip().lower()
    if host:
        return host
    if request.url.netloc:
        return request.url.netloc.lower()
    return ""


def request_origin(request: Request) -> str:
    host = request_host(request)
    if not host:
        return ""
    return f"{request_forwarded_proto(request)}://{host}"


def normalized_origin(value: str) -> str:
    token = (value or "").strip()
    if not token:
        return ""
    try:
        parsed = urlsplit(token)
    except ValueError:
        return ""
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        return ""
    netloc = (parsed.netloc or "").strip().lower()
    if not netloc:
        return ""
    return f"{scheme}://{netloc}"


def allowed_request_origins(request: Request) -> set[str]:
    allowed: set[str] = set()
    current = normalized_origin(request_origin(request))
    if current:
        allowed.add(current)
    if PUBLIC_BASE_URL:
        public = normalized_origin(PUBLIC_BASE_URL)
        if public:
            allowed.add(public)
    for item in CSRF_TRUSTED_ORIGINS:
        normalized = normalized_origin(item)
        if normalized:
            allowed.add(normalized)
    return allowed


def is_csrf_origin_allowed(origin_like: str, request: Request) -> bool:
    normalized = normalized_origin(origin_like)
    if not normalized:
        return False
    return normalized in allowed_request_origins(request)


def app_base_origin(request: Request) -> str:
    public = normalized_origin(PUBLIC_BASE_URL)
    if public:
        return public
    current = normalized_origin(request_origin(request))
    if current:
        return current
    return f"{request.url.scheme}://{request.url.netloc}".rstrip("/")


def issue_csrf_token() -> str:
    return secrets.token_urlsafe(24)


def set_csrf_cookie(response: Response, request: Request, token: str | None = None) -> str:
    csrf_token = token if token else issue_csrf_token()
    response.set_cookie(
        key=CSRF_COOKIE,
        value=csrf_token,
        httponly=False,
        samesite=normalize_samesite(SESSION_COOKIE_SAMESITE),
        secure=should_use_secure_cookie(request),
        path="/",
    )
    return csrf_token


def mark_response_private(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["Pragma"] = "no-cache"


def normalized_idle_ttl_seconds(raw_value: Any, fallback_seconds: int) -> int:
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        parsed = fallback_seconds
    return max(900, parsed)


def user_session_idle_seconds(remember_me: bool) -> int:
    return normalized_idle_ttl_seconds(
        SESSION_REMEMBER_TTL_SECONDS if remember_me else SESSION_TTL_SECONDS,
        SESSION_TTL_SECONDS,
    )


def platform_session_idle_seconds(remember_me: bool) -> int:
    return normalized_idle_ttl_seconds(
        PLATFORM_SESSION_REMEMBER_TTL_SECONDS if remember_me else PLATFORM_SESSION_TTL_SECONDS,
        PLATFORM_SESSION_TTL_SECONDS,
    )


def normalize_slug(value: str) -> str:
    slug = value.strip().lower()
    if not re.fullmatch(r"[a-z0-9-]{3,64}", slug):
        raise ValueError("Slug must use lowercase letters, numbers, and hyphens only.")
    return slug


def demo_tenant_slug() -> str:
    try:
        return normalize_slug(DEMO_TENANT_SLUG_RAW)
    except ValueError:
        return "bidboarddemo"


def is_demo_tenant_slug(slug: str) -> bool:
    return DEMO_ENABLED and slug == demo_tenant_slug()


def normalize_theme_color(value: str, fallback: str) -> str:
    raw = value.strip() if value else fallback
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", raw):
        return fallback
    return raw.lower()


def sanitize_short_text(value: str | None, fallback: str, *, max_length: int = 96) -> str:
    raw = (value or "").strip()
    if not raw:
        return fallback
    normalized = re.sub(r"\s+", " ", raw)
    if len(normalized) > max_length:
        normalized = normalized[:max_length].strip()
    return normalized or fallback


def parse_json_array(raw: Any) -> list[Any]:
    if isinstance(raw, list):
        return list(raw)
    if not isinstance(raw, str):
        return []
    token = raw.strip()
    if not token:
        return []
    try:
        decoded = json.loads(token)
    except (TypeError, ValueError):
        return []
    return list(decoded) if isinstance(decoded, list) else []


def default_rating_criteria() -> list[dict[str, Any]]:
    return [dict(item) for item in DEFAULT_RATING_CRITERIA]


def rating_criteria_by_field(criteria: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["field"]): item for item in criteria if isinstance(item, dict) and "field" in item}


def normalize_rating_criteria_config(raw: Any) -> list[dict[str, Any]]:
    by_field: dict[str, dict[str, Any]] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            if isinstance(value, dict):
                by_field[str(key)] = value
    else:
        for item in parse_json_array(raw) if isinstance(raw, str) else (raw if isinstance(raw, list) else []):
            if isinstance(item, dict) and item.get("field"):
                by_field[str(item["field"])] = item

    normalized: list[dict[str, Any]] = []
    for base in DEFAULT_RATING_CRITERIA:
        field = str(base["field"])
        candidate = by_field.get(field, {})
        max_limit = int(RATING_FIELD_LIMITS[field])
        max_value_raw = candidate.get("max", base["max"]) if isinstance(candidate, dict) else base["max"]
        try:
            max_value = int(max_value_raw)
        except (TypeError, ValueError):
            max_value = int(base["max"])
        max_value = max(1, min(max_limit, max_value))
        label = sanitize_short_text(
            candidate.get("label") if isinstance(candidate, dict) else None,
            str(base["label"]),
            max_length=60,
        )
        short_label = sanitize_short_text(
            candidate.get("short_label") if isinstance(candidate, dict) else None,
            str(base["short_label"]),
            max_length=20,
        )
        normalized.append(
            {
                "field": field,
                "label": label,
                "short_label": short_label,
                "max": max_value,
            }
        )
    return normalized


def rating_total_max(criteria: list[dict[str, Any]]) -> int:
    if not criteria:
        return int(sum(item["max"] for item in DEFAULT_RATING_CRITERIA))
    total = 0
    for item in criteria:
        try:
            total += int(item.get("max", 0))
        except (TypeError, ValueError):
            continue
    return max(1, total)


def parse_default_interest_tags(raw: Any) -> list[str]:
    source: list[Any]
    if isinstance(raw, list):
        source = raw
    else:
        source = parse_json_array(raw)
        if not source and isinstance(raw, str):
            source = [part.strip() for part in re.split(r"[,;\n]+", raw) if part.strip()]
    normalized: list[str] = []
    seen: set[str] = set()
    for item in source:
        try:
            value = normalize_interest(str(item))
        except ValueError:
            continue
        lowered = value.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(value)
    if not normalized:
        return list(DEFAULT_INTEREST_TAG_SUGGESTIONS)
    return normalized[:20]


def parse_default_stereotype_tags(raw: Any) -> list[str]:
    source: list[Any]
    if isinstance(raw, list):
        source = raw
    else:
        source = parse_json_array(raw)
        if not source and isinstance(raw, str):
            source = [part.strip() for part in re.split(r"[,;\n]+", raw) if part.strip()]
    normalized: list[str] = []
    seen: set[str] = set()
    for item in source:
        token = sanitize_short_text(str(item), "", max_length=32)
        if not token:
            continue
        lowered = token.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(token)
    if not normalized:
        return list(DEFAULT_STEREOTYPE_TAG_SUGGESTIONS)
    return normalized[:20]


def normalize_org_type(value: str | None) -> str:
    return sanitize_short_text(value, DEFAULT_ORG_TYPE, max_length=40)


def normalize_role_weights(officer: Any, rusher: Any) -> tuple[float, float]:
    def _parse(raw: Any, fallback: float) -> float:
        try:
            parsed = float(raw)
        except (TypeError, ValueError):
            parsed = fallback
        if parsed <= 0:
            return fallback
        return min(parsed, 1.0)

    officer_weight = _parse(officer, 0.6)
    rusher_weight = _parse(rusher, 0.4)
    if officer_weight + rusher_weight <= 0:
        return 0.6, 0.4
    return officer_weight, rusher_weight


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


def file_metadata(path: Path) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "uses_data_mount": uses_data_mount(path),
    }
    if path.exists():
        stat = path.stat()
        entry["size_bytes"] = int(stat.st_size)
        entry["modified_at"] = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
    return entry


def tenant_logo_public_path(slug: str, extension: str) -> str:
    return f"/uploads/tenants/{slug}/branding/logo{extension}"


def tenant_logo_fs_dir(slug: str) -> Path:
    return TENANT_UPLOADS_ROOT / slug / "branding"


def tenant_context_from_row(row: sqlite3.Row) -> TenantContext:
    slug = row["slug"]
    db_path = Path(row["db_path"])
    calendar_share_token = (row["calendar_share_token"] or "").strip() if "calendar_share_token" in row.keys() else ""
    if not calendar_share_token:
        calendar_share_token = secrets.token_urlsafe(24)
    criteria = normalize_rating_criteria_config(row["rating_criteria_json"] if "rating_criteria_json" in row.keys() else "")
    officer_weight, rusher_weight = normalize_role_weights(
        row["officer_weight"] if "officer_weight" in row.keys() else 0.6,
        row["rusher_weight"] if "rusher_weight" in row.keys() else 0.4,
    )
    default_interest_tags = parse_default_interest_tags(row["default_interest_tags"] if "default_interest_tags" in row.keys() else "")
    default_stereotype_tags = parse_default_stereotype_tags(
        row["default_stereotype_tags"] if "default_stereotype_tags" in row.keys() else ""
    )
    return TenantContext(
        slug=slug,
        display_name=row["display_name"],
        chapter_name=row["chapter_name"] or "",
        org_type=normalize_org_type(row["org_type"] if "org_type" in row.keys() else None),
        setup_tagline=sanitize_short_text(
            row["setup_tagline"] if "setup_tagline" in row.keys() else "",
            "",
            max_length=180,
        ),
        logo_path=row["logo_path"],
        theme_primary=normalize_theme_color(row["theme_primary"] or "", DEFAULT_THEME_PRIMARY),
        theme_secondary=normalize_theme_color(row["theme_secondary"] or "", DEFAULT_THEME_SECONDARY),
        theme_tertiary=normalize_theme_color(
            row["theme_tertiary"] if "theme_tertiary" in row.keys() else "",
            DEFAULT_THEME_TERTIARY,
        ),
        role_weight_officer=officer_weight,
        role_weight_rusher=rusher_weight,
        rating_criteria=tuple(criteria),
        rating_total_max=rating_total_max(criteria),
        default_interest_tags=tuple(default_interest_tags),
        default_stereotype_tags=tuple(default_stereotype_tags),
        db_path=db_path,
        pnm_uploads_dir=TENANT_UPLOADS_ROOT / slug / "pnms",
        backup_dir=BACKUP_DIR / slug,
        calendar_share_token=calendar_share_token,
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


def app_config_for_tenant(tenant: TenantContext) -> dict[str, Any]:
    base_path = f"/{tenant.slug}"
    member_base = f"{base_path}/member"
    member_signup_qr_path = f"{base_path}/member-signup-qr.svg"
    mobile_base = f"{base_path}/mobile"
    desktop_routes = {
        "dashboard": f"{base_path}/dashboard",
        "rushees": f"{base_path}/rushees",
        "meetings": f"{base_path}/meetings",
        "team": f"{base_path}/team",
        "calendar": f"{base_path}/calendar",
        "admin": f"{base_path}/admin",
    }
    mobile_routes = {
        "dashboard": mobile_base,
        "rushees": f"{mobile_base}/pnms",
        "meetings": f"{mobile_base}/meetings",
        "team": f"{mobile_base}/members",
        "calendar": f"{mobile_base}/calendar",
        "admin": f"{mobile_base}/admin",
        "create": f"{mobile_base}/create",
        "meeting": f"{mobile_base}/meeting",
    }
    return {
        "base_path": base_path,
        "api_base": f"{base_path}/api",
        "meeting_base": f"{base_path}/meeting",
        "member_base": member_base,
        "platform_base": "/platform",
        "mobile_base": mobile_base,
        "tenant_slug": tenant.slug,
        "tenant_name": tenant.display_name,
        "chapter_name": tenant.chapter_name,
        "org_type": tenant.org_type,
        "setup_tagline": tenant.setup_tagline,
        "logo_path": tenant.logo_path,
        "theme_primary": tenant.theme_primary,
        "theme_secondary": tenant.theme_secondary,
        "theme_tertiary": tenant.theme_tertiary,
        "rating_criteria": list(tenant.rating_criteria),
        "rating_total_max": tenant.rating_total_max,
        "role_weights": {
            "officer": tenant.role_weight_officer,
            "rusher": tenant.role_weight_rusher,
        },
        "default_interest_tags": list(tenant.default_interest_tags),
        "default_stereotype_tags": list(tenant.default_stereotype_tags),
        "state_options": [{"code": code, "name": name} for code, name in sorted(US_STATE_CODE_TO_NAME.items())],
        "desktop_routes": desktop_routes,
        "mobile_routes": mobile_routes,
        "member_signup_path": member_base,
        "member_signup_qr_path": member_signup_qr_path,
        "calendar_timezone": CALENDAR_TIMEZONE,
        "calendar_feed_path": f"/{tenant.slug}/calendar/rush.ics?token={tenant.calendar_share_token}",
        "calendar_lunch_feed_path": f"/{tenant.slug}/calendar/lunches.ics?token={tenant.calendar_share_token}",
        "is_demo_tenant": is_demo_tenant_slug(tenant.slug),
    }


DESKTOP_ROUTE_TO_PAGE_KEY: dict[str, str] = {
    "dashboard": "overview",
    "rushees": "rushees",
    "meetings": "meetings",
    "team": "members",
    "calendar": "operations",
    "admin": "admin",
}
DEFAULT_DESKTOP_ROUTE = "dashboard"
LEGACY_VIEW_TO_ROUTE: dict[str, str] = {
    "overview": "dashboard",
    "rushees": "rushees",
    "meetings": "meetings",
    "members": "team",
    "admin": "admin",
}


def normalize_desktop_route(route: str | None) -> str:
    token = str(route or "").strip().lower()
    if token in DESKTOP_ROUTE_TO_PAGE_KEY:
        return token
    return DEFAULT_DESKTOP_ROUTE


def desktop_routes_for_tenant(tenant: TenantContext) -> dict[str, str]:
    return {
        route: f"/{tenant.slug}/{route}"
        for route in DESKTOP_ROUTE_TO_PAGE_KEY
    }


def legacy_view_redirect_url(tenant: TenantContext, view: str | None) -> str | None:
    token = str(view or "").strip().lower()
    if not token:
        return None
    if token == "operations":
        # Keep legacy bookmark compatibility to dashboard section.
        return f"/{tenant.slug}/dashboard#operations"
    mapped_route = LEGACY_VIEW_TO_ROUTE.get(token)
    if not mapped_route:
        return None
    return f"/{tenant.slug}/{mapped_route}"


def desktop_context(
    request: Request,
    tenant: TenantContext,
    desktop_route: str,
    *,
    is_demo_mode: bool = False,
    initial_authenticated: bool = False,
) -> dict[str, Any]:
    resolved_route = normalize_desktop_route(desktop_route)
    app_config = app_config_for_tenant(tenant)
    app_config["desktop_page"] = DESKTOP_ROUTE_TO_PAGE_KEY.get(resolved_route, DESKTOP_ROUTE_TO_PAGE_KEY[DEFAULT_DESKTOP_ROUTE])
    app_config["desktop_route"] = resolved_route
    app_config["desktop_routes"] = desktop_routes_for_tenant(tenant)
    return {
        "request": request,
        "tenant": tenant,
        "app_config": app_config,
        "desktop_route": resolved_route,
        "is_demo_mode": is_demo_mode,
        "initial_authenticated": initial_authenticated,
    }


def render_desktop_page(
    request: Request,
    *,
    desktop_route: str,
    is_demo_mode: bool = False,
) -> HTMLResponse:
    tenant = getattr(request.state, "tenant", None)
    if not isinstance(tenant, TenantContext):
        raise HTTPException(status_code=404, detail="Organization context required.")

    legacy_redirect = legacy_view_redirect_url(tenant, request.query_params.get("view"))
    if legacy_redirect:
        return RedirectResponse(url=legacy_redirect, status_code=307)

    session_role = request_session_role(request)
    if session_role == ROLE_RUSHER:
        return RedirectResponse(url=f"/{tenant.slug}/member", status_code=307)
    if request_prefers_mobile(request) and bool(session_role):
        mobile_target = "/mobile/meetings" if normalize_desktop_route(desktop_route) == "meetings" else "/mobile"
        return RedirectResponse(url=f"/{tenant.slug}{mobile_target}", status_code=307)

    resolved_route = normalize_desktop_route(desktop_route)
    if resolved_route == "admin" and session_role and session_role != ROLE_HEAD:
        return RedirectResponse(url=f"/{tenant.slug}/dashboard?notice=admin-access-denied", status_code=307)

    return templates.TemplateResponse(
        "desktop_shell.html",
        desktop_context(
            request,
            tenant,
            resolved_route,
            is_demo_mode=is_demo_mode,
            initial_authenticated=bool(session_role),
        ),
    )


def manifest_payload_for_tenant(tenant: TenantContext | None) -> dict[str, Any]:
    if tenant:
        display_name = tenant.display_name.strip() or "BidBoard"
        chapter_short = (tenant.chapter_name or display_name).strip()
        start_url = f"/{tenant.slug}/dashboard"
        scope = f"/{tenant.slug}/"
        return {
            "name": f"{display_name} | BidBoard",
            "short_name": chapter_short[:24],
            "description": f"{display_name} recruitment workspace on BidBoard.",
            "start_url": start_url,
            "scope": scope,
            "display": "standalone",
            "display_override": ["standalone", "minimal-ui", "browser"],
            "background_color": "#f4efe6",
            "theme_color": tenant.theme_primary,
            "icons": [
                {
                    "src": "/static/icons/icon-192.png",
                    "sizes": "192x192",
                    "type": "image/png",
                },
                {
                    "src": "/static/icons/icon-512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any maskable",
                },
            ],
        }
    return {
        "name": "BidBoard Recruitment OS",
        "short_name": "BidBoard",
        "description": "Recruitment operating system for fraternities and sororities.",
        "start_url": "/organizations",
        "scope": "/",
        "display": "standalone",
        "display_override": ["standalone", "minimal-ui", "browser"],
        "background_color": "#f4efe6",
        "theme_color": DEFAULT_THEME_PRIMARY,
        "icons": [
            {
                "src": "/static/icons/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
            },
            {
                "src": "/static/icons/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable",
            },
        ],
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


def fold_ical_line(line: str, limit: int = 75) -> str:
    if len(line) <= limit:
        return line
    chunks = [line[:limit]]
    remainder = line[limit:]
    while remainder:
        chunks.append(f" {remainder[:limit-1]}")
        remainder = remainder[limit - 1 :]
    return "\r\n".join(chunks)


def escape_ical_text(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
    escaped = escaped.replace(";", "\\;").replace(",", "\\,")
    return escaped


def format_utc_ical(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def format_google_event_stamp(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S")


def parse_clock_value(raw: str | None) -> tuple[int, int] | None:
    if raw is None:
        return None
    token = raw.strip()
    if not token:
        return None
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", token):
        raise ValueError("Time must use HH:MM in 24-hour format.")
    hour, minute = token.split(":")
    return int(hour), int(minute)


def build_google_calendar_event_url(
    *,
    pnm_name: str,
    pnm_code: str,
    lunch_date: str,
    notes: str,
    location: str,
    start_time: str | None,
    end_time: str | None,
    logged_by_username: str,
) -> str:
    event_date = date.fromisoformat(lunch_date)
    title = f"Lunch with {pnm_name}"
    details_parts = [f"PNM Code: {pnm_code}", f"Logged by: {logged_by_username}"]
    if notes:
        details_parts.append(f"Notes: {notes}")
    details = "\n".join(details_parts)

    start_clock = parse_clock_value(start_time)
    end_clock = parse_clock_value(end_time)
    if end_clock and not start_clock:
        raise ValueError("End time requires a start time.")

    if start_clock:
        start_dt = datetime(event_date.year, event_date.month, event_date.day, start_clock[0], start_clock[1], 0)
        if end_clock:
            end_dt = datetime(event_date.year, event_date.month, event_date.day, end_clock[0], end_clock[1], 0)
            if end_dt <= start_dt:
                raise ValueError("End time must be after start time.")
        else:
            end_dt = start_dt + timedelta(hours=1)
        dates_value = f"{format_google_event_stamp(start_dt)}/{format_google_event_stamp(end_dt)}"
    else:
        end_date = event_date + timedelta(days=1)
        dates_value = f"{event_date.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"

    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": dates_value,
        "details": details,
        "location": location,
        "ctz": CALENDAR_TIMEZONE,
    }
    return f"https://calendar.google.com/calendar/render?{urlencode(params)}"


def build_google_calendar_generic_event_url(
    *,
    title: str,
    event_date: str,
    details: str,
    location: str,
    start_time: str | None,
    end_time: str | None,
) -> str:
    event_day = date.fromisoformat(event_date)
    start_clock = parse_clock_value(start_time)
    end_clock = parse_clock_value(end_time)
    if end_clock and not start_clock:
        raise ValueError("End time requires a start time.")

    if start_clock:
        start_dt = datetime(event_day.year, event_day.month, event_day.day, start_clock[0], start_clock[1], 0)
        if end_clock:
            end_dt = datetime(event_day.year, event_day.month, event_day.day, end_clock[0], end_clock[1], 0)
            if end_dt <= start_dt:
                raise ValueError("End time must be after start time.")
        else:
            end_dt = start_dt + timedelta(hours=1)
        dates_value = f"{format_google_event_stamp(start_dt)}/{format_google_event_stamp(end_dt)}"
    else:
        end_date = event_day + timedelta(days=1)
        dates_value = f"{event_day.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"

    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": dates_value,
        "details": details,
        "location": location,
        "ctz": CALENDAR_TIMEZONE,
    }
    return f"https://calendar.google.com/calendar/render?{urlencode(params)}"


def normalize_rush_event_type(value: str) -> str:
    token = value.strip().lower()
    if token not in RUSH_EVENT_TYPES:
        raise ValueError(
            "Event type must be one of: "
            + ", ".join(sorted(RUSH_EVENT_TYPES))
        )
    return token


def normalize_engagement_event_type(value: str) -> str:
    token = value.strip().lower()
    if token not in ENGAGEMENT_EVENT_TYPES:
        raise ValueError(
            "Engagement event type must be one of: "
            + ", ".join(sorted(ENGAGEMENT_EVENT_TYPES))
        )
    return token


def normalize_engagement_event_status(value: str) -> str:
    token = value.strip().lower()
    if token not in ENGAGEMENT_EVENT_STATUSES:
        raise ValueError(
            "Event status must be one of: "
            + ", ".join(sorted(ENGAGEMENT_EVENT_STATUSES))
        )
    return token


def normalize_assignment_status(value: str) -> str:
    token = value.strip().lower()
    if token not in ASSIGNMENT_STATUSES:
        raise ValueError(
            "Assignment status must be one of: "
            + ", ".join(sorted(ASSIGNMENT_STATUSES))
        )
    return token


def normalize_package_group_id(value: Any) -> str:
    token = str(value or "").strip()
    return token


def new_package_group_id() -> str:
    return f"pkg_{secrets.token_hex(6)}"


def package_group_label(package_group_id: str | None) -> str | None:
    token = normalize_package_group_id(package_group_id)
    if not token:
        return None
    if token.startswith("pkg_"):
        token = token[4:]
    token = token.upper()
    return token[:8] if token else None


def normalize_funnel_stage(value: str) -> str:
    token = value.strip().lower()
    if token not in PNM_FUNNEL_STAGES:
        raise ValueError(
            "Funnel stage must be one of: "
            + ", ".join(PNM_FUNNEL_STAGES)
        )
    return token


def normalize_digest_period(value: str) -> str:
    token = value.strip().lower()
    if token not in {"daily", "weekly"}:
        raise ValueError("Digest period must be daily or weekly.")
    return token


def normalize_weekly_goal_metric(value: str) -> str:
    token = value.strip().lower()
    if token not in WEEKLY_GOAL_METRIC_TYPES:
        raise ValueError(
            "Goal metric must be one of: "
            + ", ".join(sorted(WEEKLY_GOAL_METRIC_TYPES))
        )
    return token


def week_bounds_for(day_value: date) -> tuple[date, date]:
    start = day_value - timedelta(days=day_value.weekday())
    return start, start + timedelta(days=6)


def parse_week_date(value: str | None, fallback: date) -> date:
    if value is None:
        return fallback
    token = value.strip()
    if not token:
        return fallback
    return date.fromisoformat(token)


def date_within_span(day_value: date, start_day: date, end_day: date) -> bool:
    return start_day <= day_value <= end_day


def normalize_chat_tag(value: str) -> str:
    token = value.strip().lower()
    if token.startswith("#"):
        token = token[1:]
    if not token:
        raise ValueError("Tag cannot be empty.")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,23}", token):
        raise ValueError("Tags must be 2-24 chars and use letters, numbers, dash, underscore.")
    return token


def parse_chat_tags(raw: str | list[str] | None, message: str) -> list[str]:
    candidates: list[str] = []
    if isinstance(raw, str):
        candidates.extend([part.strip() for part in re.split(r"[,;\n]+", raw) if part.strip()])
    elif isinstance(raw, list):
        candidates.extend([str(part).strip() for part in raw if str(part).strip()])

    hashtag_tokens = re.findall(r"(?:^|\s)#([A-Za-z0-9_-]{2,24})", message or "")
    candidates.extend(hashtag_tokens)

    normalized: list[str] = []
    seen: set[str] = set()
    for token in candidates:
        try:
            cleaned = normalize_chat_tag(token)
        except ValueError:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized[:12]


def extract_message_mentions(message: str) -> list[str]:
    if not message:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for token in re.findall(r"@([A-Za-z0-9._-]{3,64})", message):
        lowered = token.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(lowered)
    return ordered


def build_webcal_url(http_url: str) -> str:
    parsed = urlsplit(http_url)
    return urlunsplit(("webcal", parsed.netloc, parsed.path, parsed.query, ""))


def build_google_subscribe_url(http_url: str) -> str:
    return f"https://calendar.google.com/calendar/u/0/r?cid={quote(http_url, safe='')}"


def normalize_csv_column_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())


def resolve_google_form_columns(headers: list[str]) -> dict[str, str | None]:
    normalized_to_original: dict[str, str] = {}
    for header in headers:
        normalized = normalize_csv_column_name(header)
        if normalized and normalized not in normalized_to_original:
            normalized_to_original[normalized] = header

    resolved: dict[str, str | None] = {}
    for field, aliases in GOOGLE_FORM_COLUMN_ALIASES.items():
        found: str | None = None
        normalized_aliases = [normalize_csv_column_name(alias) for alias in aliases]
        for alias in normalized_aliases:
            candidate = normalized_to_original.get(alias)
            if candidate:
                found = candidate
                break
        if not found:
            for normalized_header, original in normalized_to_original.items():
                if any(alias and alias in normalized_header for alias in normalized_aliases):
                    found = original
                    break
        resolved[field] = found
    return resolved


def csv_row_value(row: dict[str, Any], column: str | None) -> str:
    if not column:
        return ""
    return str(row.get(column, "")).strip()


def split_full_name(raw: str) -> tuple[str, str]:
    tokens = [token for token in re.split(r"\s+", raw.strip()) if token]
    if not tokens:
        return "", ""
    if len(tokens) == 1:
        return tokens[0], "Unknown"
    return tokens[0], " ".join(tokens[1:])


def normalize_import_class_year(raw: str) -> str:
    token = raw.strip().lower()
    if not token:
        return "F"
    if token in {"f", "freshman", "freshmen", "firstyear", "first-year", "1", "1st"}:
        return "F"
    if token in {"s", "sophomore", "sophomores", "secondyear", "second-year", "2", "2nd"}:
        return "S"
    if token in {"j", "junior", "juniors", "thirdyear", "third-year", "3", "3rd"}:
        return "J"
    if token[:1] in {"f", "s", "j"}:
        return token[:1].upper()
    raise ValueError("Class year must be F, S, or J.")


def normalize_vcard_photo_bytes(raw: bytes, suffix: str) -> tuple[bytes, str] | None:
    token = suffix.strip().lower()
    if token in {".jpg", ".jpeg"}:
        if len(raw) <= VCARD_PHOTO_MAX_BYTES:
            return raw, "JPEG"
        token = ".jpeg"  # nosec B105
    elif token == ".png" and len(raw) <= VCARD_PHOTO_MAX_BYTES:  # nosec B105
        return raw, "PNG"

    if Image is None:
        return None

    try:
        with Image.open(io.BytesIO(raw)) as image:
            converted = image.convert("RGB")
            max_edge = 640
            if max(converted.size) > max_edge:
                converted.thumbnail((max_edge, max_edge))
            output = io.BytesIO()
            quality = 86
            for _ in range(3):
                output.seek(0)
                output.truncate(0)
                converted.save(output, format="JPEG", optimize=True, quality=quality)
                converted_bytes = output.getvalue()
                if len(converted_bytes) <= VCARD_PHOTO_MAX_BYTES or quality <= 60:
                    return converted_bytes, "JPEG"
                quality -= 12
    except Exception:
        return None
    return None


def build_vcard_photo_line(photo_path: str | None) -> str | None:
    fs_path = photo_fs_path(photo_path)
    if fs_path is None or not fs_path.exists() or not fs_path.is_file():
        return None

    raw = fs_path.read_bytes()
    if not raw:
        return None
    normalized = normalize_vcard_photo_bytes(raw, fs_path.suffix)
    if not normalized:
        return None
    content, photo_type = normalized
    encoded = base64.b64encode(content).decode("ascii")
    return fold_vcard_line(f"PHOTO;ENCODING=b;TYPE={photo_type}:{encoded}")


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

    photo_line = build_vcard_photo_line(row["photo_path"])
    if photo_line:
        lines.append(photo_line)

    lines.append("END:VCARD")
    return "\r\n".join(lines)


def upsert_contact_download_records(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    pnm_ids: list[int],
    downloaded_at: str | None = None,
) -> None:
    normalized_ids: list[int] = []
    seen: set[int] = set()
    for raw_id in pnm_ids:
        pnm_id = int(raw_id)
        if pnm_id <= 0 or pnm_id in seen:
            continue
        seen.add(pnm_id)
        normalized_ids.append(pnm_id)
    if not normalized_ids:
        return
    stamp = downloaded_at or now_iso()
    conn.executemany(
        """
        INSERT INTO user_contact_downloads (user_id, pnm_id, downloaded_at)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, pnm_id) DO UPDATE SET downloaded_at = excluded.downloaded_at
        """,
        [(int(user_id), pnm_id, stamp) for pnm_id in normalized_ids],
    )


def contact_download_status_records(conn: sqlite3.Connection, *, user_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT pnm_id, downloaded_at
        FROM user_contact_downloads
        WHERE user_id = ?
        ORDER BY downloaded_at DESC
        """,
        (int(user_id),),
    ).fetchall()
    return [
        {
            "pnm_id": int(row["pnm_id"]),
            "downloaded_at": row["downloaded_at"],
        }
        for row in rows
    ]


def request_prefers_mobile(request: Request) -> bool:
    if request.query_params.get("desktop") == "1":
        return False
    if request.query_params.get("mobile") == "1":
        return True

    sec_mobile = (request.headers.get("sec-ch-ua-mobile") or "").strip()
    if sec_mobile == "?1":
        return True

    cloudfront_mobile = (request.headers.get("cloudfront-is-mobile-viewer") or "").strip().lower()
    if cloudfront_mobile == "true":
        return True

    forwarded_mobile = (request.headers.get("x-mobile-view") or "").strip().lower()
    if forwarded_mobile in {"1", "true", "yes"}:
        return True

    user_agent = (
        request.headers.get("x-device-user-agent")
        or request.headers.get("user-agent")
        or ""
    ).lower()
    mobile_markers = ["iphone", "android", "mobile", "ipad", "ipod"]
    return any(marker in user_agent for marker in mobile_markers)


def current_platform_admin(request: Request) -> sqlite3.Row:
    token = request.cookies.get(PLATFORM_SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")

    with platform_db_session() as conn:
        row = conn.execute(
            """
            SELECT pa.*, ps.last_seen_at, ps.max_idle_seconds
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
        idle_limit = normalized_idle_ttl_seconds(row["max_idle_seconds"], PLATFORM_SESSION_TTL_SECONDS)
        if (datetime.now(timezone.utc) - last_seen_dt).total_seconds() > idle_limit:
            conn.execute("DELETE FROM platform_sessions WHERE token = ?", (token,))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.")

        conn.execute("UPDATE platform_sessions SET last_seen_at = ? WHERE token = ?", (now_iso(), token))
        return row


def current_platform_admin_optional(request: Request) -> sqlite3.Row | None:
    token = request.cookies.get(PLATFORM_SESSION_COOKIE)
    if not token:
        return None

    with platform_db_session() as conn:
        row = conn.execute(
            """
            SELECT pa.*, ps.last_seen_at, ps.max_idle_seconds
            FROM platform_sessions ps
            JOIN platform_admins pa ON pa.id = ps.admin_id
            WHERE ps.token = ?
            """,
            (token,),
        ).fetchone()
        if not row:
            return None

        try:
            last_seen_dt = datetime.fromisoformat(row["last_seen_at"])
        except (TypeError, ValueError):
            conn.execute("DELETE FROM platform_sessions WHERE token = ?", (token,))
            return None
        idle_limit = normalized_idle_ttl_seconds(row["max_idle_seconds"], PLATFORM_SESSION_TTL_SECONDS)
        if (datetime.now(timezone.utc) - last_seen_dt).total_seconds() > idle_limit:
            conn.execute("DELETE FROM platform_sessions WHERE token = ?", (token,))
            return None

        conn.execute("UPDATE platform_sessions SET last_seen_at = ? WHERE token = ?", (now_iso(), token))
        return row


@app.middleware("http")
async def security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https://unavatar.io https://*.instagram.com https://*.cdninstagram.com https://*.fbcdn.net; "
        "connect-src 'self'; "
        "manifest-src 'self'; "
        "worker-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'"
    )
    if request_forwarded_proto(request) == "https":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    return response


@app.middleware("http")
async def csrf_protection(request: Request, call_next):  # type: ignore[no-untyped-def]
    method = request.method.upper()
    if not ENFORCE_CSRF or method not in UNSAFE_HTTP_METHODS:
        return await call_next(request)

    has_session_cookie = request_has_active_session(request) or request_has_active_platform_session(request)
    origin = (request.headers.get("origin") or "").strip()
    referer = (request.headers.get("referer") or "").strip()

    if origin:
        if not is_csrf_origin_allowed(origin, request):
            return JSONResponse(status_code=403, content={"detail": "CSRF blocked: request origin not allowed."})
    elif referer:
        if not is_csrf_origin_allowed(referer, request):
            return JSONResponse(status_code=403, content={"detail": "CSRF blocked: request origin not allowed."})
    elif has_session_cookie:
        return JSONResponse(status_code=403, content={"detail": "CSRF blocked: origin headers required."})

    if has_session_cookie:
        cookie_token = (request.cookies.get(CSRF_COOKIE) or "").strip()
        header_token = (request.headers.get(CSRF_HEADER) or "").strip()
        if not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token):
            return JSONResponse(status_code=403, content={"detail": "CSRF blocked: token missing or invalid."})

    return await call_next(request)


@app.middleware("http")
async def tenant_resolution(request: Request, call_next):  # type: ignore[no-untyped-def]
    path = request.scope.get("path", "/")
    bypass_prefixes = ("/static", "/uploads", "/platform", "/organizations", "/features", "/faq", "/health", "/demo")
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
    - first: whether the supplied password is valid
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
        raise ValueError("Password must be at least 8 characters.")
    if not re.search(r"[A-Za-z]", access_code_norm) or not re.search(r"[0-9]", access_code_norm):
        raise ValueError("Password must include at least one letter and one number.")


def normalized_ip_or_empty(raw_ip: str | None) -> str:
    token = (raw_ip or "").strip()
    if not token:
        return ""
    try:
        return str(ipaddress.ip_address(token))
    except ValueError:
        return ""


def client_ip(request: Request) -> str:
    if TRUST_X_FORWARDED_FOR:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            first_hop = forwarded_for.split(",")[0].strip()
            normalized = normalized_ip_or_empty(first_hop)
            if normalized:
                return normalized
    if request.client and request.client.host:
        normalized = normalized_ip_or_empty(request.client.host)
        if normalized:
            return normalized
    return "unknown"


def login_throttle_key(request: Request, username: str, *, scope: str) -> str:
    username_token = username.strip().lower() or "unknown-user"
    return f"{scope}:{client_ip(request)}:{username_token}"


def assert_login_allowed(throttle_key: str) -> None:
    now = now_epoch()
    with _LOGIN_GUARD:
        blocked_until = _LOGIN_BLOCKED_UNTIL.get(throttle_key, 0)
        if blocked_until > now:
            retry_after = max(1, int(blocked_until - now))
            raise HTTPException(
                status_code=429,
                detail=f"Too many login attempts. Try again in {retry_after} seconds.",
            )


def record_login_failure(throttle_key: str) -> None:
    now = now_epoch()
    with _LOGIN_GUARD:
        attempts = [ts for ts in _LOGIN_ATTEMPTS.get(throttle_key, []) if now - ts <= LOGIN_WINDOW_SECONDS]
        attempts.append(now)
        _LOGIN_ATTEMPTS[throttle_key] = attempts
        if len(attempts) >= LOGIN_MAX_FAILURES:
            _LOGIN_BLOCKED_UNTIL[throttle_key] = now + LOGIN_BLOCK_SECONDS
            _LOGIN_ATTEMPTS[throttle_key] = []


def record_login_success(throttle_key: str) -> None:
    with _LOGIN_GUARD:
        _LOGIN_ATTEMPTS.pop(throttle_key, None)
        _LOGIN_BLOCKED_UNTIL.pop(throttle_key, None)


def normalize_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Name fields cannot be empty.")
    return value[0].upper() + value[1:].strip()


def normalize_city_value(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value.strip())


def normalize_state_code(value: str | None) -> str:
    token = re.sub(r"\s+", " ", str(value or "").strip())
    if not token:
        return ""

    direct_code = re.sub(r"[^A-Za-z]", "", token).upper()
    if len(direct_code) == 2 and direct_code in US_STATE_CODE_TO_NAME:
        return direct_code

    normalized_name = re.sub(r"[^A-Za-z ]", " ", token).lower()
    normalized_name = re.sub(r"\s+", " ", normalized_name).strip()
    if not normalized_name:
        return ""
    return US_STATE_NAME_TO_CODE.get(normalized_name, "")


def parse_state_filter(raw_state: str | None) -> str | None:
    if raw_state is None:
        return None
    token = raw_state.strip()
    if not token:
        return None
    normalized = normalize_state_code(token)
    if not normalized:
        raise ValueError("State must be a valid US state name or 2-letter code.")
    return normalized


def parse_hometown_city_state(hometown: str | None) -> tuple[str, str]:
    text = re.sub(r"\s+", " ", str(hometown or "").strip())
    if not text:
        return "", ""

    if "," in text:
        city_part, state_part = text.rsplit(",", 1)
        state_code = normalize_state_code(state_part)
        if state_code:
            return city_part.strip(), state_code

    trailing_code_match = re.match(r"^(?P<city>.+?)\s+([A-Za-z]{2})$", text)
    if trailing_code_match:
        state_code = normalize_state_code(trailing_code_match.group(2))
        if state_code:
            return trailing_code_match.group("city").strip(" ,"), state_code

    lowered = text.lower()
    for state_name in US_STATE_NAMES_DESC:
        if lowered == state_name:
            return "", US_STATE_NAME_TO_CODE[state_name]
        suffix = f" {state_name}"
        if lowered.endswith(suffix):
            city_part = text[: -len(suffix)].strip(" ,")
            if city_part:
                return city_part, US_STATE_NAME_TO_CODE[state_name]

    return text, ""


def resolve_pnm_state_code(hometown: str | None, explicit_state: str | None = None) -> str:
    normalized_explicit = normalize_state_code(explicit_state)
    if normalized_explicit:
        return normalized_explicit
    _, parsed_state = parse_hometown_city_state(hometown)
    return parsed_state


def pnm_state_code_for_row(row: sqlite3.Row) -> str:
    keys = set(row.keys())
    hometown_value = row["hometown"] if "hometown" in keys else None
    explicit_state = row["hometown_state_code"] if "hometown_state_code" in keys else None
    return resolve_pnm_state_code(hometown_value, explicit_state)


def normalize_role_filter(value: str | None) -> str | None:
    token = str(value or "").strip().lower()
    if not token or token == "all":
        return None
    if token in {"head rush officer", "head"}:
        return ROLE_HEAD
    if token in {"rush officer", "officer"}:
        return ROLE_RUSH_OFFICER
    if token in {"rusher", "member", "general member"}:
        return ROLE_RUSHER
    raise ValueError("Role must be Head Rush Officer, Rush Officer, Rusher, or all.")


def role_sort_value(role: str | None) -> int:
    return ROLE_SORT_ORDER.get(str(role or "").strip(), 99)


def user_location_sort_key(row: sqlite3.Row) -> tuple[Any, ...]:
    keys = set(row.keys())
    state_code = normalize_state_code(row["state_code"]) if "state_code" in keys else ""
    city = normalize_city_value(row["city"] if "city" in keys else "")
    username = str(row["username"] or "").strip().lower()
    return (
        state_code == "",
        state_code,
        city == "",
        city.lower(),
        username,
    )


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


def allowed_interest_map_for_tenant(tenant: TenantContext | None = None) -> dict[str, str]:
    resolved = tenant if tenant is not None else CURRENT_TENANT.get()
    source = list(resolved.default_interest_tags) if resolved else list(DEFAULT_INTEREST_TAG_SUGGESTIONS)
    allowed: dict[str, str] = {}
    for raw in source:
        try:
            normalized = normalize_interest(str(raw))
        except ValueError:
            continue
        key = normalized.lower()
        if key in allowed:
            continue
        allowed[key] = normalized
    if allowed:
        return allowed
    fallback: dict[str, str] = {}
    for raw in DEFAULT_INTEREST_TAG_SUGGESTIONS:
        normalized = normalize_interest(raw)
        fallback[normalized.lower()] = normalized
    return fallback


def allowed_stereotype_map_for_tenant(tenant: TenantContext | None = None) -> dict[str, str]:
    resolved = tenant if tenant is not None else CURRENT_TENANT.get()
    source = list(resolved.default_stereotype_tags) if resolved else list(DEFAULT_STEREOTYPE_TAG_SUGGESTIONS)
    allowed: dict[str, str] = {}
    for raw in source:
        token = sanitize_short_text(str(raw), "", max_length=48)
        if not token:
            continue
        key = token.lower()
        if key in allowed:
            continue
        allowed[key] = token
    if allowed:
        return allowed
    fallback: dict[str, str] = {}
    for raw in DEFAULT_STEREOTYPE_TAG_SUGGESTIONS:
        token = sanitize_short_text(raw, "", max_length=48)
        if token:
            fallback[token.lower()] = token
    return fallback


def default_interest_tag_for_tenant(tenant: TenantContext | None = None) -> str:
    allowed = allowed_interest_map_for_tenant(tenant)
    return next(iter(allowed.values()))


def default_stereotype_tag_for_tenant(tenant: TenantContext | None = None) -> str:
    allowed = allowed_stereotype_map_for_tenant(tenant)
    return next(iter(allowed.values()))


def enforce_allowed_interests(interests: list[str], tenant: TenantContext | None = None) -> list[str]:
    allowed = allowed_interest_map_for_tenant(tenant)
    normalized: list[str] = []
    seen: set[str] = set()
    invalid: list[str] = []
    for item in interests:
        key = item.lower()
        canonical = allowed.get(key)
        if not canonical:
            invalid.append(item)
            continue
        canonical_key = canonical.lower()
        if canonical_key in seen:
            continue
        seen.add(canonical_key)
        normalized.append(canonical)
    if invalid:
        raise ValueError(
            f"Interests must be selected from approved options. Unsupported: {', '.join(sorted(set(invalid), key=str.lower))}."
        )
    if not normalized:
        raise ValueError("Select at least one approved interest.")
    return normalized


def enforce_allowed_stereotype(stereotype: str, tenant: TenantContext | None = None) -> str:
    token = sanitize_short_text(stereotype, "", max_length=48)
    if not token:
        raise ValueError("Stereotype is required.")
    allowed = allowed_stereotype_map_for_tenant(tenant)
    canonical = allowed.get(token.lower())
    if not canonical:
        raise ValueError("Stereotype must be selected from approved options.")
    return canonical


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


def role_weight(role: str, tenant: TenantContext | None = None) -> float:
    resolved = tenant if tenant is not None else CURRENT_TENANT.get()
    officer_weight = resolved.role_weight_officer if resolved else 0.6
    rusher_weight = resolved.role_weight_rusher if resolved else 0.4
    if role in {ROLE_RUSH_OFFICER, ROLE_HEAD}:
        return float(officer_weight)
    return float(rusher_weight)


def score_total(payload: dict[str, int]) -> int:
    return (
        payload["good_with_girls"]
        + payload["will_make_it"]
        + payload["personable"]
        + payload["alcohol_control"]
        + payload["instagram_marketability"]
    )


def validate_score_data_against_criteria(score_data: dict[str, int], criteria: list[dict[str, Any]]) -> None:
    criteria_map = rating_criteria_by_field(criteria)
    for field in RATING_FIELDS:
        value = int(score_data.get(field, 0))
        field_limit = int(RATING_FIELD_LIMITS[field])
        configured = criteria_map.get(field)
        configured_max = int(configured["max"]) if configured and "max" in configured else field_limit
        max_allowed = max(1, min(field_limit, configured_max))
        if value < 0 or value > max_allowed:
            label = configured["label"] if configured and "label" in configured else field
            raise HTTPException(status_code=400, detail=f"{label} must be between 0 and {max_allowed}.")


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


def instagram_avatar_fallback_url(instagram_handle: str | None) -> str | None:
    if not instagram_handle:
        return None
    username = instagram_username_from_handle(instagram_handle)
    if not username:
        return None
    return f"https://unavatar.io/instagram/{quote(username, safe='')}"


def demo_pnm_placeholder_url() -> str:
    return "/static/images/demo-pnm-placeholder.svg"


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


def has_local_photo_file(photo_path: str | None) -> bool:
    local_url = public_photo_url(photo_path)
    if not local_url:
        return False
    fs_path = photo_fs_path(local_url)
    if fs_path is None:
        return False
    return fs_path.exists() and fs_path.is_file()


def resolve_pnm_photo_url(photo_path: str | None, instagram_handle: str | None) -> str | None:
    local_url = public_photo_url(photo_path)
    if local_url and has_local_photo_file(local_url):
        return local_url
    tenant = CURRENT_TENANT.get()
    if tenant and is_demo_tenant_slug(tenant.slug):
        return demo_pnm_placeholder_url()
    return instagram_avatar_fallback_url(instagram_handle)


def remove_photo_if_present(photo_path: str | None) -> None:
    target = photo_fs_path(photo_path)
    if target and target.exists() and target.is_file():
        target.unlink(missing_ok=True)


def detect_image_extension(content_type: str | None, content: bytes) -> str | None:
    normalized = (content_type or "").split(";")[0].strip().lower()
    extension = ALLOWED_PHOTO_TYPES.get(normalized)
    if extension:
        return extension
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    return None


def write_pnm_photo_bytes(pnm_id: int, content: bytes, extension: str) -> tuple[str, Path]:
    tenant = current_tenant()
    uploads_dir = active_pnm_uploads_dir()
    uploads_dir.mkdir(parents=True, exist_ok=True)
    filename = f"pnm-{pnm_id}-{secrets.token_hex(10)}{extension}"
    target_path = uploads_dir / filename
    target_path.write_bytes(content)
    public_path = f"/uploads/tenants/{tenant.slug}/pnms/{filename}"
    return public_path, target_path


def instagram_username_from_handle(handle: str) -> str:
    token = handle.strip()
    if token.startswith("@"):
        token = token[1:]
    return token.strip()


def is_allowed_remote_fetch_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return False
    if host in ALLOWED_REMOTE_FETCH_HOSTS:
        return True
    return any(host.endswith(suffix) for suffix in ALLOWED_REMOTE_FETCH_HOST_SUFFIXES)


def fetch_image_from_url(request_url: str, referer: str | None = None) -> tuple[bytes, str] | None:
    if not is_allowed_remote_fetch_url(request_url):
        return None
    headers = {
        "User-Agent": HTTP_USER_AGENT,
        "Accept": "image/*",
    }
    if referer and is_allowed_remote_fetch_url(referer):
        headers["Referer"] = referer
        parsed = urlsplit(referer)
        if parsed.scheme and parsed.netloc:
            headers["Origin"] = f"{parsed.scheme}://{parsed.netloc}"
    request = URLRequest(
        request_url,
        headers=headers,
    )
    try:
        with urlopen(request, timeout=INSTAGRAM_AVATAR_TIMEOUT_SECONDS) as response:  # nosec B310
            content = response.read(MAX_PNM_PHOTO_BYTES + 1)
            if not content:
                return None
            if len(content) > MAX_PNM_PHOTO_BYTES:
                return None
            content_type = response.headers.get("Content-Type", "")
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        return None

    extension = detect_image_extension(content_type, content)
    if not extension:
        return None
    return content, extension


def fetch_instagram_og_image_url(username: str) -> str | None:
    request_url = f"https://www.instagram.com/{quote(username, safe='')}/"
    if not is_allowed_remote_fetch_url(request_url):
        return None
    request = URLRequest(
        request_url,
        headers={
            "User-Agent": HTTP_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urlopen(request, timeout=INSTAGRAM_AVATAR_TIMEOUT_SECONDS) as response:  # nosec B310
            content = response.read(INSTAGRAM_PROFILE_HTML_MAX_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        return None

    if not content:
        return None
    if len(content) > INSTAGRAM_PROFILE_HTML_MAX_BYTES:
        content = content[:INSTAGRAM_PROFILE_HTML_MAX_BYTES]

    page = content.decode("utf-8", errors="ignore")
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, page, flags=re.IGNORECASE)
        if not match:
            continue
        candidate = normalize_instagram_image_url(html.unescape(match.group(1)).strip())
        if candidate.startswith("http://") or candidate.startswith("https://"):
            return candidate
    return None


def normalize_instagram_image_url(url: str) -> str:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return url

    # Keep Instagram-signed URLs byte-for-byte intact. Re-encoding query params
    # can invalidate signed CDN links ("URL signature mismatch" 403).
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return url

    return url.strip()


def fetch_instagram_api_image_url(username: str) -> str | None:
    api_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={quote(username, safe='')}"
    if not is_allowed_remote_fetch_url(api_url):
        return None
    request = URLRequest(
        api_url,
        headers={
            "User-Agent": HTTP_USER_AGENT,
            "Accept": "application/json",
            "X-IG-App-ID": INSTAGRAM_WEB_APP_ID,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"https://www.instagram.com/{quote(username, safe='')}/",
        },
    )
    try:
        with urlopen(request, timeout=INSTAGRAM_AVATAR_TIMEOUT_SECONDS) as response:  # nosec B310
            payload = response.read(INSTAGRAM_API_RESPONSE_MAX_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        return None
    if not payload or len(payload) > INSTAGRAM_API_RESPONSE_MAX_BYTES:
        return None

    try:
        decoded = json.loads(payload.decode("utf-8", errors="ignore"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    user = ((decoded.get("data") or {}).get("user") or {}) if isinstance(decoded, dict) else {}
    if not isinstance(user, dict):
        return None
    url = user.get("profile_pic_url_hd") or user.get("profile_pic_url")
    if not isinstance(url, str):
        return None
    candidate = normalize_instagram_image_url(html.unescape(url).strip())
    if candidate.startswith("http://") or candidate.startswith("https://"):
        return candidate
    return None


def try_fetch_instagram_profile_photo(instagram_handle: str) -> tuple[bytes, str] | None:
    username = instagram_username_from_handle(instagram_handle)
    if not username:
        return None
    profile_referer = f"https://www.instagram.com/{quote(username, safe='')}/"

    high_res_url = fetch_instagram_api_image_url(username)
    if high_res_url:
        image = fetch_image_from_url(high_res_url, referer=profile_referer)
        if image:
            return image

    og_url = fetch_instagram_og_image_url(username)
    if og_url:
        image = fetch_image_from_url(og_url, referer=profile_referer)
        if image:
            return image

    fallback_url = f"https://unavatar.io/instagram/{quote(username, safe='')}?fallback=false"
    return fetch_image_from_url(fallback_url)


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


def copy_sqlite_database(source: Path, destination: Path) -> bool:
    if not source.exists() or source == destination:
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_conn = sqlite3.connect(source)
    destination_conn = sqlite3.connect(destination)
    try:
        with destination_conn:
            source_conn.backup(destination_conn)
    except Exception:
        destination_conn.close()
        source_conn.close()
        destination.unlink(missing_ok=True)
        return False
    destination_conn.close()
    source_conn.close()
    return True


def season_archive_path() -> Path:
    return active_backup_dir() / SEASON_ARCHIVE_FILENAME


def write_sqlite_snapshot(source_db: Path, destination_db: Path) -> None:
    destination_db.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination_db.with_suffix(f"{destination_db.suffix}.tmp")
    source_conn = sqlite3.connect(source_db)
    destination_conn = sqlite3.connect(temp_path)
    try:
        with destination_conn:
            source_conn.backup(destination_conn)
    finally:
        destination_conn.close()
        source_conn.close()
    temp_path.replace(destination_db)


def purge_pnm_uploads_dir() -> None:
    uploads_dir = active_pnm_uploads_dir()
    if not uploads_dir.exists():
        return
    for candidate in uploads_dir.glob("*"):
        if candidate.is_file():
            candidate.unlink(missing_ok=True)


def csv_safe_cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, str):
        if value[:1] in {"=", "+", "-", "@", "\t"}:
            return f"'{value}"
        return value
    return value


def csv_bytes_from_rows(columns: list[str], rows: list[dict[str, Any]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({column: csv_safe_cell(row.get(column)) for column in columns})
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
        pnm_assignment_rows = [dict(row) for row in conn.execute("SELECT * FROM pnm_officer_assignments ORDER BY id ASC").fetchall()]
        rating_rows = [dict(row) for row in conn.execute("SELECT * FROM ratings ORDER BY id ASC").fetchall()]
        rating_change_rows = [dict(row) for row in conn.execute("SELECT * FROM rating_changes ORDER BY id ASC").fetchall()]
        rating_history_rows = [dict(row) for row in conn.execute("SELECT * FROM rating_history ORDER BY id ASC").fetchall()]
        rating_comment_event_rows = [dict(row) for row in conn.execute("SELECT * FROM rating_comment_events ORDER BY id ASC").fetchall()]
        lunch_rows = [dict(row) for row in conn.execute("SELECT * FROM lunches ORDER BY id ASC").fetchall()]
        rush_event_rows = [dict(row) for row in conn.execute("SELECT * FROM rush_events ORDER BY id ASC").fetchall()]
        engagement_event_rows = [dict(row) for row in conn.execute("SELECT * FROM engagement_events ORDER BY id ASC").fetchall()]
        weekly_goal_rows = [dict(row) for row in conn.execute("SELECT * FROM weekly_goals ORDER BY id ASC").fetchall()]
        stage_history_rows = [dict(row) for row in conn.execute("SELECT * FROM pnm_stage_history ORDER BY id ASC").fetchall()]
        audit_rows = [dict(row) for row in conn.execute("SELECT * FROM audit_ledger ORDER BY id ASC").fetchall()]
        chat_rows = [dict(row) for row in conn.execute("SELECT * FROM officer_chat_messages ORDER BY id ASC").fetchall()]
        chat_tag_rows = [dict(row) for row in conn.execute("SELECT * FROM officer_chat_tags ORDER BY id ASC").fetchall()]
        chat_mention_rows = [dict(row) for row in conn.execute("SELECT * FROM officer_chat_mentions ORDER BY id ASC").fetchall()]
        notification_rows = [dict(row) for row in conn.execute("SELECT * FROM notifications ORDER BY id ASC").fetchall()]

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
            "phone_number",
            "instagram_handle",
            "first_event_date",
            "interests",
            "interests_norm",
            "stereotype",
            "photo_path",
            "photo_uploaded_at",
            "photo_uploaded_by",
            "lunch_stats",
            "notes",
            "total_lunches",
            "rating_count",
            "avg_good_with_girls",
            "avg_will_make_it",
            "avg_personable",
            "avg_alcohol_control",
            "avg_instagram_marketability",
            "weighted_total",
            "assigned_officer_id",
            "assigned_by",
            "assigned_at",
            "assignment_status",
            "assignment_priority",
            "assignment_due_date",
            "assignment_notes",
            "assignment_updated_at",
            "funnel_stage",
            "funnel_stage_reason",
            "funnel_stage_updated_at",
            "funnel_stage_updated_by",
            "created_by",
            "created_at",
            "updated_at",
        ], pnm_rows))
        zf.writestr("pnm_officer_assignments.csv", csv_bytes_from_rows(list(pnm_assignment_rows[0].keys()) if pnm_assignment_rows else [
            "id",
            "pnm_id",
            "officer_user_id",
            "assigned_by",
            "assigned_at",
            "is_primary",
            "created_at",
            "updated_at",
        ], pnm_assignment_rows))
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
        zf.writestr("rating_history.csv", csv_bytes_from_rows(list(rating_history_rows[0].keys()) if rating_history_rows else [
            "id",
            "rating_id",
            "pnm_id",
            "user_id",
            "event_type",
            "total_score",
            "good_with_girls",
            "will_make_it",
            "personable",
            "alcohol_control",
            "instagram_marketability",
            "changed_at",
        ], rating_history_rows))
        zf.writestr("rating_comment_events.csv", csv_bytes_from_rows(list(rating_comment_event_rows[0].keys()) if rating_comment_event_rows else [
            "id",
            "rating_id",
            "pnm_id",
            "user_id",
            "event_type",
            "old_total",
            "new_total",
            "delta_total",
            "comment",
            "changed_at",
        ], rating_comment_event_rows))
        zf.writestr("lunches.csv", csv_bytes_from_rows(list(lunch_rows[0].keys()) if lunch_rows else [
            "id",
            "pnm_id",
            "user_id",
            "lunch_date",
            "start_time",
            "end_time",
            "location",
            "notes",
            "created_at",
        ], lunch_rows))
        zf.writestr("rush_events.csv", csv_bytes_from_rows(list(rush_event_rows[0].keys()) if rush_event_rows else [
            "id",
            "title",
            "event_type",
            "event_date",
            "start_time",
            "end_time",
            "location",
            "details",
            "is_official",
            "is_cancelled",
            "created_by",
            "created_at",
            "updated_at",
        ], rush_event_rows))
        zf.writestr("engagement_events.csv", csv_bytes_from_rows(list(engagement_event_rows[0].keys()) if engagement_event_rows else [
            "id",
            "event_type",
            "status",
            "title",
            "event_date",
            "start_time",
            "end_time",
            "location",
            "details",
            "pnm_id",
            "owner_user_id",
            "source_type",
            "source_id",
            "created_by",
            "created_at",
            "updated_at",
        ], engagement_event_rows))
        zf.writestr("weekly_goals.csv", csv_bytes_from_rows(list(weekly_goal_rows[0].keys()) if weekly_goal_rows else [
            "id",
            "title",
            "description",
            "metric_type",
            "target_count",
            "manual_progress",
            "week_start",
            "week_end",
            "assigned_user_id",
            "created_by",
            "is_archived",
            "completed_at",
            "created_at",
            "updated_at",
        ], weekly_goal_rows))
        zf.writestr("pnm_stage_history.csv", csv_bytes_from_rows(list(stage_history_rows[0].keys()) if stage_history_rows else [
            "id",
            "pnm_id",
            "from_stage",
            "to_stage",
            "reason",
            "changed_by",
            "changed_at",
        ], stage_history_rows))
        zf.writestr("audit_ledger.csv", csv_bytes_from_rows(list(audit_rows[0].keys()) if audit_rows else [
            "id",
            "actor_user_id",
            "action_type",
            "entity_type",
            "entity_id",
            "payload_json",
            "created_at",
        ], audit_rows))
        zf.writestr("officer_chat_messages.csv", csv_bytes_from_rows(list(chat_rows[0].keys()) if chat_rows else [
            "id",
            "sender_id",
            "message",
            "tags",
            "created_at",
            "edited_at",
        ], chat_rows))
        zf.writestr("officer_chat_tags.csv", csv_bytes_from_rows(list(chat_tag_rows[0].keys()) if chat_tag_rows else [
            "id",
            "message_id",
            "tag",
            "created_at",
        ], chat_tag_rows))
        zf.writestr("officer_chat_mentions.csv", csv_bytes_from_rows(list(chat_mention_rows[0].keys()) if chat_mention_rows else [
            "id",
            "message_id",
            "user_id",
            "created_at",
        ], chat_mention_rows))
        zf.writestr("notifications.csv", csv_bytes_from_rows(list(notification_rows[0].keys()) if notification_rows else [
            "id",
            "user_id",
            "notif_type",
            "title",
            "body",
            "link_path",
            "is_read",
            "created_at",
        ], notification_rows))
        readme = (
            "KAO Rush Backup Export\n"
            f"Generated (UTC): {datetime.now(timezone.utc).isoformat()}\n"
            f"Database path: {db_path}\n"
            "Contains: users.csv, pnms.csv, ratings.csv, rating_changes.csv, rating_history.csv, rating_comment_events.csv, lunches.csv, rush_events.csv, engagement_events.csv, weekly_goals.csv, pnm_stage_history.csv, audit_ledger.csv, officer_chat_messages.csv, officer_chat_tags.csv, officer_chat_mentions.csv, notifications.csv\n"
            "Password hashes are intentionally excluded from users.csv for security.\n"
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
        "[startup] HEAD_SEED_ACCESS_CODE not provided. Generated an in-memory bootstrap credential. "
        "Set HEAD_SEED_ACCESS_CODE in production to disable runtime generation."
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


def create_notification(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    notif_type: str,
    title: str,
    body: str = "",
    link_path: str = "",
) -> None:
    if user_id <= 0:
        return
    conn.execute(
        """
        INSERT INTO notifications (
            user_id,
            notif_type,
            title,
            body,
            link_path,
            is_read,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, 0, ?)
        """,
        (
            user_id,
            notif_type.strip()[:32] or "info",
            title.strip()[:160] or "Update",
            body.strip()[:500],
            link_path.strip()[:200],
            now_iso(),
        ),
    )


def create_notifications_for_users(
    conn: sqlite3.Connection,
    user_ids: list[int] | set[int],
    *,
    notif_type: str,
    title: str,
    body: str = "",
    link_path: str = "",
) -> None:
    unique_ids = {int(item) for item in user_ids if int(item) > 0}
    for user_id in unique_ids:
        create_notification(
            conn,
            user_id=user_id,
            notif_type=notif_type,
            title=title,
            body=body,
            link_path=link_path,
        )


def append_audit_entry(
    conn: sqlite3.Connection,
    *,
    actor_user_id: int | None,
    action_type: str,
    entity_type: str,
    entity_id: int | None,
    payload: dict[str, Any] | None = None,
) -> None:
    action_token = action_type.strip().lower()[:64] or "update"
    entity_token = entity_type.strip().lower()[:64] or "resource"
    payload_json = json.dumps(payload or {}, ensure_ascii=True, separators=(",", ":"))
    conn.execute(
        """
        INSERT INTO audit_ledger (
            actor_user_id,
            action_type,
            entity_type,
            entity_id,
            payload_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            int(actor_user_id) if actor_user_id is not None else None,
            action_token,
            entity_token,
            int(entity_id) if entity_id is not None else None,
            payload_json,
            now_iso(),
        ),
    )


def assignment_due_state(status: str, due_date_raw: str | None) -> str:
    status_token = (status or "").strip().lower()
    if not due_date_raw:
        return "none"
    try:
        due_day = date.fromisoformat(due_date_raw)
    except ValueError:
        return "none"
    if status_token == "completed":
        return "done"
    today = date.today()
    if due_day < today:
        return "overdue"
    if due_day <= today + timedelta(days=max(1, ASSIGNMENT_DUE_SOON_DAYS)):
        return "due_soon"
    return "upcoming"


def clamped_assignment_priority(value: int | None) -> int:
    if value is None:
        return max(1, min(ASSIGNMENT_MAX_PRIORITY, ASSIGNMENT_DEFAULT_PRIORITY))
    return max(1, min(ASSIGNMENT_MAX_PRIORITY, int(value)))


def assignment_target_rows_for_pnm(
    conn: sqlite3.Connection,
    *,
    pnm_id: int,
    package_group_id: str | None,
) -> list[sqlite3.Row]:
    group_token = normalize_package_group_id(package_group_id)
    if group_token:
        rows = conn.execute(
            """
            SELECT *
            FROM pnms
            WHERE package_group_id = ?
            ORDER BY id ASC
            """,
            (group_token,),
        ).fetchall()
        if rows:
            return rows
    row = conn.execute("SELECT * FROM pnms WHERE id = ?", (pnm_id,)).fetchone()
    if not row:
        return []
    return [row]


def fetch_assignment_links_for_pnms(
    conn: sqlite3.Connection,
    *,
    pnm_ids: list[int],
) -> dict[int, list[dict[str, Any]]]:
    normalized_ids: list[int] = []
    seen: set[int] = set()
    for raw_id in pnm_ids:
        pnm_id = int(raw_id)
        if pnm_id <= 0 or pnm_id in seen:
            continue
        seen.add(pnm_id)
        normalized_ids.append(pnm_id)
    if not normalized_ids:
        return {}

    rows = conn.execute(
        """
        SELECT
            pa.pnm_id,
            pa.officer_user_id,
            pa.assigned_by,
            pa.assigned_at,
            pa.is_primary,
            u.username,
            u.role,
            u.emoji
        FROM pnm_officer_assignments pa
        JOIN users u ON u.id = pa.officer_user_id
        WHERE pa.pnm_id IN (SELECT CAST(value AS INTEGER) FROM json_each(?))
        ORDER BY
            pa.pnm_id ASC,
            pa.is_primary DESC,
            COALESCE(pa.assigned_at, pa.created_at, pa.updated_at) ASC,
            lower(u.username) ASC
        """,
        (json.dumps(normalized_ids),),
    ).fetchall()

    links_by_pnm: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        pnm_id = int(row["pnm_id"])
        links_by_pnm.setdefault(pnm_id, []).append(
            {
                "user_id": int(row["officer_user_id"]),
                "username": row["username"],
                "role": row["role"],
                "emoji": row["emoji"],
                "is_primary": bool(row["is_primary"]),
                "assigned_by": int(row["assigned_by"]) if row["assigned_by"] is not None else None,
                "assigned_at": row["assigned_at"],
            }
        )
    return links_by_pnm


def merge_assigned_officers_for_pnm_row(
    row: sqlite3.Row,
    linked_officers: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    officers: list[dict[str, Any]] = []
    seen: set[int] = set()
    primary_id = int(row["assigned_officer_id"]) if "assigned_officer_id" in row.keys() and row["assigned_officer_id"] is not None else None

    for raw in linked_officers or []:
        if not isinstance(raw, dict):
            continue
        user_id = int(raw.get("user_id") or 0)
        if user_id <= 0 or user_id in seen:
            continue
        seen.add(user_id)
        officers.append(
            {
                "user_id": user_id,
                "username": raw.get("username"),
                "role": raw.get("role") or ROLE_RUSH_OFFICER,
                "emoji": raw.get("emoji"),
                "is_primary": bool(raw.get("is_primary")) or (primary_id is not None and user_id == primary_id),
                "assigned_by": int(raw["assigned_by"]) if raw.get("assigned_by") is not None else None,
                "assigned_at": raw.get("assigned_at"),
            }
        )

    fallback_primary = assigned_officer_payload_from_row(row)
    if fallback_primary:
        fallback_user_id = int(fallback_primary["user_id"])
        if fallback_user_id not in seen:
            officers.insert(
                0,
                {
                    "user_id": fallback_user_id,
                    "username": fallback_primary.get("username"),
                    "role": fallback_primary.get("role") or ROLE_RUSH_OFFICER,
                    "emoji": fallback_primary.get("emoji"),
                    "is_primary": True,
                    "assigned_by": int(row["assigned_by"]) if "assigned_by" in row.keys() and row["assigned_by"] is not None else None,
                    "assigned_at": row["assigned_at"] if "assigned_at" in row.keys() else None,
                },
            )
            seen.add(fallback_user_id)

    if primary_id is not None:
        for officer in officers:
            officer["is_primary"] = int(officer["user_id"]) == primary_id
        if officers and not any(bool(item.get("is_primary")) for item in officers):
            officers[0]["is_primary"] = True
    else:
        primary_marked = False
        for officer in officers:
            if bool(officer.get("is_primary")) and not primary_marked:
                officer["is_primary"] = True
                primary_marked = True
            else:
                officer["is_primary"] = False

    officers.sort(
        key=lambda item: (
            0 if item.get("is_primary") else 1,
            str(item.get("username") or "").lower(),
            int(item.get("user_id") or 0),
        )
    )
    return officers


def sync_primary_assignment_links_for_pnm(
    conn: sqlite3.Connection,
    *,
    pnm_id: int,
    primary_officer_user_id: int | None,
    assigned_by: int | None,
    assigned_at: str | None,
    updated_at: str | None = None,
    clear_all_if_unassigned: bool = True,
) -> None:
    stamp = updated_at or now_iso()
    if primary_officer_user_id is None:
        if clear_all_if_unassigned:
            conn.execute("DELETE FROM pnm_officer_assignments WHERE pnm_id = ?", (pnm_id,))
            return
        conn.execute(
            """
            UPDATE pnm_officer_assignments
            SET is_primary = 0, updated_at = ?
            WHERE pnm_id = ?
            """,
            (stamp, pnm_id),
        )
        return

    assigned_stamp = assigned_at or stamp
    conn.execute(
        """
        INSERT INTO pnm_officer_assignments (
            pnm_id,
            officer_user_id,
            assigned_by,
            assigned_at,
            is_primary,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, 1, ?, ?)
        ON CONFLICT(pnm_id, officer_user_id) DO UPDATE SET
            assigned_by = COALESCE(excluded.assigned_by, pnm_officer_assignments.assigned_by),
            assigned_at = COALESCE(pnm_officer_assignments.assigned_at, excluded.assigned_at),
            is_primary = 1,
            updated_at = excluded.updated_at
        """,
        (
            int(pnm_id),
            int(primary_officer_user_id),
            int(assigned_by) if assigned_by is not None else None,
            assigned_stamp,
            assigned_stamp,
            stamp,
        ),
    )
    conn.execute(
        """
        UPDATE pnm_officer_assignments
        SET
            is_primary = CASE WHEN officer_user_id = ? THEN 1 ELSE 0 END,
            updated_at = ?
        WHERE pnm_id = ?
        """,
        (int(primary_officer_user_id), stamp, int(pnm_id)),
    )


def add_officer_assignment_link(
    conn: sqlite3.Connection,
    *,
    pnm_id: int,
    officer_user_id: int,
    assigned_by: int | None,
    assigned_at: str | None = None,
) -> None:
    stamp = now_iso()
    assigned_stamp = assigned_at or stamp
    conn.execute(
        """
        INSERT INTO pnm_officer_assignments (
            pnm_id,
            officer_user_id,
            assigned_by,
            assigned_at,
            is_primary,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, 0, ?, ?)
        ON CONFLICT(pnm_id, officer_user_id) DO UPDATE SET
            assigned_by = COALESCE(excluded.assigned_by, pnm_officer_assignments.assigned_by),
            assigned_at = COALESCE(pnm_officer_assignments.assigned_at, excluded.assigned_at),
            updated_at = excluded.updated_at
        """,
        (
            int(pnm_id),
            int(officer_user_id),
            int(assigned_by) if assigned_by is not None else None,
            assigned_stamp,
            assigned_stamp,
            stamp,
        ),
    )


def resolve_assignable_officer_or_400(conn: sqlite3.Connection, officer_user_id: int) -> sqlite3.Row:
    officer = conn.execute(
        "SELECT id, username, role, emoji, is_approved FROM users WHERE id = ?",
        (int(officer_user_id),),
    ).fetchone()
    if not officer:
        raise HTTPException(status_code=404, detail="Rush Officer not found.")
    if not bool(officer["is_approved"]):
        raise HTTPException(status_code=400, detail="Assignment target must be approved first.")
    if officer["role"] != ROLE_RUSH_OFFICER:
        raise HTTPException(status_code=400, detail="Assignment target must be a Rush Officer.")
    return officer


def pnm_payload_with_assignment_links(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    own_rating: dict[str, Any] | None,
    links_by_pnm: dict[int, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    pnm_id = int(row["id"])
    if links_by_pnm is None:
        links_by_pnm = fetch_assignment_links_for_pnms(conn, pnm_ids=[pnm_id])
    return pnm_payload(
        row,
        own_rating,
        assigned_officer=assigned_officer_payload_from_row(row),
        assigned_officers=links_by_pnm.get(pnm_id, []),
    )


def default_engagement_status_for_date(event_date_raw: str, *, is_cancelled: bool = False) -> str:
    if is_cancelled:
        return "cancelled"
    try:
        event_day = date.fromisoformat(event_date_raw)
    except ValueError:
        return "planned"
    return "attended" if event_day < date.today() else "planned"


def sync_engagement_event_from_lunch(conn: sqlite3.Connection, lunch_id: int) -> None:
    row = conn.execute(
        """
        SELECT
            l.id,
            l.pnm_id,
            l.user_id,
            l.lunch_date,
            l.start_time,
            l.end_time,
            l.location,
            l.notes,
            l.created_at,
            p.first_name,
            p.last_name
        FROM lunches l
        JOIN pnms p ON p.id = l.pnm_id
        WHERE l.id = ?
        """,
        (lunch_id,),
    ).fetchone()
    if not row:
        return

    status = default_engagement_status_for_date(row["lunch_date"])
    title = f"Lunch with {row['first_name']} {row['last_name']}"
    details = (row["notes"] or "").strip()
    location = (row["location"] or "").strip()
    updated_at = now_iso()
    conn.execute(
        """
        INSERT INTO engagement_events (
            event_type,
            status,
            title,
            event_date,
            start_time,
            end_time,
            location,
            details,
            pnm_id,
            owner_user_id,
            source_type,
            source_id,
            created_by,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'lunch', ?, ?, ?, ?)
        ON CONFLICT(source_type, source_id) DO UPDATE SET
            event_type = excluded.event_type,
            status = excluded.status,
            title = excluded.title,
            event_date = excluded.event_date,
            start_time = excluded.start_time,
            end_time = excluded.end_time,
            location = excluded.location,
            details = excluded.details,
            pnm_id = excluded.pnm_id,
            owner_user_id = excluded.owner_user_id,
            updated_at = excluded.updated_at
        """,
        (
            "lunch",
            status,
            title,
            row["lunch_date"],
            row["start_time"],
            row["end_time"],
            location,
            details,
            row["pnm_id"],
            row["user_id"],
            row["id"],
            row["user_id"],
            row["created_at"],
            updated_at,
        ),
    )


def sync_engagement_event_from_rush_event(conn: sqlite3.Connection, event_id: int) -> None:
    row = conn.execute(
        """
        SELECT
            id,
            title,
            event_type,
            event_date,
            start_time,
            end_time,
            location,
            details,
            is_cancelled,
            created_by,
            created_at
        FROM rush_events
        WHERE id = ?
        """,
        (event_id,),
    ).fetchone()
    if not row:
        return

    normalized_type = "meeting" if row["event_type"] == "meeting" else "rush_event"
    status = default_engagement_status_for_date(row["event_date"], is_cancelled=bool(row["is_cancelled"]))
    updated_at = now_iso()
    conn.execute(
        """
        INSERT INTO engagement_events (
            event_type,
            status,
            title,
            event_date,
            start_time,
            end_time,
            location,
            details,
            pnm_id,
            owner_user_id,
            source_type,
            source_id,
            created_by,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, 'rush_event', ?, ?, ?, ?)
        ON CONFLICT(source_type, source_id) DO UPDATE SET
            event_type = excluded.event_type,
            status = excluded.status,
            title = excluded.title,
            event_date = excluded.event_date,
            start_time = excluded.start_time,
            end_time = excluded.end_time,
            location = excluded.location,
            details = excluded.details,
            owner_user_id = excluded.owner_user_id,
            updated_at = excluded.updated_at
        """,
        (
            normalized_type,
            status,
            row["title"],
            row["event_date"],
            row["start_time"],
            row["end_time"],
            (row["location"] or "").strip(),
            (row["details"] or "").strip(),
            row["created_by"],
            row["id"],
            row["created_by"],
            row["created_at"],
            updated_at,
        ),
    )


def sync_engagement_events_from_sources(conn: sqlite3.Connection) -> None:
    lunch_rows = conn.execute("SELECT id FROM lunches ORDER BY id ASC").fetchall()
    for row in lunch_rows:
        sync_engagement_event_from_lunch(conn, int(row["id"]))

    rush_rows = conn.execute("SELECT id FROM rush_events ORDER BY id ASC").fetchall()
    for row in rush_rows:
        sync_engagement_event_from_rush_event(conn, int(row["id"]))

    conn.execute(
        """
        DELETE FROM engagement_events
        WHERE source_type = 'lunch'
          AND source_id NOT IN (SELECT id FROM lunches)
        """
    )
    conn.execute(
        """
        DELETE FROM engagement_events
        WHERE source_type = 'rush_event'
          AND source_id NOT IN (SELECT id FROM rush_events)
        """
    )


def resolve_goal_week_span(week_start_raw: str | None, week_end_raw: str | None) -> tuple[str, str]:
    today = date.today()
    default_start, default_end = week_bounds_for(today)
    week_start = parse_week_date(week_start_raw, default_start)
    week_end = parse_week_date(week_end_raw, week_start + timedelta(days=6))
    if week_end < week_start:
        raise ValueError("Week end must be on or after week start.")
    if (week_end - week_start).days > 20:
        raise ValueError("Week range cannot exceed 21 days.")
    return week_start.isoformat(), week_end.isoformat()


def weekly_goal_progress_count(conn: sqlite3.Connection, goal_row: sqlite3.Row) -> int:
    metric = str(goal_row["metric_type"])
    week_start = str(goal_row["week_start"])
    week_end = str(goal_row["week_end"])
    assigned_user_id = int(goal_row["assigned_user_id"]) if goal_row["assigned_user_id"] is not None else None

    if metric == "manual":
        return int(goal_row["manual_progress"] or 0)

    if metric == "ratings_submitted":
        if assigned_user_id:
            row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM rating_history
                WHERE user_id = ?
                  AND event_type IN ('create', 'update')
                  AND date(changed_at) BETWEEN ? AND ?
                """,
                (assigned_user_id, week_start, week_end),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM rating_history
                WHERE event_type IN ('create', 'update')
                  AND date(changed_at) BETWEEN ? AND ?
                """,
                (week_start, week_end),
            ).fetchone()
        return int(row["c"])

    if metric == "lunches_logged":
        if assigned_user_id:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM lunches WHERE user_id = ? AND lunch_date BETWEEN ? AND ?",
                (assigned_user_id, week_start, week_end),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM lunches WHERE lunch_date BETWEEN ? AND ?",
                (week_start, week_end),
            ).fetchone()
        return int(row["c"])

    if metric == "pnms_created":
        if assigned_user_id:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM pnms WHERE created_by = ? AND date(created_at) BETWEEN ? AND ?",
                (assigned_user_id, week_start, week_end),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM pnms WHERE date(created_at) BETWEEN ? AND ?",
                (week_start, week_end),
            ).fetchone()
        return int(row["c"])

    if metric == "chat_messages":
        if assigned_user_id:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM officer_chat_messages WHERE sender_id = ? AND date(created_at) BETWEEN ? AND ?",
                (assigned_user_id, week_start, week_end),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM officer_chat_messages WHERE date(created_at) BETWEEN ? AND ?",
                (week_start, week_end),
            ).fetchone()
        return int(row["c"])

    if metric == "rush_events_created":
        if assigned_user_id:
            row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM rush_events
                WHERE created_by = ?
                  AND is_cancelled = 0
                  AND event_date BETWEEN ? AND ?
                """,
                (assigned_user_id, week_start, week_end),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM rush_events
                WHERE is_cancelled = 0
                  AND event_date BETWEEN ? AND ?
                """,
                (week_start, week_end),
            ).fetchone()
        return int(row["c"])

    return 0


def weekly_goal_payload(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    progress_count = weekly_goal_progress_count(conn, row)
    target = max(1, int(row["target_count"]))
    computed_complete = progress_count >= target
    completed_at = row["completed_at"] if row["completed_at"] else None
    is_completed = bool(completed_at) or computed_complete
    today = date.today()
    try:
        week_end = date.fromisoformat(row["week_end"])
    except ValueError:
        week_end = today
    status = "completed" if is_completed else ("overdue" if week_end < today else "active")
    percent = round(min(100.0, (progress_count / target) * 100), 1)

    return {
        "goal_id": int(row["id"]),
        "title": row["title"],
        "description": row["description"],
        "metric_type": row["metric_type"],
        "metric_label": WEEKLY_GOAL_METRIC_LABELS.get(row["metric_type"], row["metric_type"]),
        "target_count": target,
        "progress_count": progress_count,
        "percent_complete": percent,
        "week_start": row["week_start"],
        "week_end": row["week_end"],
        "assigned_user_id": row["assigned_user_id"],
        "assigned_username": row["assigned_username"] if "assigned_username" in row.keys() else None,
        "created_by": row["created_by"],
        "created_by_username": row["created_by_username"] if "created_by_username" in row.keys() else None,
        "manual_progress": int(row["manual_progress"] or 0),
        "is_archived": bool(row["is_archived"]),
        "is_completed": is_completed,
        "status": status,
        "completed_at": completed_at,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def evaluate_weekly_goal_completions(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT
            g.*,
            assignee.username AS assigned_username,
            creator.username AS created_by_username
        FROM weekly_goals g
        LEFT JOIN users assignee ON assignee.id = g.assigned_user_id
        LEFT JOIN users creator ON creator.id = g.created_by
        WHERE g.is_archived = 0
          AND g.completed_at IS NULL
        ORDER BY g.week_start ASC, g.id ASC
        """
    ).fetchall()
    for row in rows:
        progress = weekly_goal_progress_count(conn, row)
        target = max(1, int(row["target_count"]))
        if progress < target:
            continue
        completed_at = now_iso()
        cursor = conn.execute(
            """
            UPDATE weekly_goals
            SET completed_at = ?, updated_at = ?
            WHERE id = ? AND completed_at IS NULL
            """,
            (completed_at, completed_at, row["id"]),
        )
        if cursor.rowcount <= 0:
            continue

        recipients: set[int] = {int(row["created_by"])}
        if row["assigned_user_id"] is not None:
            recipients.add(int(row["assigned_user_id"]))
        else:
            head_rows = conn.execute(
                "SELECT id FROM users WHERE role = ? AND is_approved = 1",
                (ROLE_HEAD,),
            ).fetchall()
            recipients.update(int(head_row["id"]) for head_row in head_rows)
        create_notifications_for_users(
            conn,
            recipients,
            notif_type="goal_completed",
            title=f"Goal Completed: {row['title']}",
            body=f"Progress reached {progress}/{target}.",
            link_path="/calendar",
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


def write_rating_history_event(
    conn: sqlite3.Connection,
    *,
    rating_id: int,
    pnm_id: int,
    user_id: int,
    event_type: str,
    scores: dict[str, int],
    changed_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO rating_history (
            rating_id,
            pnm_id,
            user_id,
            event_type,
            total_score,
            good_with_girls,
            will_make_it,
            personable,
            alcohol_control,
            instagram_marketability,
            changed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            rating_id,
            pnm_id,
            user_id,
            event_type,
            scores["total_score"],
            scores["good_with_girls"],
            scores["will_make_it"],
            scores["personable"],
            scores["alcohol_control"],
            scores["instagram_marketability"],
            changed_at,
        ),
    )


def write_rating_comment_event(
    conn: sqlite3.Connection,
    *,
    rating_id: int,
    pnm_id: int,
    user_id: int,
    event_type: str,
    old_total: int | None,
    new_total: int,
    delta_total: int,
    comment: str,
    changed_at: str,
) -> None:
    normalized_event = event_type.strip().lower()
    if normalized_event not in {"create", "update"}:
        raise ValueError("Unsupported rating comment event type.")
    normalized_comment = re.sub(r"\s+", " ", (comment or "").strip())
    if not normalized_comment:
        normalized_comment = "Initial rating submitted." if normalized_event == "create" else "Rating update logged."

    conn.execute(
        """
        INSERT INTO rating_comment_events (
            rating_id,
            pnm_id,
            user_id,
            event_type,
            old_total,
            new_total,
            delta_total,
            comment,
            changed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(rating_id),
            int(pnm_id),
            int(user_id),
            normalized_event,
            int(old_total) if old_total is not None else None,
            int(new_total),
            int(delta_total),
            normalized_comment,
            changed_at,
        ),
    )


def build_rating_trend_points(history_rows: list[sqlite3.Row], max_points: int = 240) -> list[dict[str, Any]]:
    latest_by_user: dict[int, tuple[int, str]] = {}
    points: list[dict[str, Any]] = []

    for row in history_rows:
        user_id = int(row["user_id"])
        total_score = int(row["total_score"])
        role = row["role"]
        latest_by_user[user_id] = (total_score, role)

        weighted_sum = 0.0
        total_weight = 0.0
        raw_sum = 0
        for score, user_role in latest_by_user.values():
            weight = role_weight(user_role)
            weighted_sum += score * weight
            total_weight += weight
            raw_sum += score

        count = len(latest_by_user)
        weighted_total = (weighted_sum / total_weight) if total_weight else 0.0
        avg_total = (raw_sum / count) if count else 0.0
        point = {
            "changed_at": row["changed_at"],
            "weighted_total": round(weighted_total, 2),
            "avg_total": round(avg_total, 2),
            "ratings_count": count,
            "event_type": row["event_type"],
        }
        points.append(point)

    if len(points) <= max_points:
        return points

    # Preserve trend shape by regular sampling and always keep final point.
    step = max(1, len(points) // max_points)
    sampled = [points[idx] for idx in range(0, len(points), step)]
    if sampled[-1] != points[-1]:
        sampled.append(points[-1])
    return sampled[-max_points:]


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
            city TEXT NOT NULL DEFAULT '',
            state_code TEXT NOT NULL DEFAULT '',
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
            onboarding_mode TEXT NOT NULL DEFAULT 'guided',
            onboarding_completed_at TEXT,
            onboarding_version INTEGER NOT NULL DEFAULT 0,
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
            hometown_state_code TEXT NOT NULL DEFAULT '',
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
            notes TEXT NOT NULL DEFAULT '',
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
            assignment_status TEXT NOT NULL DEFAULT 'unassigned' CHECK (assignment_status IN ('unassigned', 'assigned', 'in_progress', 'completed', 'needs_help')),
            assignment_priority INTEGER NOT NULL DEFAULT 3 CHECK (assignment_priority BETWEEN 1 AND 5),
            assignment_due_date TEXT,
            assignment_notes TEXT NOT NULL DEFAULT '',
            assignment_updated_at TEXT,
            package_group_id TEXT,
            funnel_stage TEXT NOT NULL DEFAULT 'sourced' CHECK (funnel_stage IN ('sourced', 'engaged', 'evaluated', 'discussed', 'bid', 'accepted', 'declined')),
            funnel_stage_reason TEXT NOT NULL DEFAULT '',
            funnel_stage_updated_at TEXT,
            funnel_stage_updated_by INTEGER REFERENCES users(id),
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pnm_officer_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pnm_id INTEGER NOT NULL REFERENCES pnms(id) ON DELETE CASCADE,
            officer_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            assigned_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            assigned_at TEXT NOT NULL,
            is_primary INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (pnm_id, officer_user_id)
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

        CREATE TABLE IF NOT EXISTS rating_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rating_id INTEGER NOT NULL REFERENCES ratings(id) ON DELETE CASCADE,
            pnm_id INTEGER NOT NULL REFERENCES pnms(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            event_type TEXT NOT NULL CHECK (event_type IN ('seed', 'create', 'update')),
            total_score INTEGER NOT NULL CHECK (total_score BETWEEN 0 AND 45),
            good_with_girls INTEGER NOT NULL CHECK (good_with_girls BETWEEN 0 AND 10),
            will_make_it INTEGER NOT NULL CHECK (will_make_it BETWEEN 0 AND 10),
            personable INTEGER NOT NULL CHECK (personable BETWEEN 0 AND 10),
            alcohol_control INTEGER NOT NULL CHECK (alcohol_control BETWEEN 0 AND 10),
            instagram_marketability INTEGER NOT NULL CHECK (instagram_marketability BETWEEN 0 AND 5),
            changed_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rating_comment_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rating_id INTEGER NOT NULL REFERENCES ratings(id) ON DELETE CASCADE,
            pnm_id INTEGER NOT NULL REFERENCES pnms(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            event_type TEXT NOT NULL CHECK (event_type IN ('create', 'update')),
            old_total INTEGER,
            new_total INTEGER NOT NULL CHECK (new_total BETWEEN 0 AND 45),
            delta_total INTEGER NOT NULL,
            comment TEXT NOT NULL DEFAULT '',
            changed_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS lunches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pnm_id INTEGER NOT NULL REFERENCES pnms(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            lunch_date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            location TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            UNIQUE (pnm_id, user_id, lunch_date)
        );

        CREATE TABLE IF NOT EXISTS rush_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            event_type TEXT NOT NULL CHECK (event_type IN ('official', 'roundtable', 'mixer', 'philanthropy', 'brotherhood', 'interview', 'meeting', 'social', 'other')),
            event_date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            location TEXT NOT NULL DEFAULT '',
            details TEXT NOT NULL DEFAULT '',
            is_official INTEGER NOT NULL DEFAULT 1,
            is_cancelled INTEGER NOT NULL DEFAULT 0,
            created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS weekly_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            metric_type TEXT NOT NULL CHECK (metric_type IN ('manual', 'ratings_submitted', 'lunches_logged', 'pnms_created', 'chat_messages', 'rush_events_created')),
            target_count INTEGER NOT NULL DEFAULT 1 CHECK (target_count >= 1),
            manual_progress INTEGER NOT NULL DEFAULT 0 CHECK (manual_progress >= 0),
            week_start TEXT NOT NULL,
            week_end TEXT NOT NULL,
            assigned_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            is_archived INTEGER NOT NULL DEFAULT 0,
            completed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS officer_chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            edited_at TEXT
        );

        CREATE TABLE IF NOT EXISTS officer_chat_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL REFERENCES officer_chat_messages(id) ON DELETE CASCADE,
            tag TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (message_id, tag)
        );

        CREATE TABLE IF NOT EXISTS officer_chat_mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL REFERENCES officer_chat_messages(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            UNIQUE (message_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            notif_type TEXT NOT NULL DEFAULT 'info',
            title TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            link_path TEXT NOT NULL DEFAULT '',
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_contact_downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            pnm_id INTEGER NOT NULL REFERENCES pnms(id) ON DELETE CASCADE,
            downloaded_at TEXT NOT NULL,
            UNIQUE (user_id, pnm_id)
        );

        CREATE TABLE IF NOT EXISTS engagement_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL CHECK (event_type IN ('lunch', 'rush_event', 'meeting', 'follow_up')),
            status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'attended', 'no_show', 'cancelled')),
            title TEXT NOT NULL,
            event_date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            location TEXT NOT NULL DEFAULT '',
            details TEXT NOT NULL DEFAULT '',
            pnm_id INTEGER REFERENCES pnms(id) ON DELETE SET NULL,
            owner_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            source_type TEXT NOT NULL DEFAULT 'manual' CHECK (source_type IN ('manual', 'lunch', 'rush_event')),
            source_id INTEGER,
            created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (source_type, source_id)
        );

        CREATE TABLE IF NOT EXISTS pnm_stage_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pnm_id INTEGER NOT NULL REFERENCES pnms(id) ON DELETE CASCADE,
            from_stage TEXT NOT NULL,
            to_stage TEXT NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            changed_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            changed_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            action_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            max_idle_seconds INTEGER NOT NULL DEFAULT 43200
        );

        CREATE TABLE IF NOT EXISTS season_archive_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            archive_path TEXT NOT NULL,
            archived_at TEXT NOT NULL,
            archived_by INTEGER NOT NULL REFERENCES users(id),
            archive_label TEXT NOT NULL DEFAULT '',
            pnm_count INTEGER NOT NULL DEFAULT 0,
            rating_count INTEGER NOT NULL DEFAULT 0,
            lunch_count INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_users_stereotype ON users(stereotype);
        CREATE INDEX IF NOT EXISTS idx_users_interests ON users(interests_norm);
        CREATE INDEX IF NOT EXISTS idx_pnms_stereotype ON pnms(stereotype);
        CREATE INDEX IF NOT EXISTS idx_pnms_interests ON pnms(interests_norm);
        CREATE INDEX IF NOT EXISTS idx_pnm_officer_assignments_pnm ON pnm_officer_assignments(pnm_id);
        CREATE INDEX IF NOT EXISTS idx_pnm_officer_assignments_officer ON pnm_officer_assignments(officer_user_id);
        CREATE INDEX IF NOT EXISTS idx_pnm_officer_assignments_primary ON pnm_officer_assignments(pnm_id, is_primary);
        CREATE INDEX IF NOT EXISTS idx_ratings_pnm ON ratings(pnm_id);
        CREATE INDEX IF NOT EXISTS idx_ratings_user ON ratings(user_id);
        CREATE INDEX IF NOT EXISTS idx_rating_history_pnm_changed_at ON rating_history(pnm_id, changed_at);
        CREATE INDEX IF NOT EXISTS idx_rating_history_rating_changed_at ON rating_history(rating_id, changed_at);
        CREATE INDEX IF NOT EXISTS idx_rating_comment_events_pnm_changed_at ON rating_comment_events(pnm_id, changed_at);
        CREATE INDEX IF NOT EXISTS idx_rating_comment_events_rating_changed_at ON rating_comment_events(rating_id, changed_at);
        CREATE INDEX IF NOT EXISTS idx_lunches_pnm ON lunches(pnm_id);
        CREATE INDEX IF NOT EXISTS idx_lunches_user ON lunches(user_id);
        CREATE INDEX IF NOT EXISTS idx_rush_events_date ON rush_events(event_date, start_time);
        CREATE INDEX IF NOT EXISTS idx_rush_events_created_by ON rush_events(created_by);
        CREATE INDEX IF NOT EXISTS idx_weekly_goals_week ON weekly_goals(week_start, week_end);
        CREATE INDEX IF NOT EXISTS idx_weekly_goals_assigned_user ON weekly_goals(assigned_user_id);
        CREATE INDEX IF NOT EXISTS idx_officer_chat_messages_created_at ON officer_chat_messages(created_at);
        CREATE INDEX IF NOT EXISTS idx_officer_chat_messages_sender ON officer_chat_messages(sender_id);
        CREATE INDEX IF NOT EXISTS idx_officer_chat_tags_tag ON officer_chat_tags(tag);
        CREATE INDEX IF NOT EXISTS idx_officer_chat_mentions_user ON officer_chat_mentions(user_id);
        CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications(user_id, is_read, created_at);
        CREATE INDEX IF NOT EXISTS idx_user_contact_downloads_user ON user_contact_downloads(user_id, downloaded_at);
        CREATE INDEX IF NOT EXISTS idx_user_contact_downloads_pnm ON user_contact_downloads(pnm_id);
        CREATE INDEX IF NOT EXISTS idx_engagement_events_date ON engagement_events(event_date, start_time);
        CREATE INDEX IF NOT EXISTS idx_engagement_events_status ON engagement_events(status);
        CREATE INDEX IF NOT EXISTS idx_engagement_events_owner ON engagement_events(owner_user_id);
        CREATE INDEX IF NOT EXISTS idx_engagement_events_pnm ON engagement_events(pnm_id);
        CREATE INDEX IF NOT EXISTS idx_engagement_events_source ON engagement_events(source_type, source_id);
        CREATE INDEX IF NOT EXISTS idx_pnm_stage_history_pnm_changed_at ON pnm_stage_history(pnm_id, changed_at);
        CREATE INDEX IF NOT EXISTS idx_audit_ledger_created_at ON audit_ledger(created_at);
        CREATE INDEX IF NOT EXISTS idx_audit_ledger_entity ON audit_ledger(entity_type, entity_id, created_at);
        """
    )


def ensure_schema_upgrades(conn: sqlite3.Connection) -> None:
    user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "onboarding_mode" not in user_columns:
        conn.execute(f"ALTER TABLE users ADD COLUMN onboarding_mode TEXT NOT NULL DEFAULT '{ONBOARDING_DEFAULT_MODE}'")
    if "onboarding_completed_at" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN onboarding_completed_at TEXT")
    if "onboarding_version" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN onboarding_version INTEGER NOT NULL DEFAULT 0")
    if "city" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN city TEXT NOT NULL DEFAULT ''")
    if "state_code" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN state_code TEXT NOT NULL DEFAULT ''")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_state_code ON users(state_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_city ON users(city)")
    conn.execute("UPDATE users SET city = '' WHERE city IS NULL")
    conn.execute("UPDATE users SET state_code = '' WHERE state_code IS NULL")
    state_rows = conn.execute(
        "SELECT id, state_code FROM users WHERE state_code IS NOT NULL AND trim(state_code) != ''"
    ).fetchall()
    for row in state_rows:
        normalized_state = normalize_state_code(row["state_code"])
        if normalized_state != str(row["state_code"] or "").strip():
            conn.execute(
                "UPDATE users SET state_code = ?, updated_at = COALESCE(NULLIF(updated_at, ''), ?) WHERE id = ?",
                (normalized_state, now_iso(), int(row["id"])),
            )
    city_rows = conn.execute(
        "SELECT id, city FROM users WHERE city IS NOT NULL AND city != trim(city)"
    ).fetchall()
    for row in city_rows:
        conn.execute(
            "UPDATE users SET city = ?, updated_at = COALESCE(NULLIF(updated_at, ''), ?) WHERE id = ?",
            (normalize_city_value(row["city"]), now_iso(), int(row["id"])),
        )
    conn.execute(
        "UPDATE users SET onboarding_mode = ? WHERE onboarding_mode IS NULL OR trim(onboarding_mode) = ''",
        (ONBOARDING_DEFAULT_MODE,),
    )
    conn.execute(
        """
        UPDATE users
        SET onboarding_mode = ?
        WHERE lower(trim(onboarding_mode)) NOT IN ('quick', 'guided', 'advanced')
        """,
        (ONBOARDING_DEFAULT_MODE,),
    )
    conn.execute(
        "UPDATE users SET onboarding_version = 0 WHERE onboarding_version IS NULL OR onboarding_version < 0"
    )
    # Existing users with successful logins are treated as already onboarded.
    conn.execute(
        """
        UPDATE users
        SET
            onboarding_completed_at = COALESCE(onboarding_completed_at, last_login_at),
            onboarding_version = CASE
                WHEN (COALESCE(onboarding_completed_at, last_login_at, '') != '') AND onboarding_version < ? THEN ?
                ELSE onboarding_version
            END
        """,
        (ONBOARDING_TUTORIAL_VERSION, ONBOARDING_TUTORIAL_VERSION),
    )

    pnm_columns = {row["name"] for row in conn.execute("PRAGMA table_info(pnms)").fetchall()}
    if "hometown_state_code" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN hometown_state_code TEXT NOT NULL DEFAULT ''")
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
    if "notes" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN notes TEXT NOT NULL DEFAULT ''")
    if "assignment_status" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN assignment_status TEXT NOT NULL DEFAULT 'unassigned'")
    if "assignment_priority" not in pnm_columns:
        conn.execute(
            f"ALTER TABLE pnms ADD COLUMN assignment_priority INTEGER NOT NULL DEFAULT {max(1, min(ASSIGNMENT_MAX_PRIORITY, ASSIGNMENT_DEFAULT_PRIORITY))}"
        )
    if "assignment_due_date" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN assignment_due_date TEXT")
    if "assignment_notes" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN assignment_notes TEXT NOT NULL DEFAULT ''")
    if "assignment_updated_at" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN assignment_updated_at TEXT")
    if "package_group_id" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN package_group_id TEXT")
    if "funnel_stage" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN funnel_stage TEXT NOT NULL DEFAULT 'sourced'")
    if "funnel_stage_reason" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN funnel_stage_reason TEXT NOT NULL DEFAULT ''")
    if "funnel_stage_updated_at" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN funnel_stage_updated_at TEXT")
    if "funnel_stage_updated_by" not in pnm_columns:
        conn.execute("ALTER TABLE pnms ADD COLUMN funnel_stage_updated_by INTEGER REFERENCES users(id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pnms_assigned_officer ON pnms(assigned_officer_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pnms_assignment_status ON pnms(assignment_status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pnms_assignment_due_date ON pnms(assignment_due_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pnms_funnel_stage ON pnms(funnel_stage)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pnms_package_group ON pnms(package_group_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pnms_hometown_state_code ON pnms(hometown_state_code)")
    conn.execute("UPDATE pnms SET hometown_state_code = '' WHERE hometown_state_code IS NULL")
    pnm_state_rows = conn.execute(
        "SELECT id, hometown, hometown_state_code FROM pnms"
    ).fetchall()
    for row in pnm_state_rows:
        resolved_state = resolve_pnm_state_code(row["hometown"], row["hometown_state_code"])
        stored_state = normalize_state_code(row["hometown_state_code"])
        if resolved_state != stored_state:
            conn.execute(
                "UPDATE pnms SET hometown_state_code = ?, updated_at = COALESCE(NULLIF(updated_at, ''), ?) WHERE id = ?",
                (resolved_state, now_iso(), int(row["id"])),
            )
    conn.execute(
        """
        UPDATE pnms
        SET assignment_status = CASE
            WHEN assigned_officer_id IS NULL THEN 'unassigned'
            WHEN assignment_status IS NULL OR trim(assignment_status) = '' THEN 'assigned'
            ELSE assignment_status
        END
        """
    )
    conn.execute(
        """
        UPDATE pnms
        SET assignment_status = CASE
            WHEN assigned_officer_id IS NULL THEN 'unassigned'
            ELSE 'assigned'
        END
        WHERE lower(trim(COALESCE(assignment_status, ''))) NOT IN ('unassigned', 'assigned', 'in_progress', 'completed', 'needs_help')
        """
    )
    conn.execute(
        """
        UPDATE pnms
        SET assignment_priority = ?
        WHERE assignment_priority IS NULL OR assignment_priority < 1 OR assignment_priority > ?
        """,
        (
            max(1, min(ASSIGNMENT_MAX_PRIORITY, ASSIGNMENT_DEFAULT_PRIORITY)),
            ASSIGNMENT_MAX_PRIORITY,
        ),
    )
    conn.execute(
        """
        UPDATE pnms
        SET assignment_updated_at = COALESCE(assignment_updated_at, assigned_at, updated_at, created_at)
        WHERE assignment_updated_at IS NULL OR trim(assignment_updated_at) = ''
        """
    )
    conn.execute(
        """
        UPDATE pnms
        SET package_group_id = NULL
        WHERE package_group_id IS NOT NULL AND trim(package_group_id) = ''
        """
    )
    conn.execute(
        """
        UPDATE pnms
        SET funnel_stage = CASE
            WHEN funnel_stage IS NULL OR trim(funnel_stage) = '' THEN
                CASE
                    WHEN weighted_total > 0 THEN 'evaluated'
                    WHEN total_lunches > 0 THEN 'engaged'
                    ELSE 'sourced'
                END
            ELSE lower(trim(funnel_stage))
        END
        """
    )
    conn.execute(
        """
        UPDATE pnms
        SET funnel_stage = 'sourced'
        WHERE funnel_stage NOT IN ('sourced', 'engaged', 'evaluated', 'discussed', 'bid', 'accepted', 'declined')
        """
    )
    conn.execute(
        """
        UPDATE pnms
        SET funnel_stage_updated_at = COALESCE(funnel_stage_updated_at, updated_at, created_at)
        WHERE funnel_stage_updated_at IS NULL OR trim(funnel_stage_updated_at) = ''
        """
    )

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS pnm_officer_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pnm_id INTEGER NOT NULL REFERENCES pnms(id) ON DELETE CASCADE,
            officer_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            assigned_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            assigned_at TEXT NOT NULL,
            is_primary INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (pnm_id, officer_user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_pnm_officer_assignments_pnm ON pnm_officer_assignments(pnm_id);
        CREATE INDEX IF NOT EXISTS idx_pnm_officer_assignments_officer ON pnm_officer_assignments(officer_user_id);
        CREATE INDEX IF NOT EXISTS idx_pnm_officer_assignments_primary ON pnm_officer_assignments(pnm_id, is_primary);
        """
    )
    link_sync_stamp = now_iso()
    conn.execute(
        """
        INSERT INTO pnm_officer_assignments (
            pnm_id,
            officer_user_id,
            assigned_by,
            assigned_at,
            is_primary,
            created_at,
            updated_at
        )
        SELECT
            p.id,
            p.assigned_officer_id,
            p.assigned_by,
            COALESCE(p.assigned_at, p.assignment_updated_at, p.updated_at, p.created_at, ?),
            1,
            COALESCE(p.assigned_at, p.assignment_updated_at, p.updated_at, p.created_at, ?),
            ?
        FROM pnms p
        JOIN users u ON u.id = p.assigned_officer_id
        WHERE p.assigned_officer_id IS NOT NULL
          AND u.role = 'Rush Officer'
          AND u.is_approved = 1
        ON CONFLICT(pnm_id, officer_user_id) DO UPDATE SET
            assigned_by = COALESCE(excluded.assigned_by, pnm_officer_assignments.assigned_by),
            assigned_at = COALESCE(pnm_officer_assignments.assigned_at, excluded.assigned_at),
            is_primary = 1,
            updated_at = excluded.updated_at
        """,
        (link_sync_stamp, link_sync_stamp, link_sync_stamp),
    )
    conn.execute(
        """
        UPDATE pnm_officer_assignments
        SET
            is_primary = CASE
                WHEN officer_user_id = COALESCE((SELECT assigned_officer_id FROM pnms WHERE id = pnm_id), -1) THEN 1
                ELSE 0
            END,
            updated_at = ?
        """,
        (link_sync_stamp,),
    )

    lunch_columns = {row["name"] for row in conn.execute("PRAGMA table_info(lunches)").fetchall()}
    if "start_time" not in lunch_columns:
        conn.execute("ALTER TABLE lunches ADD COLUMN start_time TEXT")
    if "end_time" not in lunch_columns:
        conn.execute("ALTER TABLE lunches ADD COLUMN end_time TEXT")
    if "location" not in lunch_columns:
        conn.execute("ALTER TABLE lunches ADD COLUMN location TEXT NOT NULL DEFAULT ''")

    session_columns = {row["name"] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()}
    if "max_idle_seconds" not in session_columns:
        conn.execute(f"ALTER TABLE sessions ADD COLUMN max_idle_seconds INTEGER NOT NULL DEFAULT {SESSION_TTL_SECONDS}")
    conn.execute(
        "UPDATE sessions SET max_idle_seconds = ? WHERE max_idle_seconds IS NULL OR max_idle_seconds <= 0",
        (SESSION_TTL_SECONDS,),
    )

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS rating_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rating_id INTEGER NOT NULL REFERENCES ratings(id) ON DELETE CASCADE,
            pnm_id INTEGER NOT NULL REFERENCES pnms(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            event_type TEXT NOT NULL CHECK (event_type IN ('seed', 'create', 'update')),
            total_score INTEGER NOT NULL CHECK (total_score BETWEEN 0 AND 45),
            good_with_girls INTEGER NOT NULL CHECK (good_with_girls BETWEEN 0 AND 10),
            will_make_it INTEGER NOT NULL CHECK (will_make_it BETWEEN 0 AND 10),
            personable INTEGER NOT NULL CHECK (personable BETWEEN 0 AND 10),
            alcohol_control INTEGER NOT NULL CHECK (alcohol_control BETWEEN 0 AND 10),
            instagram_marketability INTEGER NOT NULL CHECK (instagram_marketability BETWEEN 0 AND 5),
            changed_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_rating_history_pnm_changed_at ON rating_history(pnm_id, changed_at);
        CREATE INDEX IF NOT EXISTS idx_rating_history_rating_changed_at ON rating_history(rating_id, changed_at);

        CREATE TABLE IF NOT EXISTS rating_comment_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rating_id INTEGER NOT NULL REFERENCES ratings(id) ON DELETE CASCADE,
            pnm_id INTEGER NOT NULL REFERENCES pnms(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            event_type TEXT NOT NULL CHECK (event_type IN ('create', 'update')),
            old_total INTEGER,
            new_total INTEGER NOT NULL CHECK (new_total BETWEEN 0 AND 45),
            delta_total INTEGER NOT NULL,
            comment TEXT NOT NULL DEFAULT '',
            changed_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_rating_comment_events_pnm_changed_at ON rating_comment_events(pnm_id, changed_at);
        CREATE INDEX IF NOT EXISTS idx_rating_comment_events_rating_changed_at ON rating_comment_events(rating_id, changed_at);
        """
    )

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS season_archive_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            archive_path TEXT NOT NULL,
            archived_at TEXT NOT NULL,
            archived_by INTEGER NOT NULL REFERENCES users(id),
            archive_label TEXT NOT NULL DEFAULT '',
            pnm_count INTEGER NOT NULL DEFAULT 0,
            rating_count INTEGER NOT NULL DEFAULT 0,
            lunch_count INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    season_columns = {row["name"] for row in conn.execute("PRAGMA table_info(season_archive_state)").fetchall()}
    if "archive_label" not in season_columns:
        conn.execute("ALTER TABLE season_archive_state ADD COLUMN archive_label TEXT NOT NULL DEFAULT ''")
    if "pnm_count" not in season_columns:
        conn.execute("ALTER TABLE season_archive_state ADD COLUMN pnm_count INTEGER NOT NULL DEFAULT 0")
    if "rating_count" not in season_columns:
        conn.execute("ALTER TABLE season_archive_state ADD COLUMN rating_count INTEGER NOT NULL DEFAULT 0")
    if "lunch_count" not in season_columns:
        conn.execute("ALTER TABLE season_archive_state ADD COLUMN lunch_count INTEGER NOT NULL DEFAULT 0")

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS rush_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            event_type TEXT NOT NULL CHECK (event_type IN ('official', 'roundtable', 'mixer', 'philanthropy', 'brotherhood', 'interview', 'meeting', 'social', 'other')),
            event_date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            location TEXT NOT NULL DEFAULT '',
            details TEXT NOT NULL DEFAULT '',
            is_official INTEGER NOT NULL DEFAULT 1,
            is_cancelled INTEGER NOT NULL DEFAULT 0,
            created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_rush_events_date ON rush_events(event_date, start_time);
        CREATE INDEX IF NOT EXISTS idx_rush_events_created_by ON rush_events(created_by);

        CREATE TABLE IF NOT EXISTS weekly_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            metric_type TEXT NOT NULL CHECK (metric_type IN ('manual', 'ratings_submitted', 'lunches_logged', 'pnms_created', 'chat_messages', 'rush_events_created')),
            target_count INTEGER NOT NULL DEFAULT 1 CHECK (target_count >= 1),
            manual_progress INTEGER NOT NULL DEFAULT 0 CHECK (manual_progress >= 0),
            week_start TEXT NOT NULL,
            week_end TEXT NOT NULL,
            assigned_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            is_archived INTEGER NOT NULL DEFAULT 0,
            completed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_weekly_goals_week ON weekly_goals(week_start, week_end);
        CREATE INDEX IF NOT EXISTS idx_weekly_goals_assigned_user ON weekly_goals(assigned_user_id);

        CREATE TABLE IF NOT EXISTS officer_chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            edited_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_officer_chat_messages_created_at ON officer_chat_messages(created_at);
        CREATE INDEX IF NOT EXISTS idx_officer_chat_messages_sender ON officer_chat_messages(sender_id);

        CREATE TABLE IF NOT EXISTS officer_chat_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL REFERENCES officer_chat_messages(id) ON DELETE CASCADE,
            tag TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (message_id, tag)
        );
        CREATE INDEX IF NOT EXISTS idx_officer_chat_tags_tag ON officer_chat_tags(tag);

        CREATE TABLE IF NOT EXISTS officer_chat_mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL REFERENCES officer_chat_messages(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            UNIQUE (message_id, user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_officer_chat_mentions_user ON officer_chat_mentions(user_id);

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            notif_type TEXT NOT NULL DEFAULT 'info',
            title TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            link_path TEXT NOT NULL DEFAULT '',
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications(user_id, is_read, created_at);

        CREATE TABLE IF NOT EXISTS user_contact_downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            pnm_id INTEGER NOT NULL REFERENCES pnms(id) ON DELETE CASCADE,
            downloaded_at TEXT NOT NULL,
            UNIQUE (user_id, pnm_id)
        );
        CREATE INDEX IF NOT EXISTS idx_user_contact_downloads_user ON user_contact_downloads(user_id, downloaded_at);
        CREATE INDEX IF NOT EXISTS idx_user_contact_downloads_pnm ON user_contact_downloads(pnm_id);
        """
    )
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS engagement_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL CHECK (event_type IN ('lunch', 'rush_event', 'meeting', 'follow_up')),
            status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'attended', 'no_show', 'cancelled')),
            title TEXT NOT NULL,
            event_date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            location TEXT NOT NULL DEFAULT '',
            details TEXT NOT NULL DEFAULT '',
            pnm_id INTEGER REFERENCES pnms(id) ON DELETE SET NULL,
            owner_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            source_type TEXT NOT NULL DEFAULT 'manual' CHECK (source_type IN ('manual', 'lunch', 'rush_event')),
            source_id INTEGER,
            created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (source_type, source_id)
        );
        CREATE INDEX IF NOT EXISTS idx_engagement_events_date ON engagement_events(event_date, start_time);
        CREATE INDEX IF NOT EXISTS idx_engagement_events_status ON engagement_events(status);
        CREATE INDEX IF NOT EXISTS idx_engagement_events_owner ON engagement_events(owner_user_id);
        CREATE INDEX IF NOT EXISTS idx_engagement_events_pnm ON engagement_events(pnm_id);
        CREATE INDEX IF NOT EXISTS idx_engagement_events_source ON engagement_events(source_type, source_id);

        CREATE TABLE IF NOT EXISTS pnm_stage_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pnm_id INTEGER NOT NULL REFERENCES pnms(id) ON DELETE CASCADE,
            from_stage TEXT NOT NULL,
            to_stage TEXT NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            changed_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            changed_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_pnm_stage_history_pnm_changed_at ON pnm_stage_history(pnm_id, changed_at);

        CREATE TABLE IF NOT EXISTS audit_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            action_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_audit_ledger_created_at ON audit_ledger(created_at);
        CREATE INDEX IF NOT EXISTS idx_audit_ledger_entity ON audit_ledger(entity_type, entity_id, created_at);
        """
    )
    weekly_goal_columns = {row["name"] for row in conn.execute("PRAGMA table_info(weekly_goals)").fetchall()}
    if "description" not in weekly_goal_columns:
        conn.execute("ALTER TABLE weekly_goals ADD COLUMN description TEXT NOT NULL DEFAULT ''")
    if "manual_progress" not in weekly_goal_columns:
        conn.execute("ALTER TABLE weekly_goals ADD COLUMN manual_progress INTEGER NOT NULL DEFAULT 0")
    if "assigned_user_id" not in weekly_goal_columns:
        conn.execute("ALTER TABLE weekly_goals ADD COLUMN assigned_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL")
    if "is_archived" not in weekly_goal_columns:
        conn.execute("ALTER TABLE weekly_goals ADD COLUMN is_archived INTEGER NOT NULL DEFAULT 0")
    if "completed_at" not in weekly_goal_columns:
        conn.execute("ALTER TABLE weekly_goals ADD COLUMN completed_at TEXT")
    if "updated_at" not in weekly_goal_columns:
        conn.execute("ALTER TABLE weekly_goals ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''")

    rush_event_columns = {row["name"] for row in conn.execute("PRAGMA table_info(rush_events)").fetchall()}
    if "is_cancelled" not in rush_event_columns:
        conn.execute("ALTER TABLE rush_events ADD COLUMN is_cancelled INTEGER NOT NULL DEFAULT 0")
    if "details" not in rush_event_columns:
        conn.execute("ALTER TABLE rush_events ADD COLUMN details TEXT NOT NULL DEFAULT ''")
    if "location" not in rush_event_columns:
        conn.execute("ALTER TABLE rush_events ADD COLUMN location TEXT NOT NULL DEFAULT ''")

    sync_engagement_events_from_sources(conn)

    # Backfill a baseline seed event for legacy ratings so trend charts can start from current stored state.
    conn.execute(
        """
        INSERT INTO rating_history (
            rating_id,
            pnm_id,
            user_id,
            event_type,
            total_score,
            good_with_girls,
            will_make_it,
            personable,
            alcohol_control,
            instagram_marketability,
            changed_at
        )
        SELECT
            r.id,
            r.pnm_id,
            r.user_id,
            'seed',
            r.total_score,
            r.good_with_girls,
            r.will_make_it,
            r.personable,
            r.alcohol_control,
            r.instagram_marketability,
            COALESCE(r.updated_at, r.created_at, ?)
        FROM ratings r
        WHERE NOT EXISTS (
            SELECT 1
            FROM rating_history rh
            WHERE rh.rating_id = r.id
        )
        """,
        (now_iso(),),
    )

    # Backfill comment events for legacy data so meeting view can show all stored rating comments.
    conn.execute(
        """
        INSERT INTO rating_comment_events (
            rating_id,
            pnm_id,
            user_id,
            event_type,
            old_total,
            new_total,
            delta_total,
            comment,
            changed_at
        )
        SELECT
            r.id,
            r.pnm_id,
            r.user_id,
            'create',
            NULL,
            r.total_score,
            0,
            COALESCE(NULLIF(trim(r.comment), ''), 'Initial rating submitted.'),
            COALESCE(r.created_at, r.updated_at, ?)
        FROM ratings r
        WHERE NOT EXISTS (
            SELECT 1
            FROM rating_comment_events rce
            WHERE rce.rating_id = r.id AND rce.event_type = 'create'
        )
        """,
        (now_iso(),),
    )
    conn.execute(
        """
        INSERT INTO rating_comment_events (
            rating_id,
            pnm_id,
            user_id,
            event_type,
            old_total,
            new_total,
            delta_total,
            comment,
            changed_at
        )
        SELECT
            rc.rating_id,
            rc.pnm_id,
            rc.user_id,
            'update',
            rc.old_total,
            rc.new_total,
            rc.delta_total,
            COALESCE(NULLIF(trim(rc.comment), ''), 'Rating update logged.'),
            rc.changed_at
        FROM rating_changes rc
        WHERE NOT EXISTS (
            SELECT 1
            FROM rating_comment_events rce
            WHERE rce.rating_id = rc.rating_id
              AND rce.event_type = 'update'
              AND rce.changed_at = rc.changed_at
        )
        """
    )


def ensure_package_link_schema(conn: sqlite3.Connection) -> None:
    required_columns = {
        "package_group_id",
        "assigned_officer_id",
        "assigned_by",
        "assigned_at",
        "assignment_status",
        "assignment_priority",
        "assignment_due_date",
        "assignment_notes",
        "assignment_updated_at",
    }
    pnm_columns = {row["name"] for row in conn.execute("PRAGMA table_info(pnms)").fetchall()}
    if required_columns.issubset(pnm_columns):
        return

    ensure_schema_upgrades(conn)
    refreshed_columns = {row["name"] for row in conn.execute("PRAGMA table_info(pnms)").fetchall()}
    missing_columns = sorted(required_columns.difference(refreshed_columns))
    if missing_columns:
        raise RuntimeError(f"PNM schema upgrade incomplete for package linking: missing {', '.join(missing_columns)}")


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

    require_bootstrap_secret_configured(
        access_code,
        env_name="HEAD_SEED_ACCESS_CODE",
        principal_label="Head rush officer",
    )
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
        "[startup] PLATFORM_ADMIN_ACCESS_CODE not provided. Generated an in-memory bootstrap credential. "
        "Set PLATFORM_ADMIN_ACCESS_CODE in production to disable runtime generation."
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
            last_seen_at TEXT NOT NULL,
            max_idle_seconds INTEGER NOT NULL DEFAULT 43200
        );

        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            chapter_name TEXT NOT NULL DEFAULT '',
            org_type TEXT NOT NULL DEFAULT 'Fraternity',
            setup_tagline TEXT NOT NULL DEFAULT '',
            logo_path TEXT,
            theme_primary TEXT NOT NULL DEFAULT '#8a1538',
            theme_secondary TEXT NOT NULL DEFAULT '#c99a2b',
            theme_tertiary TEXT NOT NULL DEFAULT '#1d7a4b',
            rating_criteria_json TEXT NOT NULL DEFAULT '',
            officer_weight REAL NOT NULL DEFAULT 0.6,
            rusher_weight REAL NOT NULL DEFAULT 0.4,
            default_interest_tags TEXT NOT NULL DEFAULT '',
            default_stereotype_tags TEXT NOT NULL DEFAULT '',
            calendar_share_token TEXT NOT NULL DEFAULT '',
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


def ensure_platform_schema_upgrades(conn: sqlite3.Connection) -> None:
    platform_session_columns = {row["name"] for row in conn.execute("PRAGMA table_info(platform_sessions)").fetchall()}
    if "max_idle_seconds" not in platform_session_columns:
        conn.execute(
            f"ALTER TABLE platform_sessions ADD COLUMN max_idle_seconds INTEGER NOT NULL DEFAULT {PLATFORM_SESSION_TTL_SECONDS}"
        )
    conn.execute(
        "UPDATE platform_sessions SET max_idle_seconds = ? WHERE max_idle_seconds IS NULL OR max_idle_seconds <= 0",
        (PLATFORM_SESSION_TTL_SECONDS,),
    )

    tenant_columns = {row["name"] for row in conn.execute("PRAGMA table_info(tenants)").fetchall()}
    if "calendar_share_token" not in tenant_columns:
        conn.execute("ALTER TABLE tenants ADD COLUMN calendar_share_token TEXT NOT NULL DEFAULT ''")
    if "org_type" not in tenant_columns:
        conn.execute(f"ALTER TABLE tenants ADD COLUMN org_type TEXT NOT NULL DEFAULT '{DEFAULT_ORG_TYPE}'")
    if "setup_tagline" not in tenant_columns:
        conn.execute("ALTER TABLE tenants ADD COLUMN setup_tagline TEXT NOT NULL DEFAULT ''")
    if "theme_tertiary" not in tenant_columns:
        conn.execute(f"ALTER TABLE tenants ADD COLUMN theme_tertiary TEXT NOT NULL DEFAULT '{DEFAULT_THEME_TERTIARY}'")
    if "rating_criteria_json" not in tenant_columns:
        conn.execute("ALTER TABLE tenants ADD COLUMN rating_criteria_json TEXT NOT NULL DEFAULT ''")
    if "officer_weight" not in tenant_columns:
        conn.execute("ALTER TABLE tenants ADD COLUMN officer_weight REAL NOT NULL DEFAULT 0.6")
    if "rusher_weight" not in tenant_columns:
        conn.execute("ALTER TABLE tenants ADD COLUMN rusher_weight REAL NOT NULL DEFAULT 0.4")
    if "default_interest_tags" not in tenant_columns:
        conn.execute("ALTER TABLE tenants ADD COLUMN default_interest_tags TEXT NOT NULL DEFAULT ''")
    if "default_stereotype_tags" not in tenant_columns:
        conn.execute("ALTER TABLE tenants ADD COLUMN default_stereotype_tags TEXT NOT NULL DEFAULT ''")

    default_criteria_json = json.dumps(default_rating_criteria(), separators=(",", ":"))
    default_interest_tags_json = json.dumps(DEFAULT_INTEREST_TAG_SUGGESTIONS, separators=(",", ":"))
    default_stereotype_tags_json = json.dumps(DEFAULT_STEREOTYPE_TAG_SUGGESTIONS, separators=(",", ":"))
    conn.execute(
        """
        UPDATE tenants
        SET
            org_type = COALESCE(NULLIF(trim(org_type), ''), ?),
            setup_tagline = COALESCE(setup_tagline, ''),
            theme_primary = COALESCE(NULLIF(trim(theme_primary), ''), ?),
            theme_secondary = COALESCE(NULLIF(trim(theme_secondary), ''), ?),
            theme_tertiary = COALESCE(NULLIF(trim(theme_tertiary), ''), ?),
            rating_criteria_json = COALESCE(NULLIF(trim(rating_criteria_json), ''), ?),
            officer_weight = CASE WHEN officer_weight > 0 THEN officer_weight ELSE 0.6 END,
            rusher_weight = CASE WHEN rusher_weight > 0 THEN rusher_weight ELSE 0.4 END,
            default_interest_tags = COALESCE(NULLIF(trim(default_interest_tags), ''), ?),
            default_stereotype_tags = COALESCE(NULLIF(trim(default_stereotype_tags), ''), ?)
        """,
        (
            DEFAULT_ORG_TYPE,
            DEFAULT_THEME_PRIMARY,
            DEFAULT_THEME_SECONDARY,
            DEFAULT_THEME_TERTIARY,
            default_criteria_json,
            default_interest_tags_json,
            default_stereotype_tags_json,
        ),
    )

    rows = conn.execute("SELECT id, calendar_share_token FROM tenants").fetchall()
    for row in rows:
        if (row["calendar_share_token"] or "").strip():
            continue
        conn.execute(
            "UPDATE tenants SET calendar_share_token = ?, updated_at = ? WHERE id = ?",
            (secrets.token_urlsafe(24), now_iso(), row["id"]),
        )


def ensure_platform_admin_seed(conn: sqlite3.Connection) -> None:
    created_at = now_iso()
    existing = conn.execute("SELECT id FROM platform_admins WHERE username = ?", (PLATFORM_ADMIN_USERNAME,)).fetchone()
    if existing:
        if PLATFORM_ADMIN_ACCESS_CODE:
            seed_access_code = resolve_platform_admin_access_code()
            conn.execute(
                "UPDATE platform_admins SET access_code_hash = ?, updated_at = ? WHERE id = ?",
                (hash_access_code(seed_access_code), created_at, existing["id"]),
            )
        return

    require_bootstrap_secret_configured(
        PLATFORM_ADMIN_ACCESS_CODE,
        env_name="PLATFORM_ADMIN_ACCESS_CODE",
        principal_label="Platform admin",
    )
    seed_access_code = resolve_platform_admin_access_code()
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
        existing_token = (row["calendar_share_token"] or "").strip() if "calendar_share_token" in row.keys() else ""
        calendar_share_token = existing_token or secrets.token_urlsafe(24)
        existing_db_path_raw = (row["db_path"] or "").strip()
        existing_db_path = Path(existing_db_path_raw).expanduser() if existing_db_path_raw else None
        preserved_db_path = existing_db_path or default_db_path

        if existing_db_path and existing_db_path != default_db_path:
            if not existing_db_path.exists():
                preserved_db_path = default_db_path
                print(
                    f"[startup] warning: prior default tenant DB path not found ({existing_db_path}). "
                    f"Switching to configured path {default_db_path}."
                )
            else:
                if not default_db_path.exists() and copy_sqlite_database(existing_db_path, default_db_path):
                    print(
                        f"[startup] migrated default tenant DB from {existing_db_path} to {default_db_path} "
                        "for persistent storage."
                    )
                if default_db_path.exists():
                    preserved_db_path = default_db_path
                else:
                    print(
                        f"[startup] warning: default tenant DB path differs from configured path and migration was not "
                        f"possible ({existing_db_path} -> {default_db_path}). Keeping existing path."
                    )

        conn.execute(
            """
            UPDATE tenants
            SET
                display_name = ?,
                db_path = ?,
                calendar_share_token = ?,
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
                str(preserved_db_path),
                calendar_share_token,
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
            calendar_share_token,
            db_path,
            head_seed_username,
            head_seed_first_name,
            head_seed_last_name,
            head_seed_pledge_class,
            created_at,
            updated_at,
            is_active
        )
        VALUES (?, ?, ?, NULL, '#8a1538', '#c99a2b', ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            DEFAULT_TENANT_SLUG,
            DEFAULT_TENANT_NAME,
            "KAO",
            secrets.token_urlsafe(24),
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


def ensure_demo_tenant_record(conn: sqlite3.Connection) -> sqlite3.Row | None:
    if not DEMO_ENABLED:
        return None

    slug = demo_tenant_slug()
    created_at = now_iso()
    demo_db_path = default_tenant_db_path(slug)
    row = conn.execute("SELECT * FROM tenants WHERE slug = ?", (slug,)).fetchone()
    setup_tagline = "Explore the full BidBoard workflow with live demo data."

    if row:
        existing_token = (row["calendar_share_token"] or "").strip() if "calendar_share_token" in row.keys() else ""
        calendar_share_token = existing_token or secrets.token_urlsafe(24)
        existing_db_path_raw = (row["db_path"] or "").strip()
        existing_db_path = Path(existing_db_path_raw).expanduser() if existing_db_path_raw else None
        preserved_db_path = existing_db_path or demo_db_path

        if existing_db_path and existing_db_path != demo_db_path:
            if not existing_db_path.exists():
                preserved_db_path = demo_db_path
                print(
                    f"[startup] warning: prior demo tenant DB path not found ({existing_db_path}). "
                    f"Switching to configured path {demo_db_path}."
                )
            else:
                if not demo_db_path.exists() and copy_sqlite_database(existing_db_path, demo_db_path):
                    print(
                        f"[startup] migrated demo tenant DB from {existing_db_path} to {demo_db_path} "
                        "for persistent storage."
                    )
                if demo_db_path.exists():
                    preserved_db_path = demo_db_path
                else:
                    print(
                        "[startup] warning: demo tenant DB migration to configured path was not possible "
                        f"({existing_db_path} -> {demo_db_path}). Keeping existing path."
                    )

        conn.execute(
            """
            UPDATE tenants
            SET
                display_name = ?,
                chapter_name = ?,
                org_type = ?,
                setup_tagline = ?,
                db_path = ?,
                calendar_share_token = ?,
                head_seed_username = ?,
                head_seed_first_name = ?,
                head_seed_last_name = ?,
                head_seed_pledge_class = ?,
                is_active = 1,
                updated_at = ?
            WHERE slug = ?
            """,
            (
                DEMO_TENANT_NAME,
                DEMO_TENANT_CHAPTER_NAME,
                "Fraternity",
                setup_tagline,
                str(preserved_db_path),
                calendar_share_token,
                DEMO_HEAD_USERNAME,
                DEMO_HEAD_FIRST_NAME,
                DEMO_HEAD_LAST_NAME,
                DEMO_HEAD_PLEDGE_CLASS,
                created_at,
                slug,
            ),
        )
        return conn.execute("SELECT * FROM tenants WHERE slug = ?", (slug,)).fetchone()

    conn.execute(
        """
        INSERT INTO tenants (
            slug,
            display_name,
            chapter_name,
            org_type,
            setup_tagline,
            logo_path,
            theme_primary,
            theme_secondary,
            theme_tertiary,
            rating_criteria_json,
            officer_weight,
            rusher_weight,
            default_interest_tags,
            default_stereotype_tags,
            calendar_share_token,
            db_path,
            head_seed_username,
            head_seed_first_name,
            head_seed_last_name,
            head_seed_pledge_class,
            created_at,
            updated_at,
            is_active
        )
        VALUES (?, ?, ?, ?, ?, NULL, '#0f4c81', '#c99a2b', '#1d7a4b', ?, 0.6, 0.4, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            slug,
            DEMO_TENANT_NAME,
            DEMO_TENANT_CHAPTER_NAME,
            "Fraternity",
            setup_tagline,
            json.dumps(default_rating_criteria(), separators=(",", ":")),
            json.dumps(DEFAULT_INTEREST_TAG_SUGGESTIONS, separators=(",", ":")),
            json.dumps(DEFAULT_STEREOTYPE_TAG_SUGGESTIONS, separators=(",", ":")),
            secrets.token_urlsafe(24),
            str(demo_db_path),
            DEMO_HEAD_USERNAME,
            DEMO_HEAD_FIRST_NAME,
            DEMO_HEAD_LAST_NAME,
            DEMO_HEAD_PLEDGE_CLASS,
            created_at,
            created_at,
        ),
    )
    return conn.execute("SELECT * FROM tenants WHERE slug = ?", (slug,)).fetchone()


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


def ensure_demo_seed_dataset(conn: sqlite3.Connection) -> None:
    def iso_at(days_offset: int, hour: int, minute: int = 0) -> str:
        base = datetime.now(timezone.utc) + timedelta(days=days_offset)
        return base.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()

    def date_at(days_offset: int) -> str:
        return (date.today() + timedelta(days=days_offset)).isoformat()

    def make_scores(good_with_girls: int, will_make_it: int, personable: int, alcohol_control: int, instagram: int) -> dict[str, int]:
        payload = {
            "good_with_girls": int(good_with_girls),
            "will_make_it": int(will_make_it),
            "personable": int(personable),
            "alcohol_control": int(alcohol_control),
            "instagram_marketability": int(instagram),
        }
        payload["total_score"] = score_total(payload)
        return payload

    def upsert_demo_user(
        *,
        username: str,
        first_name: str,
        last_name: str,
        pledge_class: str,
        role: str,
        emoji: str | None,
        stereotype: str,
        interests: list[str],
        access_code: str,
        approved: bool,
        approved_by: int | None,
    ) -> int:
        interests_csv, interests_norm = encode_interests(interests)
        stamp = now_iso()
        approved_at = iso_at(-14, 15, 0) if approved else None
        approved_by_value = int(approved_by) if approved and approved_by else None
        emoji_value = (emoji or "").strip() or None
        existing = conn.execute("SELECT id, created_at FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE users
                SET
                    first_name = ?,
                    last_name = ?,
                    pledge_class = ?,
                    role = ?,
                    emoji = ?,
                    stereotype = ?,
                    interests = ?,
                    interests_norm = ?,
                    access_code_hash = ?,
                    is_approved = ?,
                    approved_by = ?,
                    approved_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    first_name,
                    last_name,
                    pledge_class,
                    role,
                    emoji_value if role == ROLE_RUSH_OFFICER else None,
                    stereotype,
                    interests_csv,
                    interests_norm,
                    hash_access_code(access_code),
                    1 if approved else 0,
                    approved_by_value,
                    approved_at,
                    stamp,
                    int(existing["id"]),
                ),
            )
            return int(existing["id"])

        created_at = iso_at(-21, 16, 30)
        cursor = conn.execute(
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
                approved_by,
                approved_at,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                first_name,
                last_name,
                pledge_class,
                role,
                emoji_value if role == ROLE_RUSH_OFFICER else None,
                stereotype,
                interests_csv,
                interests_norm,
                hash_access_code(access_code),
                1 if approved else 0,
                approved_by_value,
                approved_at,
                created_at,
                stamp,
            ),
        )
        return int(cursor.lastrowid or 0)

    def upsert_demo_pnm(
        *,
        pnm_code: str,
        first_name: str,
        last_name: str,
        class_year: str,
        hometown: str,
        phone_number: str,
        instagram_handle: str,
        first_event_date: str,
        interests: list[str],
        stereotype: str,
        lunch_stats: str,
        notes: str,
        created_by: int,
        assigned_officer_id: int | None,
        assigned_by: int | None,
    ) -> int:
        interests_csv, interests_norm = encode_interests(interests)
        updated_at = now_iso()
        hometown_state_code = resolve_pnm_state_code(hometown)
        assigned_at = iso_at(-5, 12, 0) if assigned_officer_id else None
        existing = conn.execute("SELECT id, created_at FROM pnms WHERE pnm_code = ?", (pnm_code,)).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE pnms
                SET
                    first_name = ?,
                    last_name = ?,
                    class_year = ?,
                    hometown = ?,
                    hometown_state_code = ?,
                    phone_number = ?,
                    instagram_handle = ?,
                    first_event_date = ?,
                    interests = ?,
                    interests_norm = ?,
                    stereotype = ?,
                    lunch_stats = ?,
                    notes = ?,
                    assigned_officer_id = ?,
                    assigned_by = ?,
                    assigned_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    first_name,
                    last_name,
                    class_year,
                    hometown,
                    hometown_state_code,
                    phone_number,
                    instagram_handle,
                    first_event_date,
                    interests_csv,
                    interests_norm,
                    stereotype,
                    lunch_stats,
                    notes,
                    assigned_officer_id,
                    assigned_by,
                    assigned_at,
                    updated_at,
                    int(existing["id"]),
                ),
            )
            return int(existing["id"])

        cursor = conn.execute(
            """
            INSERT INTO pnms (
                pnm_code,
                first_name,
                last_name,
                class_year,
                hometown,
                hometown_state_code,
                phone_number,
                instagram_handle,
                first_event_date,
                interests,
                interests_norm,
                stereotype,
                lunch_stats,
                notes,
                assigned_officer_id,
                assigned_by,
                assigned_at,
                created_by,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pnm_code,
                first_name,
                last_name,
                class_year,
                hometown,
                hometown_state_code,
                phone_number,
                instagram_handle,
                first_event_date,
                interests_csv,
                interests_norm,
                stereotype,
                lunch_stats,
                notes,
                assigned_officer_id,
                assigned_by,
                assigned_at,
                created_by,
                iso_at(-15, 18, 0),
                updated_at,
            ),
        )
        return int(cursor.lastrowid or 0)

    fallback_access_code = "DemoPass123!"
    head_id = upsert_demo_user(
        username=DEMO_HEAD_USERNAME,
        first_name=DEMO_HEAD_FIRST_NAME,
        last_name=DEMO_HEAD_LAST_NAME,
        pledge_class=DEMO_HEAD_PLEDGE_CLASS,
        role=ROLE_HEAD,
        emoji=None,
        stereotype="Strategist",
        interests=["Leadership", "Analytics", "Recruitment"],
        access_code=DEMO_HEAD_ACCESS_CODE,
        approved=True,
        approved_by=None,
    )

    user_ids: dict[str, int] = {
        DEMO_HEAD_USERNAME: head_id,
        "officerjack": upsert_demo_user(
            username="officerjack",
            first_name="Jack",
            last_name="Miller",
            pledge_class="Fall23",
            role=ROLE_RUSH_OFFICER,
            emoji="🔥",
            stereotype="Connector",
            interests=["Sports", "Leadership", "Fitness"],
            access_code=fallback_access_code,
            approved=True,
            approved_by=head_id,
        ),
        "officerliam": upsert_demo_user(
            username="officerliam",
            first_name="Liam",
            last_name="Brooks",
            pledge_class="Fall24",
            role=ROLE_RUSH_OFFICER,
            emoji="⚡",
            stereotype="Mentor",
            interests=["Finance", "Outdoors", "Recruitment"],
            access_code=fallback_access_code,
            approved=True,
            approved_by=head_id,
        ),
        "officernoah": upsert_demo_user(
            username="officernoah",
            first_name="Noah",
            last_name="Grant",
            pledge_class="Spring24",
            role=ROLE_RUSH_OFFICER,
            emoji="🎯",
            stereotype="Builder",
            interests=["Academics", "Music", "Leadership"],
            access_code=fallback_access_code,
            approved=True,
            approved_by=head_id,
        ),
        "memberalex": upsert_demo_user(
            username="memberalex",
            first_name="Alex",
            last_name="Parker",
            pledge_class="Spring25",
            role=ROLE_RUSHER,
            emoji=None,
            stereotype="Social",
            interests=["Travel", "Sports", "Philanthropy"],
            access_code=fallback_access_code,
            approved=True,
            approved_by=head_id,
        ),
        "memberryan": upsert_demo_user(
            username="memberryan",
            first_name="Ryan",
            last_name="Cole",
            pledge_class="Spring25",
            role=ROLE_RUSHER,
            emoji=None,
            stereotype="Athlete",
            interests=["Fitness", "Outdoors", "Gaming"],
            access_code=fallback_access_code,
            approved=True,
            approved_by=head_id,
        ),
        "memberniko": upsert_demo_user(
            username="memberniko",
            first_name="Niko",
            last_name="West",
            pledge_class="Fall25",
            role=ROLE_RUSHER,
            emoji=None,
            stereotype="Scholar",
            interests=["Academics", "Finance", "Music"],
            access_code=fallback_access_code,
            approved=True,
            approved_by=head_id,
        ),
        "newmemberdemo": upsert_demo_user(
            username="newmemberdemo",
            first_name="Jordan",
            last_name="Lee",
            pledge_class="Spring26",
            role=ROLE_RUSHER,
            emoji=None,
            stereotype="Leader",
            interests=["Leadership", "Music"],
            access_code=fallback_access_code,
            approved=False,
            approved_by=None,
        ),
    }

    pnm_seed = [
        {
            "pnm_code": "DMB01202026",
            "first_name": "Ethan",
            "last_name": "Brooks",
            "class_year": "F",
            "hometown": "Nashville, TN",
            "phone_number": "(555) 201-1001",
            "instagram_handle": "@ethanbrooks",
            "first_event_date": date_at(-20),
            "interests": ["Leadership", "Sports", "Faith"],
            "stereotype": "Leader",
            "lunch_stats": "2 lunches this month",
            "notes": "Strong early buy-in and follows up quickly.",
            "assigned_officer": "officerjack",
        },
        {
            "pnm_code": "DJC01222026",
            "first_name": "Mason",
            "last_name": "Carter",
            "class_year": "S",
            "hometown": "Dallas, TX",
            "phone_number": "(555) 201-1002",
            "instagram_handle": "@masoncarter",
            "first_event_date": date_at(-18),
            "interests": ["Finance", "Entrepreneurship", "Travel"],
            "stereotype": "Builder",
            "lunch_stats": "1 lunch completed",
            "notes": "Great one-on-one conversations, needs more chapter touchpoints.",
            "assigned_officer": "officerliam",
        },
        {
            "pnm_code": "DTR01242026",
            "first_name": "Owen",
            "last_name": "Hayes",
            "class_year": "J",
            "hometown": "Atlanta, GA",
            "phone_number": "(555) 201-1003",
            "instagram_handle": "@owenhayes",
            "first_event_date": date_at(-16),
            "interests": ["Academics", "Outdoors", "Philanthropy"],
            "stereotype": "Scholar",
            "lunch_stats": "3 lunches logged",
            "notes": "High character, quieter in groups but very consistent.",
            "assigned_officer": "officernoah",
        },
        {
            "pnm_code": "DSW01252026",
            "first_name": "Dylan",
            "last_name": "Stone",
            "class_year": "F",
            "hometown": "Birmingham, AL",
            "phone_number": "(555) 201-1004",
            "instagram_handle": "@dylanstone",
            "first_event_date": date_at(-15),
            "interests": ["Fitness", "Sports", "Music"],
            "stereotype": "Athlete",
            "lunch_stats": "2 lunches completed",
            "notes": "Popular socially and shows up to every event.",
            "assigned_officer": "officerjack",
        },
        {
            "pnm_code": "DKM01272026",
            "first_name": "Caleb",
            "last_name": "Morris",
            "class_year": "S",
            "hometown": "Charlotte, NC",
            "phone_number": "(555) 201-1005",
            "instagram_handle": "@calebmorris",
            "first_event_date": date_at(-13),
            "interests": ["Gaming", "Music", "Leadership"],
            "stereotype": "Social",
            "lunch_stats": "1 lunch set",
            "notes": "Good personality, monitor consistency.",
            "assigned_officer": "officerliam",
        },
        {
            "pnm_code": "DAN01292026",
            "first_name": "Hudson",
            "last_name": "Knight",
            "class_year": "J",
            "hometown": "Memphis, TN",
            "phone_number": "(555) 201-1006",
            "instagram_handle": "@hudsonknight",
            "first_event_date": date_at(-11),
            "interests": ["Outdoors", "Travel", "Sports"],
            "stereotype": "Connector",
            "lunch_stats": "0 lunches so far",
            "notes": "Needs more officer contact this week.",
            "assigned_officer": "officernoah",
        },
        {
            "pnm_code": "DRV01302026",
            "first_name": "Gavin",
            "last_name": "Reed",
            "class_year": "F",
            "hometown": "Jackson, MS",
            "phone_number": "(555) 201-1007",
            "instagram_handle": "@gavinreed",
            "first_event_date": date_at(-10),
            "interests": ["Faith", "Philanthropy", "Leadership"],
            "stereotype": "Mentor",
            "lunch_stats": "2 lunches completed",
            "notes": "Great cultural fit and strong recommendations.",
            "assigned_officer": "officerjack",
        },
        {
            "pnm_code": "DPL02012026",
            "first_name": "Brady",
            "last_name": "Lane",
            "class_year": "S",
            "hometown": "Tampa, FL",
            "phone_number": "(555) 201-1008",
            "instagram_handle": "@bradylane",
            "first_event_date": date_at(-8),
            "interests": ["Finance", "Academics", "Entrepreneurship"],
            "stereotype": "Scholar",
            "lunch_stats": "1 lunch completed",
            "notes": "Analytical and thoughtful, needs social reps.",
            "assigned_officer": "officerliam",
        },
    ]

    pnm_ids: dict[str, int] = {}
    for pnm in pnm_seed:
        assigned_username = str(pnm["assigned_officer"])
        assigned_officer_id = user_ids.get(assigned_username)
        pnm_ids[str(pnm["pnm_code"])] = upsert_demo_pnm(
            pnm_code=str(pnm["pnm_code"]),
            first_name=str(pnm["first_name"]),
            last_name=str(pnm["last_name"]),
            class_year=str(pnm["class_year"]),
            hometown=str(pnm["hometown"]),
            phone_number=str(pnm["phone_number"]),
            instagram_handle=str(pnm["instagram_handle"]),
            first_event_date=str(pnm["first_event_date"]),
            interests=list(pnm["interests"]),
            stereotype=str(pnm["stereotype"]),
            lunch_stats=str(pnm["lunch_stats"]),
            notes=str(pnm["notes"]),
            created_by=head_id,
            assigned_officer_id=assigned_officer_id,
            assigned_by=head_id if assigned_officer_id else None,
        )

    ratings_seed = [
        {
            "pnm_code": "DMB01202026",
            "username": "officerjack",
            "create": make_scores(7, 8, 8, 7, 4),
            "update": make_scores(8, 8, 9, 8, 4),
            "create_comment": "Strong first read after roundtable conversations.",
            "update_comment": "Improved after two follow ups with chapter members.",
            "create_days": -19,
            "update_days": -7,
        },
        {
            "pnm_code": "DMB01202026",
            "username": "officerliam",
            "create": make_scores(8, 8, 8, 7, 4),
            "create_comment": "Reliable and engaged with multiple officers.",
            "create_days": -18,
        },
        {
            "pnm_code": "DMB01202026",
            "username": "memberalex",
            "create": make_scores(7, 7, 8, 7, 3),
            "create_comment": "Good fit and personable at dinner event.",
            "create_days": -16,
        },
        {
            "pnm_code": "DJC01222026",
            "username": "officerliam",
            "create": make_scores(6, 7, 8, 7, 3),
            "update": make_scores(7, 8, 8, 7, 4),
            "create_comment": "Solid start with high upside this cycle.",
            "update_comment": "Confidence increased after mentorship conversation.",
            "create_days": -18,
            "update_days": -6,
        },
        {
            "pnm_code": "DJC01222026",
            "username": "officernoah",
            "create": make_scores(7, 7, 7, 7, 3),
            "create_comment": "Good interview, still evaluating consistency.",
            "create_days": -14,
        },
        {
            "pnm_code": "DJC01222026",
            "username": "memberryan",
            "create": make_scores(6, 7, 7, 6, 3),
            "create_comment": "Positive conversations at social event.",
            "create_days": -12,
        },
        {
            "pnm_code": "DTR01242026",
            "username": "officernoah",
            "create": make_scores(7, 8, 7, 8, 3),
            "create_comment": "High maturity and disciplined approach overall.",
            "create_days": -15,
        },
        {
            "pnm_code": "DTR01242026",
            "username": "officerjack",
            "create": make_scores(6, 7, 7, 8, 3),
            "update": make_scores(7, 8, 8, 8, 3),
            "create_comment": "Strong character and dependable communication.",
            "update_comment": "Multiple brothers gave stronger feedback this week.",
            "create_days": -14,
            "update_days": -5,
        },
        {
            "pnm_code": "DSW01252026",
            "username": "officerjack",
            "create": make_scores(8, 8, 8, 7, 4),
            "create_comment": "High social confidence and easy chapter fit.",
            "create_days": -13,
        },
        {
            "pnm_code": "DSW01252026",
            "username": "memberalex",
            "create": make_scores(8, 7, 8, 7, 4),
            "create_comment": "Very comfortable in group settings and events.",
            "create_days": -11,
        },
        {
            "pnm_code": "DKM01272026",
            "username": "officerliam",
            "create": make_scores(6, 6, 7, 6, 3),
            "update": make_scores(7, 7, 8, 7, 4),
            "create_comment": "Personable with room to grow in consistency.",
            "update_comment": "Better communication and stronger attendance lately.",
            "create_days": -12,
            "update_days": -4,
        },
        {
            "pnm_code": "DAN01292026",
            "username": "officernoah",
            "create": make_scores(7, 6, 7, 6, 3),
            "create_comment": "Needs more touches but potential is clear.",
            "create_days": -10,
        },
        {
            "pnm_code": "DAN01292026",
            "username": "memberniko",
            "create": make_scores(6, 6, 7, 6, 3),
            "create_comment": "Good one on one interactions so far.",
            "create_days": -8,
        },
        {
            "pnm_code": "DRV01302026",
            "username": "officerjack",
            "create": make_scores(7, 8, 8, 8, 4),
            "create_comment": "Strong values fit and active participation.",
            "create_days": -9,
        },
        {
            "pnm_code": "DRV01302026",
            "username": "officerliam",
            "create": make_scores(7, 8, 7, 8, 4),
            "create_comment": "Consistent with chapter culture and expectations.",
            "create_days": -8,
        },
        {
            "pnm_code": "DPL02012026",
            "username": "officerliam",
            "create": make_scores(6, 7, 7, 7, 4),
            "create_comment": "Smart and thoughtful, still building comfort.",
            "create_days": -7,
        },
        {
            "pnm_code": "DPL02012026",
            "username": "memberryan",
            "create": make_scores(6, 7, 6, 7, 3),
            "create_comment": "Solid first impression and reliable follow through.",
            "create_days": -6,
        },
    ]

    for seed in ratings_seed:
        pnm_id = pnm_ids.get(str(seed["pnm_code"]))
        user_id = user_ids.get(str(seed["username"]))
        if not pnm_id or not user_id:
            continue

        create_scores = dict(seed["create"])
        final_scores = dict(seed.get("update") or create_scores)
        create_comment = str(seed["create_comment"])
        update_comment = str(seed.get("update_comment") or create_comment)
        create_stamp = iso_at(int(seed.get("create_days", -10)), 19, 0)
        update_stamp = iso_at(int(seed.get("update_days", -3)), 20, 0) if "update" in seed else create_stamp

        existing_rating = conn.execute(
            "SELECT id, created_at FROM ratings WHERE pnm_id = ? AND user_id = ?",
            (pnm_id, user_id),
        ).fetchone()
        if existing_rating:
            rating_id = int(existing_rating["id"])
            created_at = str(existing_rating["created_at"] or create_stamp)
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
                    created_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    final_scores["good_with_girls"],
                    final_scores["will_make_it"],
                    final_scores["personable"],
                    final_scores["alcohol_control"],
                    final_scores["instagram_marketability"],
                    final_scores["total_score"],
                    update_comment,
                    created_at,
                    update_stamp,
                    rating_id,
                ),
            )
        else:
            cursor = conn.execute(
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
                    pnm_id,
                    user_id,
                    final_scores["good_with_girls"],
                    final_scores["will_make_it"],
                    final_scores["personable"],
                    final_scores["alcohol_control"],
                    final_scores["instagram_marketability"],
                    final_scores["total_score"],
                    update_comment,
                    create_stamp,
                    update_stamp,
                ),
            )
            rating_id = int(cursor.lastrowid or 0)

        if rating_id <= 0:
            continue

        has_create_history = conn.execute(
            "SELECT 1 FROM rating_history WHERE rating_id = ? AND event_type = 'create' LIMIT 1",
            (rating_id,),
        ).fetchone()
        if not has_create_history:
            write_rating_history_event(
                conn,
                rating_id=rating_id,
                pnm_id=int(pnm_id),
                user_id=int(user_id),
                event_type="create",
                scores=create_scores,
                changed_at=create_stamp,
            )
        has_create_comment_event = conn.execute(
            "SELECT 1 FROM rating_comment_events WHERE rating_id = ? AND event_type = 'create' LIMIT 1",
            (rating_id,),
        ).fetchone()
        if not has_create_comment_event:
            write_rating_comment_event(
                conn,
                rating_id=rating_id,
                pnm_id=int(pnm_id),
                user_id=int(user_id),
                event_type="create",
                old_total=None,
                new_total=create_scores["total_score"],
                delta_total=0,
                comment=create_comment,
                changed_at=create_stamp,
            )

        if "update" in seed:
            has_update_history = conn.execute(
                "SELECT 1 FROM rating_history WHERE rating_id = ? AND event_type = 'update' LIMIT 1",
                (rating_id,),
            ).fetchone()
            if not has_update_history:
                write_rating_history_event(
                    conn,
                    rating_id=rating_id,
                    pnm_id=int(pnm_id),
                    user_id=int(user_id),
                    event_type="update",
                    scores=final_scores,
                    changed_at=update_stamp,
                )
            has_update_comment_event = conn.execute(
                """
                SELECT 1
                FROM rating_comment_events
                WHERE rating_id = ? AND event_type = 'update' AND changed_at = ?
                LIMIT 1
                """,
                (rating_id, update_stamp),
            ).fetchone()
            if not has_update_comment_event:
                write_rating_comment_event(
                    conn,
                    rating_id=rating_id,
                    pnm_id=int(pnm_id),
                    user_id=int(user_id),
                    event_type="update",
                    old_total=create_scores["total_score"],
                    new_total=final_scores["total_score"],
                    delta_total=final_scores["total_score"] - create_scores["total_score"],
                    comment=update_comment,
                    changed_at=update_stamp,
                )

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
                    rating_id,
                    int(pnm_id),
                    int(user_id),
                    create_scores["total_score"],
                    final_scores["total_score"],
                    final_scores["total_score"] - create_scores["total_score"],
                    json.dumps(create_scores, separators=(",", ":")),
                    json.dumps(final_scores, separators=(",", ":")),
                    update_comment,
                    update_stamp,
                ),
            )
        else:
            conn.execute("DELETE FROM rating_changes WHERE rating_id = ?", (rating_id,))

    lunch_seed = [
        ("DMB01202026", "officerjack", -5, "12:15", "13:00", "Student Union", "Kickoff lunch with two brothers."),
        ("DJC01222026", "officerliam", -4, "12:30", "13:10", "Campus Cafe", "Follow-up on interview questions."),
        ("DTR01242026", "officernoah", -3, "13:00", "13:45", "Library Patio", "Talked through leadership goals."),
        ("DSW01252026", "memberalex", -2, "12:00", "12:50", "Downtown Deli", "Strong social chemistry."),
        ("DKM01272026", "officerliam", -1, "12:20", "13:05", "Main Street Grill", "Good progress and better engagement."),
        ("DAN01292026", "officernoah", 1, "12:30", "13:20", "Brew House", "Scheduled to increase officer touchpoints."),
        ("DRV01302026", "officerjack", 2, "12:10", "12:55", "Campus Commons", "Discussing philanthropy involvement."),
        ("DPL02012026", "memberryan", 3, "12:45", "13:30", "North Dining", "Continuing relationship build."),
    ]
    lunch_user_ids: set[int] = set()
    lunch_pnm_ids: set[int] = set()
    for pnm_code, username, day_offset, start_time, end_time, location, notes in lunch_seed:
        pnm_id = pnm_ids.get(pnm_code)
        user_id = user_ids.get(username)
        if not pnm_id or not user_id:
            continue
        conn.execute(
            """
            INSERT OR IGNORE INTO lunches (
                pnm_id,
                user_id,
                lunch_date,
                start_time,
                end_time,
                location,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(pnm_id),
                int(user_id),
                date_at(int(day_offset)),
                str(start_time),
                str(end_time),
                str(location),
                str(notes),
                iso_at(int(day_offset), 17, 15),
            ),
        )
        lunch_user_ids.add(int(user_id))
        lunch_pnm_ids.add(int(pnm_id))

    rush_events_seed = [
        ("Chapter Kickoff", "official", -6, "18:30", "20:00", "Chapter House", "Opening rush kickoff event.", 1),
        ("Values Roundtable", "roundtable", -4, "19:00", "20:15", "Chapter House", "Roundtable with brothers and PNMs.", 1),
        ("Brotherhood Mixer", "mixer", -1, "20:00", "22:00", "Back Patio", "Informal social mixer.", 1),
        ("Philanthropy Planning", "philanthropy", 2, "18:00", "19:15", "Student Center", "Plan chapter service partnership.", 1),
        ("Interview Night", "interview", 4, "18:45", "21:00", "Chapter House", "Structured final-round interviews.", 1),
        ("Officer Debrief", "meeting", 5, "21:15", "22:00", "War Room", "Finalize bid strategy and assignments.", 0),
    ]
    for title, event_type, day_offset, start_time, end_time, location, details, is_official in rush_events_seed:
        event_date = date_at(int(day_offset))
        existing = conn.execute(
            "SELECT id, created_at FROM rush_events WHERE title = ? AND event_date = ? LIMIT 1",
            (title, event_date),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE rush_events
                SET
                    event_type = ?,
                    start_time = ?,
                    end_time = ?,
                    location = ?,
                    details = ?,
                    is_official = ?,
                    is_cancelled = 0,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    event_type,
                    start_time,
                    end_time,
                    location,
                    details,
                    int(is_official),
                    now_iso(),
                    int(existing["id"]),
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO rush_events (
                    title,
                    event_type,
                    event_date,
                    start_time,
                    end_time,
                    location,
                    details,
                    is_official,
                    is_cancelled,
                    created_by,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                """,
                (
                    title,
                    event_type,
                    event_date,
                    start_time,
                    end_time,
                    location,
                    details,
                    int(is_official),
                    int(head_id),
                    iso_at(int(day_offset), 16, 0),
                    now_iso(),
                ),
            )

    week_start, week_end = week_bounds_for(date.today())
    weekly_goals_seed = [
        (
            "Top PNMs fully rated",
            "Ensure each top-board PNM has at least three quality ratings this week.",
            "ratings_submitted",
            14,
            0,
            user_ids.get("officerjack"),
        ),
        (
            "Lunch outreach cadence",
            "Log lunch touchpoints across officer assignments.",
            "lunches_logged",
            8,
            0,
            None,
        ),
        (
            "Chapter rush coordination",
            "Track completion of prep tasks and messaging alignment.",
            "manual",
            6,
            3,
            user_ids.get("officerliam"),
        ),
        (
            "Event pipeline maintained",
            "Keep at least two upcoming official rush events scheduled.",
            "rush_events_created",
            2,
            0,
            user_ids.get("officernoah"),
        ),
    ]
    for title, description, metric_type, target_count, manual_progress, assigned_user_id in weekly_goals_seed:
        existing = conn.execute(
            """
            SELECT id
            FROM weekly_goals
            WHERE title = ?
              AND week_start = ?
              AND week_end = ?
              AND is_archived = 0
            LIMIT 1
            """,
            (title, week_start.isoformat(), week_end.isoformat()),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE weekly_goals
                SET
                    description = ?,
                    metric_type = ?,
                    target_count = ?,
                    manual_progress = ?,
                    assigned_user_id = ?,
                    created_by = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    description,
                    metric_type,
                    int(target_count),
                    int(manual_progress),
                    int(assigned_user_id) if assigned_user_id else None,
                    int(head_id),
                    now_iso(),
                    int(existing["id"]),
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO weekly_goals (
                    title,
                    description,
                    metric_type,
                    target_count,
                    manual_progress,
                    week_start,
                    week_end,
                    assigned_user_id,
                    created_by,
                    is_archived,
                    completed_at,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)
                """,
                (
                    title,
                    description,
                    metric_type,
                    int(target_count),
                    int(manual_progress),
                    week_start.isoformat(),
                    week_end.isoformat(),
                    int(assigned_user_id) if assigned_user_id else None,
                    int(head_id),
                    iso_at(-2, 14, 0),
                    now_iso(),
                ),
            )

    chat_seed = [
        {
            "sender": DEMO_HEAD_USERNAME,
            "message": "Command center sync tonight at 9pm. @officerjack lead PNM assignment updates.",
            "tags": ["Ops", "Assignment"],
            "mentions": ["officerjack"],
            "days": -2,
        },
        {
            "sender": "officerjack",
            "message": "Updated lunch coverage and added two new touchpoints for Ethan and Dylan.",
            "tags": ["Lunch", "Update"],
            "mentions": [],
            "days": -2,
        },
        {
            "sender": "officerliam",
            "message": "Need one more rating on Mason before final board review. @officernoah can you handle it?",
            "tags": ["Ratings", "Urgent"],
            "mentions": ["officernoah"],
            "days": -1,
        },
        {
            "sender": "officernoah",
            "message": "Handled. Added updated feedback and bumped confidence after interview night.",
            "tags": ["Ratings", "Done"],
            "mentions": [],
            "days": -1,
        },
    ]
    for seed in chat_seed:
        sender_id = user_ids.get(str(seed["sender"]))
        if not sender_id:
            continue
        message = str(seed["message"]).strip()
        created_at = iso_at(int(seed["days"]), 21, 0)
        existing = conn.execute(
            "SELECT id FROM officer_chat_messages WHERE sender_id = ? AND message = ? LIMIT 1",
            (int(sender_id), message),
        ).fetchone()
        if existing:
            message_id = int(existing["id"])
        else:
            cursor = conn.execute(
                """
                INSERT INTO officer_chat_messages (sender_id, message, tags, created_at, edited_at)
                VALUES (?, ?, ?, ?, NULL)
                """,
                (
                    int(sender_id),
                    message,
                    ",".join([normalize_chat_tag(str(tag)) for tag in list(seed["tags"])]),
                    created_at,
                ),
            )
            message_id = int(cursor.lastrowid or 0)
        if message_id <= 0:
            continue

        for raw_tag in list(seed["tags"]):
            tag = normalize_chat_tag(str(raw_tag))
            conn.execute(
                "INSERT OR IGNORE INTO officer_chat_tags (message_id, tag, created_at) VALUES (?, ?, ?)",
                (message_id, tag, created_at),
            )

        for mention_username in list(seed["mentions"]):
            mention_id = user_ids.get(str(mention_username))
            if not mention_id:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO officer_chat_mentions (message_id, user_id, created_at) VALUES (?, ?, ?)",
                (message_id, int(mention_id), created_at),
            )
            if int(mention_id) == int(sender_id):
                continue
            title = f"Mentioned by {seed['sender']}"
            exists_notif = conn.execute(
                """
                SELECT id
                FROM notifications
                WHERE user_id = ? AND notif_type = 'chat_mention' AND title = ? AND body = ?
                LIMIT 1
                """,
                (int(mention_id), title, message[:220]),
            ).fetchone()
            if not exists_notif:
                create_notification(
                    conn,
                    user_id=int(mention_id),
                    notif_type="chat_mention",
                    title=title,
                    body=message[:220],
                    link_path="/calendar",
                )

    upsert_contact_download_records(
        conn,
        user_id=int(head_id),
        pnm_ids=[pnm_ids["DMB01202026"], pnm_ids["DTR01242026"]],
        downloaded_at=iso_at(-1, 22, 0),
    )

    for user_id in set(user_ids.values()):
        if user_id <= 0:
            continue
        recalc_member_rating_stats(conn, user_id)
        recalc_member_lunch_stats(conn, user_id)
    for pnm_id in set(pnm_ids.values()):
        if pnm_id <= 0:
            continue
        recalc_pnm_rating_stats(conn, pnm_id)
        recalc_pnm_lunch_stats(conn, pnm_id)
    evaluate_weekly_goal_completions(conn)


def bootstrap_platform_and_tenants() -> None:
    PLATFORM_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    TENANTS_DB_DIR.mkdir(parents=True, exist_ok=True)
    TENANT_UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    with platform_db_session() as conn:
        setup_platform_schema(conn)
        ensure_platform_schema_upgrades(conn)
        ensure_platform_admin_seed(conn)
        ensure_default_tenant_record(conn)
        ensure_demo_tenant_record(conn)
        tenant_rows = conn.execute("SELECT * FROM tenants WHERE is_active = 1").fetchall()

    for row in tenant_rows:
        if row["slug"] == DEFAULT_TENANT_SLUG:
            seed_access = HEAD_SEED_ACCESS_CODE
        elif is_demo_tenant_slug(row["slug"]):
            seed_access = DEMO_HEAD_ACCESS_CODE
        else:
            seed_access = None
        initialize_tenant_datastore(row, seed_access_code=seed_access)
        if is_demo_tenant_slug(row["slug"]):
            ctx = tenant_context_from_row(row)
            with db_session(ctx.db_path) as tenant_conn:
                ensure_demo_seed_dataset(tenant_conn)


def user_payload(row: sqlite3.Row, viewer_role: str, viewer_id: int) -> dict[str, Any]:
    can_view_rating_stats = viewer_role in {ROLE_HEAD, ROLE_RUSH_OFFICER} or row["id"] == viewer_id
    keys = set(row.keys())
    onboarding_mode = (
        str(row["onboarding_mode"]).strip().lower()
        if "onboarding_mode" in keys and row["onboarding_mode"] is not None
        else ONBOARDING_DEFAULT_MODE
    )
    if onboarding_mode not in ONBOARDING_TUTORIAL_MODES:
        onboarding_mode = ONBOARDING_DEFAULT_MODE
    onboarding_completed_at = row["onboarding_completed_at"] if "onboarding_completed_at" in keys else None
    onboarding_version = int(row["onboarding_version"]) if "onboarding_version" in keys and row["onboarding_version"] is not None else 0
    city = normalize_city_value(row["city"]) if "city" in keys else ""
    state_code = normalize_state_code(row["state_code"]) if "state_code" in keys else ""
    payload = {
        "user_id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "emoji": row["emoji"] if row["role"] == ROLE_RUSH_OFFICER else None,
        "stereotype": row["stereotype"],
        "interests": decode_interests(row["interests"]),
        "city": city,
        "state_code": state_code,
        "is_approved": bool(row["is_approved"]),
        "total_lunches": int(row["total_lunches"]),
        "lunches_per_week": round(float(row["lunches_per_week"]), 2),
        "onboarding": {
            "mode": onboarding_mode,
            "completed_at": onboarding_completed_at,
            "version": onboarding_version,
            "required": onboarding_completed_at is None or onboarding_version < ONBOARDING_TUTORIAL_VERSION,
        },
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
    assigned_officers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    days_since_event = (date.today() - date.fromisoformat(row["first_event_date"])).days
    keys = set(row.keys())
    hometown_city, _ = parse_hometown_city_state(row["hometown"])
    hometown_state_code = pnm_state_code_for_row(row)
    assignment_status = (
        str(row["assignment_status"]).strip().lower()
        if "assignment_status" in keys and row["assignment_status"] is not None
        else ("assigned" if row["assigned_officer_id"] else "unassigned")
    )
    if assignment_status not in ASSIGNMENT_STATUSES:
        assignment_status = "assigned" if row["assigned_officer_id"] else "unassigned"
    assignment_priority = int(row["assignment_priority"]) if "assignment_priority" in keys and row["assignment_priority"] is not None else max(1, min(ASSIGNMENT_MAX_PRIORITY, ASSIGNMENT_DEFAULT_PRIORITY))
    assignment_priority = max(1, min(ASSIGNMENT_MAX_PRIORITY, assignment_priority))
    assignment_due_date = row["assignment_due_date"] if "assignment_due_date" in keys else None
    funnel_stage = str(row["funnel_stage"]).strip().lower() if "funnel_stage" in keys and row["funnel_stage"] is not None else "sourced"
    if funnel_stage not in PNM_FUNNEL_STAGES:
        funnel_stage = "sourced"
    package_group_id = normalize_package_group_id(row["package_group_id"]) if "package_group_id" in keys else ""
    assignment_team = merge_assigned_officers_for_pnm_row(row, assigned_officers)
    return {
        "pnm_id": row["id"],
        "pnm_code": row["pnm_code"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "class_year": row["class_year"],
        "hometown": row["hometown"],
        "hometown_city": hometown_city,
        "hometown_state_code": hometown_state_code,
        "phone_number": row["phone_number"] if "phone_number" in row.keys() else "",
        "instagram_handle": row["instagram_handle"],
        "first_event_date": row["first_event_date"],
        "days_since_first_event": days_since_event,
        "interests": decode_interests(row["interests"]),
        "stereotype": row["stereotype"],
        "photo_url": resolve_pnm_photo_url(row["photo_path"], row["instagram_handle"]),
        "photo_uploaded_at": row["photo_uploaded_at"],
        "lunch_stats": row["lunch_stats"],
        "notes": row["notes"] if "notes" in row.keys() else "",
        "total_lunches": int(row["total_lunches"]),
        "rating_count": int(row["rating_count"]),
        "avg_good_with_girls": round(float(row["avg_good_with_girls"]), 2),
        "avg_will_make_it": round(float(row["avg_will_make_it"]), 2),
        "avg_personable": round(float(row["avg_personable"]), 2),
        "avg_alcohol_control": round(float(row["avg_alcohol_control"]), 2),
        "avg_instagram_marketability": round(float(row["avg_instagram_marketability"]), 2),
        "weighted_total": round(float(row["weighted_total"]), 2),
        "assigned_officer_id": row["assigned_officer_id"] if "assigned_officer_id" in row.keys() else None,
        "assigned_by": row["assigned_by"] if "assigned_by" in row.keys() else None,
        "assigned_at": row["assigned_at"] if "assigned_at" in row.keys() else None,
        "assignment_status": assignment_status,
        "assignment_status_label": ASSIGNMENT_STATUS_LABELS.get(assignment_status, assignment_status.replace("_", " ").title()),
        "assignment_priority": assignment_priority,
        "assignment_due_date": assignment_due_date,
        "assignment_due_state": assignment_due_state(assignment_status, assignment_due_date),
        "assignment_notes": row["assignment_notes"] if "assignment_notes" in keys and row["assignment_notes"] is not None else "",
        "assignment_updated_at": row["assignment_updated_at"] if "assignment_updated_at" in keys else None,
        "assigned_officer": assigned_officer,
        "assigned_officers": assignment_team,
        "package_group_id": package_group_id or None,
        "package_group_label": package_group_label(package_group_id),
        "funnel_stage": funnel_stage,
        "funnel_stage_reason": row["funnel_stage_reason"] if "funnel_stage_reason" in keys and row["funnel_stage_reason"] is not None else "",
        "funnel_stage_updated_at": row["funnel_stage_updated_at"] if "funnel_stage_updated_at" in keys else None,
        "funnel_stage_updated_by": row["funnel_stage_updated_by"] if "funnel_stage_updated_by" in keys else None,
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
            SELECT u.*, s.last_seen_at, s.created_at AS session_created_at, s.max_idle_seconds
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
        idle_limit = normalized_idle_ttl_seconds(row["max_idle_seconds"], SESSION_TTL_SECONDS)
        if (datetime.now(timezone.utc) - last_seen_dt).total_seconds() > idle_limit:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.")

        conn.execute("UPDATE sessions SET last_seen_at = ? WHERE token = ?", (now_iso(), token))
        return row


def current_user_optional(request: Request) -> sqlite3.Row | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None

    with db_session() as conn:
        row = conn.execute(
            """
            SELECT u.*, s.last_seen_at, s.created_at AS session_created_at, s.max_idle_seconds
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()
        if not row:
            return None

        try:
            last_seen_dt = datetime.fromisoformat(row["last_seen_at"])
        except (TypeError, ValueError):
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None
        idle_limit = normalized_idle_ttl_seconds(row["max_idle_seconds"], SESSION_TTL_SECONDS)
        if (datetime.now(timezone.utc) - last_seen_dt).total_seconds() > idle_limit:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None

        conn.execute("UPDATE sessions SET last_seen_at = ? WHERE token = ?", (now_iso(), token))
        return row


def request_has_active_session(request: Request) -> bool:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return False

    with db_session() as conn:
        row = conn.execute("SELECT last_seen_at, max_idle_seconds FROM sessions WHERE token = ?", (token,)).fetchone()
        if not row:
            return False

        try:
            last_seen_dt = datetime.fromisoformat(row["last_seen_at"])
        except (TypeError, ValueError):
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return False
        idle_limit = normalized_idle_ttl_seconds(row["max_idle_seconds"], SESSION_TTL_SECONDS)
        if (datetime.now(timezone.utc) - last_seen_dt).total_seconds() > idle_limit:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return False
    return True


def request_has_active_platform_session(request: Request) -> bool:
    token = request.cookies.get(PLATFORM_SESSION_COOKIE)
    if not token:
        return False

    with platform_db_session() as conn:
        row = conn.execute("SELECT last_seen_at, max_idle_seconds FROM platform_sessions WHERE token = ?", (token,)).fetchone()
        if not row:
            return False

        try:
            last_seen_dt = datetime.fromisoformat(row["last_seen_at"])
        except (TypeError, ValueError):
            conn.execute("DELETE FROM platform_sessions WHERE token = ?", (token,))
            return False
        idle_limit = normalized_idle_ttl_seconds(row["max_idle_seconds"], PLATFORM_SESSION_TTL_SECONDS)
        if (datetime.now(timezone.utc) - last_seen_dt).total_seconds() > idle_limit:
            conn.execute("DELETE FROM platform_sessions WHERE token = ?", (token,))
            return False
    return True


def request_session_role(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None

    with db_session() as conn:
        row = conn.execute(
            """
            SELECT u.role, s.last_seen_at, s.max_idle_seconds
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()
        if not row:
            return None

        try:
            last_seen_dt = datetime.fromisoformat(row["last_seen_at"])
        except (TypeError, ValueError):
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None
        idle_limit = normalized_idle_ttl_seconds(row["max_idle_seconds"], SESSION_TTL_SECONDS)
        if (datetime.now(timezone.utc) - last_seen_dt).total_seconds() > idle_limit:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None
    return str(row["role"])


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
    city: str | None = Field(default=None, max_length=80)
    state: str | None = Field(default=None, max_length=64)

    @model_validator(mode="before")
    @classmethod
    def accept_password_alias(cls, data: Any) -> Any:
        if isinstance(data, dict) and "access_code" not in data and "password" in data:
            merged = dict(data)
            merged["access_code"] = merged.get("password")
            return merged
        return data

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

    @field_validator("city")
    @classmethod
    def normalize_optional_city(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_city_value(value)

    @field_validator("state")
    @classmethod
    def normalize_optional_state(cls, value: str | None) -> str | None:
        if value is None:
            return None
        token = value.strip()
        if not token:
            return ""
        normalized = normalize_state_code(token)
        if not normalized:
            raise ValueError("State must be a valid US state name or 2-letter code.")
        return normalized


class MemberRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    access_code: str = Field(..., min_length=8, max_length=128)
    city: str | None = Field(default=None, max_length=80)
    state: str | None = Field(default=None, max_length=64)

    @model_validator(mode="before")
    @classmethod
    def accept_password_alias(cls, data: Any) -> Any:
        if isinstance(data, dict) and "access_code" not in data and "password" in data:
            merged = dict(data)
            merged["access_code"] = merged.get("password")
            return merged
        return data

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        username = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]{3,64}", username):
            raise ValueError("Username may only include letters, numbers, dots, underscores, and hyphens.")
        return username

    @field_validator("city")
    @classmethod
    def normalize_optional_city(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_city_value(value)

    @field_validator("state")
    @classmethod
    def normalize_optional_state(cls, value: str | None) -> str | None:
        if value is None:
            return None
        token = value.strip()
        if not token:
            return ""
        normalized = normalize_state_code(token)
        if not normalized:
            raise ValueError("State must be a valid US state name or 2-letter code.")
        return normalized


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=120)
    access_code: str = Field(..., min_length=8, max_length=128)
    remember_me: bool = False

    @model_validator(mode="before")
    @classmethod
    def accept_password_alias(cls, data: Any) -> Any:
        if isinstance(data, dict) and "access_code" not in data and "password" in data:
            merged = dict(data)
            merged["access_code"] = merged.get("password")
            return merged
        return data


class TutorialCompleteRequest(BaseModel):
    mode: str = Field(default=ONBOARDING_DEFAULT_MODE, min_length=1, max_length=24)
    version: int = Field(default=ONBOARDING_TUTORIAL_VERSION, ge=1, le=25)

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ONBOARDING_TUTORIAL_MODES:
            raise ValueError("Invalid tutorial mode.")
        return normalized


class SelfUpdateRequest(BaseModel):
    stereotype: str | None = Field(default=None, min_length=1, max_length=48)
    interests: str | list[str] | None = None
    emoji: str | None = None
    city: str | None = Field(default=None, max_length=80)
    state: str | None = Field(default=None, max_length=64)

    @field_validator("city")
    @classmethod
    def normalize_optional_city(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_city_value(value)

    @field_validator("state")
    @classmethod
    def normalize_optional_state(cls, value: str | None) -> str | None:
        if value is None:
            return None
        token = value.strip()
        if not token:
            return ""
        normalized = normalize_state_code(token)
        if not normalized:
            raise ValueError("State must be a valid US state name or 2-letter code.")
        return normalized


class UserLocationUpdateRequest(BaseModel):
    city: str | None = Field(default=None, max_length=80)
    state: str | None = Field(default=None, max_length=64)

    @field_validator("city")
    @classmethod
    def normalize_optional_city(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_city_value(value)

    @field_validator("state")
    @classmethod
    def normalize_optional_state(cls, value: str | None) -> str | None:
        if value is None:
            return None
        token = value.strip()
        if not token:
            return ""
        normalized = normalize_state_code(token)
        if not normalized:
            raise ValueError("State must be a valid US state name or 2-letter code.")
        return normalized


class PNMCreateRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=48)
    last_name: str = Field(..., min_length=1, max_length=48)
    class_year: str
    hometown: str = Field(..., min_length=1, max_length=80)
    state: str | None = Field(default=None, max_length=64)
    phone_number: str = Field(default="", max_length=32)
    instagram_handle: str = Field(..., min_length=1, max_length=80)
    first_event_date: str
    interests: str | list[str]
    stereotype: str = Field(..., min_length=1, max_length=48)
    lunch_stats: str = Field(default="", max_length=256)
    notes: str = Field(default="", max_length=2000)
    auto_photo_from_instagram: bool = True

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

    @field_validator("state")
    @classmethod
    def normalize_optional_state(cls, value: str | None) -> str | None:
        if value is None:
            return None
        token = value.strip()
        if not token:
            return ""
        normalized = normalize_state_code(token)
        if not normalized:
            raise ValueError("State must be a valid US state name or 2-letter code.")
        return normalized


class PNMUpdateRequest(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=48)
    last_name: str | None = Field(default=None, min_length=1, max_length=48)
    class_year: str | None = None
    hometown: str | None = Field(default=None, min_length=1, max_length=80)
    state: str | None = Field(default=None, max_length=64)
    phone_number: str | None = Field(default=None, max_length=32)
    instagram_handle: str | None = Field(default=None, min_length=1, max_length=80)
    first_event_date: str | None = None
    interests: str | list[str] | None = None
    stereotype: str | None = Field(default=None, min_length=1, max_length=48)
    lunch_stats: str | None = Field(default=None, max_length=256)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("class_year")
    @classmethod
    def validate_optional_class_year(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if normalized not in {"F", "S", "J"}:
            raise ValueError("Class year must be F, S, or J.")
        return normalized

    @field_validator("first_event_date")
    @classmethod
    def validate_optional_first_event_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return verify_iso_date(value, "First event date")

    @field_validator("state")
    @classmethod
    def normalize_optional_state(cls, value: str | None) -> str | None:
        if value is None:
            return None
        token = value.strip()
        if not token:
            return ""
        normalized = normalize_state_code(token)
        if not normalized:
            raise ValueError("State must be a valid US state name or 2-letter code.")
        return normalized


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
    start_time: str | None = None
    end_time: str | None = None
    location: str = Field(default="", max_length=120)
    notes: str = Field(default="", max_length=500)

    @field_validator("lunch_date")
    @classmethod
    def validate_lunch_date(cls, value: str) -> str:
        return verify_iso_date(value, "Lunch date")

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time_value(cls, value: str | None) -> str | None:
        if value is None:
            return None
        token = value.strip()
        if not token:
            return None
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", token):
            raise ValueError("Time must use HH:MM in 24-hour format.")
        return token


class RushEventCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=120)
    event_type: str = Field(default="official", min_length=3, max_length=32)
    event_date: str
    start_time: str | None = None
    end_time: str | None = None
    location: str = Field(default="", max_length=140)
    details: str = Field(default="", max_length=1200)
    is_official: bool = True

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        return normalize_rush_event_type(value)

    @field_validator("event_date")
    @classmethod
    def validate_event_date(cls, value: str) -> str:
        return verify_iso_date(value, "Event date")

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time_values(cls, value: str | None) -> str | None:
        return LunchCreateRequest.validate_time_value(value)


class RushEventUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=120)
    event_type: str | None = Field(default=None, min_length=3, max_length=32)
    event_date: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    location: str | None = Field(default=None, max_length=140)
    details: str | None = Field(default=None, max_length=1200)
    is_official: bool | None = None
    is_cancelled: bool | None = None

    @field_validator("event_type")
    @classmethod
    def validate_optional_event_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_rush_event_type(value)

    @field_validator("event_date")
    @classmethod
    def validate_optional_event_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return verify_iso_date(value, "Event date")

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_optional_time_values(cls, value: str | None) -> str | None:
        return LunchCreateRequest.validate_time_value(value)


class WeeklyGoalCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=120)
    description: str = Field(default="", max_length=800)
    metric_type: str = Field(default=DEFAULT_WEEKLY_GOAL_METRIC, min_length=3, max_length=32)
    target_count: int = Field(default=1, ge=1, le=1000)
    week_start: str | None = None
    week_end: str | None = None
    assigned_user_id: int | None = None

    @field_validator("metric_type")
    @classmethod
    def validate_metric_type(cls, value: str) -> str:
        return normalize_weekly_goal_metric(value)


class WeeklyGoalUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=800)
    metric_type: str | None = Field(default=None, min_length=3, max_length=32)
    target_count: int | None = Field(default=None, ge=1, le=1000)
    week_start: str | None = None
    week_end: str | None = None
    assigned_user_id: int | None = None
    is_archived: bool | None = None
    complete_now: bool | None = None

    @field_validator("metric_type")
    @classmethod
    def validate_optional_metric_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_weekly_goal_metric(value)


class WeeklyGoalProgressRequest(BaseModel):
    delta: int = Field(default=1, ge=1, le=1000)
    note: str = Field(default="", max_length=220)


class OfficerChatMessageCreateRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2200)
    tags: str | list[str] | None = None


class AssignOfficerRequest(BaseModel):
    officer_user_id: int | None = None


class PnmAssigneeCreateRequest(BaseModel):
    officer_user_id: int = Field(..., ge=1)
    include_package: bool = False
    notify_officer: bool = True


class PnmAssignmentUpdateRequest(BaseModel):
    officer_user_id: int | None = None
    assignment_status: str | None = Field(default=None, min_length=3, max_length=20)
    assignment_priority: int | None = Field(default=None, ge=1, le=ASSIGNMENT_MAX_PRIORITY)
    assignment_due_date: str | None = None
    assignment_notes: str | None = Field(default=None, max_length=1600)
    notify_officer: bool = True

    @field_validator("assignment_status")
    @classmethod
    def validate_optional_assignment_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_assignment_status(value)

    @field_validator("assignment_due_date")
    @classmethod
    def validate_optional_assignment_due_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        token = value.strip()
        if not token:
            return None
        return verify_iso_date(token, "Assignment due date")

    @field_validator("assignment_notes")
    @classmethod
    def normalize_optional_assignment_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class PnmPackageLinkRequest(BaseModel):
    pnm_ids: list[int] = Field(..., min_length=2, max_length=48)
    sync_assignment: bool = True

    @field_validator("pnm_ids")
    @classmethod
    def validate_pnm_ids(cls, value: list[int]) -> list[int]:
        unique_ids: list[int] = []
        seen: set[int] = set()
        for raw_id in value:
            pnm_id = int(raw_id)
            if pnm_id <= 0:
                raise ValueError("PNM IDs must be positive integers.")
            if pnm_id in seen:
                continue
            seen.add(pnm_id)
            unique_ids.append(pnm_id)
        if len(unique_ids) < 2:
            raise ValueError("Select at least two unique PNMs for a package deal.")
        return unique_ids


class PnmFunnelStageUpdateRequest(BaseModel):
    stage: str = Field(..., min_length=3, max_length=24)
    reason: str = Field(default="", max_length=320)

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, value: str) -> str:
        return normalize_funnel_stage(value)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return value.strip()


class EngagementEventCreateRequest(BaseModel):
    event_type: str = Field(default="follow_up", min_length=3, max_length=32)
    status: str = Field(default="planned", min_length=3, max_length=16)
    title: str = Field(..., min_length=3, max_length=160)
    event_date: str
    start_time: str | None = None
    end_time: str | None = None
    location: str = Field(default="", max_length=180)
    details: str = Field(default="", max_length=2400)
    pnm_id: int | None = None
    owner_user_id: int | None = None

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        return normalize_engagement_event_type(value)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return normalize_engagement_event_status(value)

    @field_validator("event_date")
    @classmethod
    def validate_event_date(cls, value: str) -> str:
        return verify_iso_date(value, "Event date")

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_times(cls, value: str | None) -> str | None:
        return LunchCreateRequest.validate_time_value(value)

    @model_validator(mode="after")
    def validate_time_order(self) -> "EngagementEventCreateRequest":
        if self.end_time and not self.start_time:
            raise ValueError("End time requires a start time.")
        if self.start_time and self.end_time:
            start_value = parse_clock_value(self.start_time)
            end_value = parse_clock_value(self.end_time)
            if start_value and end_value and (end_value[0] * 60 + end_value[1]) <= (start_value[0] * 60 + start_value[1]):
                raise ValueError("End time must be after start time.")
        return self


class EngagementEventUpdateRequest(BaseModel):
    event_type: str | None = Field(default=None, min_length=3, max_length=32)
    status: str | None = Field(default=None, min_length=3, max_length=16)
    title: str | None = Field(default=None, min_length=3, max_length=160)
    event_date: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    location: str | None = Field(default=None, max_length=180)
    details: str | None = Field(default=None, max_length=2400)
    pnm_id: int | None = None
    owner_user_id: int | None = None

    @field_validator("event_type")
    @classmethod
    def validate_optional_event_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_engagement_event_type(value)

    @field_validator("status")
    @classmethod
    def validate_optional_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_engagement_event_status(value)

    @field_validator("event_date")
    @classmethod
    def validate_optional_event_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return verify_iso_date(value, "Event date")

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_optional_times(cls, value: str | None) -> str | None:
        return LunchCreateRequest.validate_time_value(value)


class NotificationDigestBroadcastRequest(BaseModel):
    period: str = Field(default="daily", min_length=5, max_length=10)
    recipients: str = Field(default="officers", min_length=3, max_length=24)
    include_read: bool = False
    max_items: int = Field(default=20, ge=5, le=120)

    @field_validator("period")
    @classmethod
    def validate_period(cls, value: str) -> str:
        return normalize_digest_period(value)

    @field_validator("recipients")
    @classmethod
    def normalize_recipients(cls, value: str) -> str:
        token = value.strip().lower()
        if token not in {"officers", "all_approved"}:
            raise ValueError("Recipients must be officers or all_approved.")
        return token


class PromoteHeadRequest(BaseModel):
    demote_existing_heads: bool = False
    demoted_head_emoji: str | None = Field(default=None, max_length=8)

    @field_validator("demoted_head_emoji")
    @classmethod
    def normalize_optional_demoted_head_emoji(cls, value: str | None) -> str | None:
        if value is None:
            return None
        token = value.strip()
        return token or None


class SeasonResetRequest(BaseModel):
    confirm_phrase: str = Field(..., min_length=4, max_length=120)
    archive_label: str | None = Field(default=None, max_length=120)
    head_chair_confirmation: bool = False

    @field_validator("confirm_phrase")
    @classmethod
    def normalize_confirm_phrase(cls, value: str) -> str:
        return value.strip()

    @field_validator("archive_label")
    @classmethod
    def normalize_archive_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        token = value.strip()
        return token or None


class PlatformLoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=120)
    access_code: str = Field(..., min_length=8, max_length=128)
    remember_me: bool = False

    @model_validator(mode="before")
    @classmethod
    def accept_password_alias(cls, data: Any) -> Any:
        if isinstance(data, dict) and "access_code" not in data and "password" in data:
            merged = dict(data)
            merged["access_code"] = merged.get("password")
            return merged
        return data


class TenantRatingCriterionInput(BaseModel):
    field: str
    label: str | None = Field(default=None, max_length=60)
    short_label: str | None = Field(default=None, max_length=20)
    max: int | None = Field(default=None, ge=1, le=10)


class TenantCreateRequest(BaseModel):
    slug: str
    display_name: str = Field(..., min_length=3, max_length=120)
    chapter_name: str = Field(..., min_length=2, max_length=24)
    org_type: str | None = Field(default=None, max_length=40)
    setup_tagline: str | None = Field(default=None, max_length=180)
    head_seed_username: str = Field(..., min_length=3, max_length=120)
    head_seed_first_name: str = Field(..., min_length=1, max_length=48)
    head_seed_last_name: str = Field(..., min_length=1, max_length=48)
    head_seed_pledge_class: str = Field(..., min_length=1, max_length=24)
    head_seed_access_code: str = Field(..., min_length=8, max_length=128)
    theme_primary: str | None = None
    theme_secondary: str | None = None
    theme_tertiary: str | None = None
    officer_weight: float | None = Field(default=None, gt=0, le=1)
    rusher_weight: float | None = Field(default=None, gt=0, le=1)
    default_interest_tags: str | list[str] | None = None
    default_stereotype_tags: str | list[str] | None = None
    rating_criteria: list[TenantRatingCriterionInput] | None = None

    @model_validator(mode="before")
    @classmethod
    def accept_password_alias(cls, data: Any) -> Any:
        if isinstance(data, dict) and "head_seed_access_code" not in data and "head_seed_password" in data:
            merged = dict(data)
            merged["head_seed_access_code"] = merged.get("head_seed_password")
            return merged
        return data


class TenantUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=3, max_length=120)
    chapter_name: str | None = Field(default=None, min_length=2, max_length=24)
    org_type: str | None = Field(default=None, max_length=40)
    setup_tagline: str | None = Field(default=None, max_length=180)
    theme_primary: str | None = None
    theme_secondary: str | None = None
    theme_tertiary: str | None = None
    officer_weight: float | None = Field(default=None, gt=0, le=1)
    rusher_weight: float | None = Field(default=None, gt=0, le=1)
    default_interest_tags: str | list[str] | None = None
    default_stereotype_tags: str | list[str] | None = None
    rating_criteria: list[TenantRatingCriterionInput] | None = None


@app.on_event("startup")
def startup() -> None:
    enforce_persistent_storage_if_required()
    enforce_host_configuration_if_required()
    print(
        "[startup] storage config: "
        f"DATA_ROOT={DATA_ROOT} DB_PATH={DB_PATH} PLATFORM_DB_PATH={PLATFORM_DB_PATH} "
        f"TENANTS_DB_DIR={TENANTS_DB_DIR} UPLOADS_DIR={UPLOADS_DIR}"
    )
    for warning in collect_storage_warnings():
        print(f"[startup] warning: {warning}")
    bootstrap_platform_and_tenants()
    default_row = fetch_tenant_row(DEFAULT_TENANT_SLUG)
    if default_row:
        tenant = tenant_context_from_row(default_row)
        print(f"[startup] default tenant db path: slug={tenant.slug} db_path={tenant.db_path}")
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
        legacy_redirect = legacy_view_redirect_url(tenant, request.query_params.get("view"))
        if legacy_redirect:
            return RedirectResponse(url=legacy_redirect, status_code=307)
        return RedirectResponse(url=f"/{tenant.slug}/{DEFAULT_DESKTOP_ROUTE}", status_code=307)

    tenants = [tenant_context_from_row(row) for row in list_tenants_rows()]
    return templates.TemplateResponse(
        "landing.html",
        {
            "request": request,
            "tenants": tenants,
            "tenant_count": len(tenants),
        },
    )


@app.get("/organizations", response_class=HTMLResponse)
async def organizations_page(request: Request) -> HTMLResponse:
    tenants = [tenant_context_from_row(row) for row in list_tenants_rows()]
    return templates.TemplateResponse(
        "platform_home.html",
        {
            "request": request,
            "tenants": tenants,
            "default_slug": DEFAULT_TENANT_SLUG,
        },
    )


@app.get("/features", response_class=HTMLResponse)
async def features_page(request: Request) -> HTMLResponse:
    tenants = [tenant_context_from_row(row) for row in list_tenants_rows()]
    return templates.TemplateResponse(
        "landing_features.html",
        {
            "request": request,
            "tenants": tenants,
            "tenant_count": len(tenants),
        },
    )


@app.get("/faq", response_class=HTMLResponse)
async def faq_page(request: Request) -> HTMLResponse:
    tenants = [tenant_context_from_row(row) for row in list_tenants_rows()]
    return templates.TemplateResponse(
        "landing_faq.html",
        {
            "request": request,
            "tenants": tenants,
            "tenant_count": len(tenants),
        },
    )


def resolved_demo_tenant() -> TenantContext | None:
    if not DEMO_ENABLED:
        return None
    row = fetch_tenant_row(demo_tenant_slug())
    if not row:
        return None
    return tenant_context_from_row(row)


def ensure_demo_head_session(request: Request, response: Response, tenant: TenantContext) -> None:
    head_username = DEMO_HEAD_USERNAME.strip()
    if not head_username:
        return

    existing_token = request.cookies.get(SESSION_COOKIE)
    issued_token: str | None = None
    max_idle_seconds = user_session_idle_seconds(True)
    now = now_iso()

    def _valid_idle_window(last_seen_raw: Any, idle_seconds_raw: Any) -> bool:
        try:
            last_seen_dt = datetime.fromisoformat(str(last_seen_raw))
        except (TypeError, ValueError):
            return False
        idle_limit = normalized_idle_ttl_seconds(idle_seconds_raw, SESSION_TTL_SECONDS)
        return (datetime.now(timezone.utc) - last_seen_dt).total_seconds() <= idle_limit

    with db_session(tenant.db_path) as conn:
        head_user = conn.execute(
            "SELECT id, role, is_approved FROM users WHERE username = ?",
            (head_username,),
        ).fetchone()
        if not head_user or head_user["role"] != ROLE_HEAD:
            return

        if not bool(head_user["is_approved"]):
            conn.execute(
                """
                UPDATE users
                SET is_approved = 1, approved_at = COALESCE(approved_at, ?), updated_at = ?
                WHERE id = ?
                """,
                (now, now, int(head_user["id"])),
            )

        if existing_token:
            session_row = conn.execute(
                "SELECT user_id, last_seen_at, max_idle_seconds FROM sessions WHERE token = ?",
                (existing_token,),
            ).fetchone()
            if session_row and int(session_row["user_id"]) == int(head_user["id"]):
                if _valid_idle_window(session_row["last_seen_at"], session_row["max_idle_seconds"]):
                    issued_token = existing_token
                    max_idle_seconds = normalized_idle_ttl_seconds(session_row["max_idle_seconds"], SESSION_TTL_SECONDS)
                else:
                    conn.execute("DELETE FROM sessions WHERE token = ?", (existing_token,))

        if not issued_token:
            latest_row = conn.execute(
                """
                SELECT token, last_seen_at, max_idle_seconds
                FROM sessions
                WHERE user_id = ?
                ORDER BY last_seen_at DESC
                LIMIT 1
                """,
                (int(head_user["id"]),),
            ).fetchone()
            if latest_row and _valid_idle_window(latest_row["last_seen_at"], latest_row["max_idle_seconds"]):
                issued_token = str(latest_row["token"])
                max_idle_seconds = normalized_idle_ttl_seconds(latest_row["max_idle_seconds"], SESSION_TTL_SECONDS)
            elif latest_row:
                conn.execute("DELETE FROM sessions WHERE token = ?", (latest_row["token"],))

        if not issued_token:
            issued_token = secrets.token_urlsafe(32)
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at, last_seen_at, max_idle_seconds) VALUES (?, ?, ?, ?, ?)",
                (issued_token, int(head_user["id"]), now, now, max_idle_seconds),
            )

        conn.execute("UPDATE sessions SET last_seen_at = ? WHERE token = ?", (now, issued_token))
        conn.execute(
            "UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?",
            (now, now, int(head_user["id"])),
        )

    if not issued_token:
        return

    secure_cookie = should_use_secure_cookie(request)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=issued_token,
        httponly=True,
        samesite=normalize_samesite(SESSION_COOKIE_SAMESITE),
        max_age=max_idle_seconds,
        secure=secure_cookie,
        path="/",
    )
    set_csrf_cookie(response, request)
    mark_response_private(response)


@app.get("/demo", response_class=HTMLResponse)
async def demo_page(request: Request) -> HTMLResponse:
    tenant = resolved_demo_tenant()
    if not tenant:
        raise HTTPException(status_code=404, detail="Demo is currently unavailable.")

    response = templates.TemplateResponse("desktop_shell.html", desktop_context(request, tenant, DEFAULT_DESKTOP_ROUTE, is_demo_mode=True))
    if DEMO_AUTO_LOGIN and request.query_params.get("autologin", "1") != "0":
        ensure_demo_head_session(request, response, tenant)
    return response


@app.head("/", include_in_schema=False)
async def home_head() -> Response:
    return Response(status_code=200)


@app.get("/manifest.webmanifest", include_in_schema=False)
async def web_manifest(request: Request) -> JSONResponse:
    tenant = getattr(request.state, "tenant", None)
    payload = manifest_payload_for_tenant(tenant if isinstance(tenant, TenantContext) else None)
    return JSONResponse(
        content=payload,
        media_type="application/manifest+json",
        headers={"Cache-Control": "public, max-age=300"},
    )


@app.get("/meeting", response_class=HTMLResponse)
async def meeting_page(request: Request) -> HTMLResponse:
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization context required.")
    if request_prefers_mobile(request) and request_has_active_session(request):
        return RedirectResponse(url=f"/{tenant.slug}/mobile/meeting", status_code=307)
    return templates.TemplateResponse(
        "meeting.html",
        {
            "request": request,
            "tenant": tenant,
            "app_config": app_config_for_tenant(tenant),
        },
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def desktop_dashboard_page(request: Request) -> HTMLResponse:
    return render_desktop_page(request, desktop_route="dashboard")


@app.get("/rushees", response_class=HTMLResponse)
async def desktop_rushees_page(request: Request) -> HTMLResponse:
    return render_desktop_page(request, desktop_route="rushees")


@app.get("/meetings", response_class=HTMLResponse)
async def desktop_meetings_page(request: Request) -> HTMLResponse:
    return render_desktop_page(request, desktop_route="meetings")


@app.get("/team", response_class=HTMLResponse)
async def desktop_team_page(request: Request) -> HTMLResponse:
    return render_desktop_page(request, desktop_route="team")


@app.get("/calendar", response_class=HTMLResponse)
async def desktop_calendar_page(request: Request) -> HTMLResponse:
    return render_desktop_page(request, desktop_route="calendar")


@app.get("/admin", response_class=HTMLResponse)
async def desktop_admin_page(request: Request) -> HTMLResponse:
    return render_desktop_page(request, desktop_route="admin")


@app.get("/member", response_class=HTMLResponse)
async def member_portal_page(request: Request) -> HTMLResponse:
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization context required.")
    return templates.TemplateResponse(
        "member_portal.html",
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


@app.get("/mobile/meetings", response_class=HTMLResponse)
async def mobile_meetings_page(request: Request) -> HTMLResponse:
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization context required.")
    return templates.TemplateResponse(
        "mobile_meeting.html",
        {
            "request": request,
            "tenant": tenant,
            "app_config": app_config_for_tenant(tenant),
            "mobile_page": "meetings",
        },
    )


@app.get("/mobile/calendar", response_class=HTMLResponse)
async def mobile_calendar_page(request: Request) -> HTMLResponse:
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization context required.")
    return templates.TemplateResponse(
        "mobile_calendar.html",
        {
            "request": request,
            "tenant": tenant,
            "app_config": app_config_for_tenant(tenant),
            "mobile_page": "calendar",
        },
    )


@app.get("/mobile/admin", response_class=HTMLResponse)
async def mobile_admin_page(request: Request) -> HTMLResponse:
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization context required.")
    session_role = request_session_role(request)
    if session_role and session_role != ROLE_HEAD:
        return RedirectResponse(url=f"/{tenant.slug}/mobile?notice=admin-access-denied", status_code=307)
    return templates.TemplateResponse(
        "mobile_admin.html",
        {
            "request": request,
            "tenant": tenant,
            "app_config": app_config_for_tenant(tenant),
            "mobile_page": "admin",
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


@app.get("/member-signup-qr.svg")
async def member_signup_qr(request: Request) -> Response:
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization context required.")
    if segno is None:
        raise HTTPException(status_code=503, detail="QR generator is not available on this deployment.")

    base_url = app_base_origin(request)
    signup_url = f"{base_url}/{tenant.slug}/member"
    qr = segno.make(signup_url, error="m", micro=False)
    output = io.BytesIO()
    qr.save(
        output,
        kind="svg",
        border=2,
        scale=6,
        dark=tenant.theme_primary,
        light="#ffffff",
    )
    return Response(
        content=output.getvalue(),
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=300"},
    )


@app.get("/platform", response_class=HTMLResponse)
async def platform_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("platform_admin.html", {"request": request})


def tenant_admin_payload(row: sqlite3.Row) -> dict[str, Any]:
    calendar_token = (row["calendar_share_token"] or "").strip() if "calendar_share_token" in row.keys() else ""
    tenant = tenant_context_from_row(row)
    base_path = f"/{tenant.slug}"
    return {
        "slug": tenant.slug,
        "display_name": tenant.display_name,
        "chapter_name": tenant.chapter_name,
        "org_type": tenant.org_type,
        "setup_tagline": tenant.setup_tagline,
        "logo_path": row["logo_path"],
        "theme_primary": tenant.theme_primary,
        "theme_secondary": tenant.theme_secondary,
        "theme_tertiary": tenant.theme_tertiary,
        "rating_criteria": list(tenant.rating_criteria),
        "rating_total_max": tenant.rating_total_max,
        "role_weights": {
            "officer": tenant.role_weight_officer,
            "rusher": tenant.role_weight_rusher,
        },
        "default_interest_tags": list(tenant.default_interest_tags),
        "default_stereotype_tags": list(tenant.default_stereotype_tags),
        "db_path": row["db_path"],
        "head_seed_username": row["head_seed_username"],
        "is_active": bool(row["is_active"]),
        "is_default": tenant.slug == DEFAULT_TENANT_SLUG,
        "calendar_feed_path": f"{base_path}/calendar/rush.ics?token={calendar_token}" if calendar_token else None,
        "calendar_lunch_feed_path": f"{base_path}/calendar/lunches.ics?token={calendar_token}" if calendar_token else None,
        "member_signup_path": f"{base_path}/member",
        "member_signup_qr_path": f"{base_path}/member-signup-qr.svg",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@app.post("/platform/api/auth/login")
def platform_login(payload: PlatformLoginRequest, request: Request, response: Response) -> dict[str, Any]:
    throttle_key = login_throttle_key(request, payload.username, scope="platform")
    assert_login_allowed(throttle_key)

    with platform_db_session() as conn:
        row = conn.execute("SELECT * FROM platform_admins WHERE username = ?", (payload.username.strip(),)).fetchone()
        if not row:
            record_login_failure(throttle_key)
            raise HTTPException(status_code=401, detail="Invalid username or password.")

        password_ok, needs_upgrade = verify_access_code(payload.access_code, row["access_code_hash"])
        if not password_ok:
            record_login_failure(throttle_key)
            raise HTTPException(status_code=401, detail="Invalid username or password.")

        token = secrets.token_urlsafe(32)
        now = now_iso()
        max_idle_seconds = platform_session_idle_seconds(bool(payload.remember_me))
        conn.execute(
            "INSERT INTO platform_sessions (token, admin_id, created_at, last_seen_at, max_idle_seconds) VALUES (?, ?, ?, ?, ?)",
            (token, row["id"], now, now, max_idle_seconds),
        )
        conn.execute("UPDATE platform_admins SET last_login_at = ?, updated_at = ? WHERE id = ?", (now, now, row["id"]))
        if needs_upgrade:
            conn.execute(
                "UPDATE platform_admins SET access_code_hash = ?, updated_at = ? WHERE id = ?",
                (hash_access_code(payload.access_code), now_iso(), row["id"]),
            )

    secure_cookie = should_use_secure_cookie(request)
    response.set_cookie(
        key=PLATFORM_SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite=normalize_samesite(SESSION_COOKIE_SAMESITE),
        max_age=max_idle_seconds,
        secure=secure_cookie,
        path="/",
    )
    set_csrf_cookie(response, request)
    mark_response_private(response)
    record_login_success(throttle_key)
    return {"admin": platform_user_payload(row), "message": "Platform admin logged in."}


@app.post("/platform/api/auth/logout")
def platform_logout(request: Request, response: Response) -> dict[str, str]:
    token = request.cookies.get(PLATFORM_SESSION_COOKIE)
    if token:
        with platform_db_session() as conn:
            conn.execute("DELETE FROM platform_sessions WHERE token = ?", (token,))
    secure_cookie = should_use_secure_cookie(request)
    response.delete_cookie(
        key=PLATFORM_SESSION_COOKIE,
        path="/",
        secure=secure_cookie,
        samesite=normalize_samesite(SESSION_COOKIE_SAMESITE),
    )
    response.delete_cookie(
        key=CSRF_COOKIE,
        path="/",
        secure=secure_cookie,
        samesite=normalize_samesite(SESSION_COOKIE_SAMESITE),
    )
    mark_response_private(response)
    return {"message": "Logged out."}


@app.get("/platform/api/auth/me")
def platform_auth_me(
    request: Request,
    response: Response,
    admin: sqlite3.Row | None = Depends(current_platform_admin_optional),
) -> dict[str, Any]:
    if not request.cookies.get(CSRF_COOKIE):
        set_csrf_cookie(response, request)
    mark_response_private(response)
    if not admin:
        return {"authenticated": False, "admin": None}
    return {"authenticated": True, "admin": platform_user_payload(admin)}


@app.get("/platform/api/tenants")
def platform_list_tenants(_: sqlite3.Row = Depends(current_platform_admin)) -> dict[str, Any]:
    with platform_db_session() as conn:
        rows = conn.execute("SELECT * FROM tenants ORDER BY display_name ASC").fetchall()
    return {"tenants": [tenant_admin_payload(row) for row in rows]}


def criteria_payload_list(raw: list[TenantRatingCriterionInput] | None) -> list[dict[str, Any]]:
    if not raw:
        return default_rating_criteria()
    return [
        {
            "field": item.field,
            "label": item.label,
            "short_label": item.short_label,
            "max": item.max,
        }
        for item in raw
    ]


@app.post("/platform/api/tenants")
def platform_create_tenant(payload: TenantCreateRequest, _: sqlite3.Row = Depends(current_platform_admin)) -> dict[str, Any]:
    slug = normalize_slug(payload.slug)
    display_name = payload.display_name.strip()
    chapter_name = payload.chapter_name.strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="Display name is required.")
    if not chapter_name:
        raise HTTPException(status_code=400, detail="Chapter name is required.")

    org_type = normalize_org_type(payload.org_type)
    setup_tagline = sanitize_short_text(payload.setup_tagline, "", max_length=180)
    theme_primary = normalize_theme_color(payload.theme_primary or "", DEFAULT_THEME_PRIMARY)
    theme_secondary = normalize_theme_color(payload.theme_secondary or "", DEFAULT_THEME_SECONDARY)
    theme_tertiary = normalize_theme_color(payload.theme_tertiary or "", DEFAULT_THEME_TERTIARY)
    officer_weight, rusher_weight = normalize_role_weights(payload.officer_weight, payload.rusher_weight)
    rating_criteria = normalize_rating_criteria_config(criteria_payload_list(payload.rating_criteria))
    rating_criteria_json = json.dumps(rating_criteria, separators=(",", ":"))
    default_interest_tags = parse_default_interest_tags(payload.default_interest_tags or DEFAULT_INTEREST_TAG_SUGGESTIONS)
    default_stereotype_tags = parse_default_stereotype_tags(payload.default_stereotype_tags or DEFAULT_STEREOTYPE_TAG_SUGGESTIONS)
    default_interest_tags_json = json.dumps(default_interest_tags, separators=(",", ":"))
    default_stereotype_tags_json = json.dumps(default_stereotype_tags, separators=(",", ":"))
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
                org_type,
                setup_tagline,
                logo_path,
                theme_primary,
                theme_secondary,
                theme_tertiary,
                rating_criteria_json,
                officer_weight,
                rusher_weight,
                default_interest_tags,
                default_stereotype_tags,
                calendar_share_token,
                db_path,
                head_seed_username,
                head_seed_first_name,
                head_seed_last_name,
                head_seed_pledge_class,
                created_at,
                updated_at,
                is_active
            )
            VALUES (
                ?,
                ?,
                ?,
                ?,
                ?,
                NULL,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                1
            )
            """,
            (
                slug,
                display_name,
                chapter_name,
                org_type,
                setup_tagline,
                theme_primary,
                theme_secondary,
                theme_tertiary,
                rating_criteria_json,
                officer_weight,
                rusher_weight,
                default_interest_tags_json,
                default_stereotype_tags_json,
                secrets.token_urlsafe(24),
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


@app.patch("/platform/api/tenants/{slug}")
def platform_update_tenant(
    slug: str,
    payload: TenantUpdateRequest,
    _: sqlite3.Row = Depends(current_platform_admin),
) -> dict[str, Any]:
    normalized_slug = normalize_slug(slug)
    with platform_db_session() as conn:
        row = conn.execute("SELECT * FROM tenants WHERE slug = ?", (normalized_slug,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Organization not found.")

        display_name = payload.display_name.strip() if payload.display_name is not None else row["display_name"]
        chapter_name = payload.chapter_name.strip() if payload.chapter_name is not None else row["chapter_name"]
        if not display_name:
            raise HTTPException(status_code=400, detail="Display name is required.")
        if not chapter_name:
            raise HTTPException(status_code=400, detail="Chapter name is required.")

        org_type = normalize_org_type(payload.org_type if payload.org_type is not None else row["org_type"])
        setup_tagline = sanitize_short_text(
            payload.setup_tagline if payload.setup_tagline is not None else row["setup_tagline"],
            "",
            max_length=180,
        )
        theme_primary = normalize_theme_color(
            payload.theme_primary if payload.theme_primary is not None else row["theme_primary"],
            DEFAULT_THEME_PRIMARY,
        )
        theme_secondary = normalize_theme_color(
            payload.theme_secondary if payload.theme_secondary is not None else row["theme_secondary"],
            DEFAULT_THEME_SECONDARY,
        )
        theme_tertiary = normalize_theme_color(
            payload.theme_tertiary
            if payload.theme_tertiary is not None
            else (row["theme_tertiary"] if "theme_tertiary" in row.keys() else DEFAULT_THEME_TERTIARY),
            DEFAULT_THEME_TERTIARY,
        )

        current_officer = row["officer_weight"] if "officer_weight" in row.keys() else 0.6
        current_rusher = row["rusher_weight"] if "rusher_weight" in row.keys() else 0.4
        officer_weight, rusher_weight = normalize_role_weights(
            payload.officer_weight if payload.officer_weight is not None else current_officer,
            payload.rusher_weight if payload.rusher_weight is not None else current_rusher,
        )

        if payload.rating_criteria is not None:
            rating_criteria = normalize_rating_criteria_config(criteria_payload_list(payload.rating_criteria))
        else:
            rating_criteria = normalize_rating_criteria_config(row["rating_criteria_json"] if "rating_criteria_json" in row.keys() else "")
        rating_criteria_json = json.dumps(rating_criteria, separators=(",", ":"))

        interest_source = (
            payload.default_interest_tags
            if payload.default_interest_tags is not None
            else (row["default_interest_tags"] if "default_interest_tags" in row.keys() else "")
        )
        stereotype_source = (
            payload.default_stereotype_tags
            if payload.default_stereotype_tags is not None
            else (row["default_stereotype_tags"] if "default_stereotype_tags" in row.keys() else "")
        )
        default_interest_tags_json = json.dumps(parse_default_interest_tags(interest_source), separators=(",", ":"))
        default_stereotype_tags_json = json.dumps(parse_default_stereotype_tags(stereotype_source), separators=(",", ":"))

        conn.execute(
            """
            UPDATE tenants
            SET
                display_name = ?,
                chapter_name = ?,
                org_type = ?,
                setup_tagline = ?,
                theme_primary = ?,
                theme_secondary = ?,
                theme_tertiary = ?,
                rating_criteria_json = ?,
                officer_weight = ?,
                rusher_weight = ?,
                default_interest_tags = ?,
                default_stereotype_tags = ?,
                updated_at = ?
            WHERE slug = ?
            """,
            (
                display_name,
                chapter_name,
                org_type,
                setup_tagline,
                theme_primary,
                theme_secondary,
                theme_tertiary,
                rating_criteria_json,
                officer_weight,
                rusher_weight,
                default_interest_tags_json,
                default_stereotype_tags_json,
                now_iso(),
                normalized_slug,
            ),
        )
        refreshed = conn.execute("SELECT * FROM tenants WHERE slug = ?", (normalized_slug,)).fetchone()

    return {"tenant": tenant_admin_payload(refreshed), "message": "Organization settings updated."}


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


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "icons" / "icon-192.png", media_type="image/png")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/admin/storage")
def storage_diagnostics(_: sqlite3.Row = Depends(require_head)) -> dict[str, Any]:
    tenant = current_tenant()
    with db_session(tenant.db_path) as conn:
        users_count = int(conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"])
        pnms_count = int(conn.execute("SELECT COUNT(*) AS count FROM pnms").fetchone()["count"])
        pnm_assignment_count = int(conn.execute("SELECT COUNT(*) AS count FROM pnm_officer_assignments").fetchone()["count"])
        ratings_count = int(conn.execute("SELECT COUNT(*) AS count FROM ratings").fetchone()["count"])
        lunches_count = int(conn.execute("SELECT COUNT(*) AS count FROM lunches").fetchone()["count"])
        rush_events_count = int(conn.execute("SELECT COUNT(*) AS count FROM rush_events").fetchone()["count"])
        engagement_events_count = int(conn.execute("SELECT COUNT(*) AS count FROM engagement_events").fetchone()["count"])
        weekly_goals_count = int(conn.execute("SELECT COUNT(*) AS count FROM weekly_goals").fetchone()["count"])
        stage_history_count = int(conn.execute("SELECT COUNT(*) AS count FROM pnm_stage_history").fetchone()["count"])
        audit_count = int(conn.execute("SELECT COUNT(*) AS count FROM audit_ledger").fetchone()["count"])
        chat_messages_count = int(conn.execute("SELECT COUNT(*) AS count FROM officer_chat_messages").fetchone()["count"])
        notifications_count = int(conn.execute("SELECT COUNT(*) AS count FROM notifications").fetchone()["count"])

    with platform_db_session() as conn:
        active_tenants = int(conn.execute("SELECT COUNT(*) AS count FROM tenants WHERE is_active = 1").fetchone()["count"])

    storage_paths = {
        "DATA_ROOT": str(DATA_ROOT),
        "DB_PATH": str(DB_PATH),
        "PLATFORM_DB_PATH": str(PLATFORM_DB_PATH),
        "TENANTS_DB_DIR": str(TENANTS_DB_DIR),
        "UPLOADS_DIR": str(UPLOADS_DIR),
        "BACKUP_DIR": str(BACKUP_DIR),
        "ACTIVE_TENANT_DB_PATH": str(tenant.db_path),
        "ACTIVE_TENANT_UPLOADS_DIR": str(tenant.pnm_uploads_dir),
        "ACTIVE_TENANT_BACKUP_DIR": str(tenant.backup_dir),
    }

    return {
        "tenant_slug": tenant.slug,
        "active_tenants": active_tenants,
        "render_env_detected": bool(os.getenv("RENDER")),
        "require_persistent_data": REQUIRE_PERSISTENT_DATA,
        "persistent_paths_ok": all(uses_data_mount(Path(path)) for path in storage_paths.values()),
        "warnings": collect_storage_warnings(),
        "table_counts": {
            "users": users_count,
            "pnms": pnms_count,
            "pnm_officer_assignments": pnm_assignment_count,
            "ratings": ratings_count,
            "lunches": lunches_count,
            "rush_events": rush_events_count,
            "engagement_events": engagement_events_count,
            "weekly_goals": weekly_goals_count,
            "pnm_stage_history": stage_history_count,
            "audit_ledger": audit_count,
            "chat_messages": chat_messages_count,
            "notifications": notifications_count,
        },
        "paths": storage_paths,
        "files": {
            "platform_db": file_metadata(PLATFORM_DB_PATH),
            "default_tenant_db": file_metadata(DB_PATH),
            "active_tenant_db": file_metadata(tenant.db_path),
        },
    }


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


@app.get("/api/admin/season/archive")
def season_archive_status(_: sqlite3.Row = Depends(require_head)) -> dict[str, Any]:
    archive_file = season_archive_path()
    with db_session() as conn:
        counts_row = conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM pnms) AS pnm_count,
                (SELECT COUNT(*) FROM ratings) AS rating_count,
                (SELECT COUNT(*) FROM lunches) AS lunch_count
            """
        ).fetchone()
        archive_row = conn.execute(
            """
            SELECT
                s.archive_path,
                s.archived_at,
                s.archived_by,
                s.archive_label,
                s.pnm_count,
                s.rating_count,
                s.lunch_count,
                u.username AS archived_by_username
            FROM season_archive_state s
            LEFT JOIN users u ON u.id = s.archived_by
            WHERE s.id = 1
            """
        ).fetchone()

    archive_payload = None
    if archive_row:
        archive_payload = {
            "archive_path": archive_row["archive_path"],
            "archived_at": archive_row["archived_at"],
            "archived_by": archive_row["archived_by"],
            "archived_by_username": archive_row["archived_by_username"],
            "archive_label": archive_row["archive_label"],
            "pnm_count": int(archive_row["pnm_count"]),
            "rating_count": int(archive_row["rating_count"]),
            "lunch_count": int(archive_row["lunch_count"]),
            "file": file_metadata(archive_file),
        }

    return {
        "confirmation_phrase": SEASON_RESET_CONFIRMATION_PHRASE,
        "archive_download_path": "/api/admin/season/archive/download" if archive_file.exists() else None,
        "archive": archive_payload,
        "current_counts": {
            "pnm_count": int(counts_row["pnm_count"]),
            "rating_count": int(counts_row["rating_count"]),
            "lunch_count": int(counts_row["lunch_count"]),
        },
    }


@app.get("/api/admin/season/archive/download")
def download_season_archive(_: sqlite3.Row = Depends(require_head)) -> FileResponse:
    archive_file = season_archive_path()
    if not archive_file.exists():
        raise HTTPException(status_code=404, detail="No archived season is available yet.")
    tenant = current_tenant()
    filename = f"{tenant.slug}-season-archive.sqlite"
    return FileResponse(
        archive_file,
        media_type="application/x-sqlite3",
        filename=filename,
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/admin/season/reset")
def reset_for_next_rush_season(payload: SeasonResetRequest, head_user: sqlite3.Row = Depends(require_head)) -> dict[str, Any]:
    if payload.confirm_phrase.strip().upper() != SEASON_RESET_CONFIRMATION_PHRASE.upper():
        raise HTTPException(
            status_code=400,
            detail=f"Confirmation phrase mismatch. Type exactly: {SEASON_RESET_CONFIRMATION_PHRASE}",
        )
    if not payload.head_chair_confirmation:
        raise HTTPException(
            status_code=400,
            detail="Head-chair confirmation is required before resetting the season.",
        )

    archive_file = season_archive_path()
    write_sqlite_snapshot(active_db_path(), archive_file)
    for stale in archive_file.parent.glob("season-archive-*.sqlite"):
        if stale == archive_file:
            continue
        stale.unlink(missing_ok=True)

    reset_at = now_iso()
    label = payload.archive_label or f"Rush Season Archived {date.today().isoformat()}"

    with db_session() as conn:
        counts_row = conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM pnms) AS pnm_count,
                (SELECT COUNT(*) FROM ratings) AS rating_count,
                (SELECT COUNT(*) FROM lunches) AS lunch_count
            """
        ).fetchone()
        pnm_count = int(counts_row["pnm_count"])
        rating_count = int(counts_row["rating_count"])
        lunch_count = int(counts_row["lunch_count"])

        conn.execute("DELETE FROM rating_changes")
        conn.execute("DELETE FROM rating_history")
        conn.execute("DELETE FROM rating_comment_events")
        conn.execute("DELETE FROM ratings")
        conn.execute("DELETE FROM officer_chat_mentions")
        conn.execute("DELETE FROM officer_chat_tags")
        conn.execute("DELETE FROM officer_chat_messages")
        conn.execute("DELETE FROM weekly_goals")
        conn.execute("DELETE FROM rush_events")
        conn.execute("DELETE FROM engagement_events")
        conn.execute("DELETE FROM pnm_stage_history")
        conn.execute("DELETE FROM notifications")
        conn.execute("DELETE FROM user_contact_downloads")
        conn.execute("DELETE FROM lunches")
        conn.execute("DELETE FROM pnms")
        conn.execute(
            """
            UPDATE users
            SET rating_count = 0, avg_rating_given = 0, total_lunches = 0, lunches_per_week = 0, updated_at = ?
            """,
            (reset_at,),
        )
        conn.execute(
            """
            INSERT INTO season_archive_state (
                id,
                archive_path,
                archived_at,
                archived_by,
                archive_label,
                pnm_count,
                rating_count,
                lunch_count
            )
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                archive_path = excluded.archive_path,
                archived_at = excluded.archived_at,
                archived_by = excluded.archived_by,
                archive_label = excluded.archive_label,
                pnm_count = excluded.pnm_count,
                rating_count = excluded.rating_count,
                lunch_count = excluded.lunch_count
            """,
            (
                str(archive_file),
                reset_at,
                head_user["id"],
                label,
                pnm_count,
                rating_count,
                lunch_count,
            ),
        )
        append_audit_entry(
            conn,
            actor_user_id=int(head_user["id"]),
            action_type="season_reset",
            entity_type="season",
            entity_id=1,
            payload={
                "archive_path": str(archive_file),
                "archive_label": label,
                "pnm_count": pnm_count,
                "rating_count": rating_count,
                "lunch_count": lunch_count,
            },
        )

    purge_pnm_uploads_dir()

    return {
        "message": "Rush season archived and reset for next season.",
        "archive": {
            "archive_path": str(archive_file),
            "archive_download_path": "/api/admin/season/archive/download",
            "archive_label": label,
            "archived_at": reset_at,
            "archived_by": head_user["id"],
            "archived_by_username": head_user["username"],
            "pnm_count": pnm_count,
            "rating_count": rating_count,
            "lunch_count": lunch_count,
        },
    }


@app.get("/api/admin/import/google-form/template")
def export_google_form_template(_: sqlite3.Row = Depends(require_head)) -> Response:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(GOOGLE_FORM_TEMPLATE_COLUMNS)
    writer.writerow(
        [
            "John",
            "Smith",
            "F",
            "Nashville",
            "+1 615 555 0110",
            "@johnsmith",
        ]
    )
    payload = buffer.getvalue().encode("utf-8")
    filename = f"google-form-rushee-template-{timestamp_slug()}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=payload, media_type="text/csv; charset=utf-8", headers=headers)


@app.post("/api/admin/import/google-form")
async def import_google_form_csv(
    file: UploadFile = File(...),
    head_user: sqlite3.Row = Depends(require_head),
) -> dict[str, Any]:
    filename = (file.filename or "").strip()
    if filename and not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a CSV file exported from Google Forms.")

    raw = await file.read(MAX_GOOGLE_FORM_IMPORT_BYTES + 1)
    if not raw:
        raise HTTPException(status_code=400, detail="CSV file cannot be empty.")
    if len(raw) > MAX_GOOGLE_FORM_IMPORT_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"CSV too large. Max size is {MAX_GOOGLE_FORM_IMPORT_BYTES // (1024 * 1024)} MB.",
        )

    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = raw.decode("latin-1")

    reader = csv.DictReader(io.StringIO(decoded))
    headers = [header.strip() for header in (reader.fieldnames or []) if header and header.strip()]
    if not headers:
        raise HTTPException(status_code=400, detail="CSV is missing a header row.")

    column_map = resolve_google_form_columns(headers)
    missing: list[str] = []
    if not (column_map["first_name"] or column_map["full_name"]):
        missing.append("First Name or Full Name")
    if not (column_map["last_name"] or column_map["full_name"]):
        missing.append("Last Name or Full Name")
    if not column_map["instagram_handle"]:
        missing.append("Instagram Handle")
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing required column(s): {', '.join(missing)}.",
        )

    created_count = 0
    skipped_duplicates = 0
    total_errors = 0
    row_count = 0
    error_limit = 80
    errors: list[dict[str, Any]] = []

    with db_session() as conn:
        existing_instagrams = {
            str(row["instagram_norm"]).strip()
            for row in conn.execute("SELECT lower(instagram_handle) AS instagram_norm FROM pnms").fetchall()
            if row["instagram_norm"]
        }

        for row_number, row in enumerate(reader, start=2):
            row_count += 1
            first_raw = csv_row_value(row, column_map["first_name"])
            last_raw = csv_row_value(row, column_map["last_name"])
            full_name_raw = csv_row_value(row, column_map["full_name"])
            if full_name_raw and (not first_raw or not last_raw):
                first_guess, last_guess = split_full_name(full_name_raw)
                if not first_raw:
                    first_raw = first_guess
                if not last_raw:
                    last_raw = last_guess

            class_year_raw = csv_row_value(row, column_map["class_year"])
            hometown_raw = csv_row_value(row, column_map["hometown"]) or "Unknown"
            phone_raw = csv_row_value(row, column_map["phone_number"])
            instagram_raw = csv_row_value(row, column_map["instagram_handle"])
            first_event_raw = date.today().isoformat()

            try:
                first_name = normalize_name(first_raw)
                last_name = normalize_name(last_raw)
                class_year = normalize_import_class_year(class_year_raw)
                hometown = hometown_raw.strip()
                if not hometown:
                    hometown = "Unknown"
                hometown = hometown[:80]
                hometown_state_code = resolve_pnm_state_code(hometown)
                instagram_handle = normalize_instagram_handle(instagram_raw)
                phone_number = normalize_phone_number(phone_raw)
                first_event_date = verify_iso_date(first_event_raw, "First event date")
                interests = [default_interest_tag_for_tenant()]
                interests_csv, interests_norm = encode_interests(interests)
                stereotype = default_stereotype_tag_for_tenant()
                notes = ""
            except ValueError as exc:
                total_errors += 1
                if len(errors) < error_limit:
                    errors.append({"row": row_number, "reason": str(exc)})
                continue

            instagram_norm = instagram_handle.lower()
            if instagram_norm in existing_instagrams:
                skipped_duplicates += 1
                continue

            created_at = now_iso()
            cursor = conn.execute(
                """
                INSERT INTO pnms (
                    pnm_code,
                    first_name,
                    last_name,
                    class_year,
                    hometown,
                    hometown_state_code,
                    phone_number,
                    instagram_handle,
                    first_event_date,
                    interests,
                    interests_norm,
                    stereotype,
                    lunch_stats,
                    notes,
                    created_by,
                    created_at,
                    updated_at
                )
                VALUES ('TBD', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?)
                """,
                (
                    first_name,
                    last_name,
                    class_year,
                    hometown,
                    hometown_state_code,
                    phone_number,
                    instagram_handle,
                    first_event_date,
                    interests_csv,
                    interests_norm,
                    stereotype,
                    notes,
                    head_user["id"],
                    created_at,
                    created_at,
                ),
            )
            pnm_id = int(cursor.lastrowid)
            code = ensure_unique_pnm_code(conn, pnm_id, pnm_code_base(first_name, last_name, first_event_date))
            conn.execute("UPDATE pnms SET pnm_code = ?, updated_at = ? WHERE id = ?", (code, now_iso(), pnm_id))
            fetched_photo = try_fetch_instagram_profile_photo(instagram_handle)
            if fetched_photo:
                photo_bytes, extension = fetched_photo
                try:
                    public_path, target_path = write_pnm_photo_bytes(pnm_id, photo_bytes, extension)
                except OSError:
                    public_path = None
                    target_path = None
                if public_path and target_path:
                    try:
                        now = now_iso()
                        conn.execute(
                            """
                            UPDATE pnms
                            SET photo_path = ?, photo_uploaded_at = ?, photo_uploaded_by = ?, updated_at = ?
                            WHERE id = ?
                            """,
                            (public_path, now, head_user["id"], now, pnm_id),
                        )
                    except Exception:
                        target_path.unlink(missing_ok=True)
                        raise
            existing_instagrams.add(instagram_norm)
            created_count += 1

    imported_message = f"Imported {created_count} rushee(s)."
    if skipped_duplicates:
        imported_message += f" Skipped {skipped_duplicates} duplicate instagram handle(s)."
    if total_errors:
        imported_message += f" {total_errors} row(s) had validation issues."

    return {
        "message": imported_message,
        "rows_processed": row_count,
        "created_count": created_count,
        "skipped_duplicates": skipped_duplicates,
        "error_count": total_errors,
        "errors_truncated": total_errors > len(errors),
        "errors": errors,
        "column_mapping": column_map,
    }


@app.get("/api/export/contacts/status")
def export_contacts_download_status(user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    with db_session() as conn:
        downloads = contact_download_status_records(conn, user_id=int(user["id"]))
    return {
        "downloads": downloads,
        "downloaded_count": len(downloads),
    }


@app.get("/api/export/contacts/{pnm_id}.vcf")
def export_single_contact_vcf(pnm_id: int, user: sqlite3.Row = Depends(current_user)) -> Response:
    tenant = CURRENT_TENANT.get()
    if tenant is None:
        default_row = require_tenant_exists(DEFAULT_TENANT_SLUG)
        tenant = tenant_context_from_row(default_row)

    with db_session() as conn:
        row = conn.execute(
            """
            SELECT id, first_name, last_name, pnm_code, phone_number, instagram_handle, photo_path
            FROM pnms
            WHERE id = ?
            """,
            (pnm_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Rushee not found.")
        stamp = now_iso()
        upsert_contact_download_records(
            conn,
            user_id=int(user["id"]),
            pnm_ids=[int(row["id"])],
            downloaded_at=stamp,
        )

    card = build_pnm_vcard(row, tenant.display_name)
    payload = f"{card}\r\n".encode("utf-8")
    safe_code = re.sub(r"[^A-Za-z0-9_-]+", "-", row["pnm_code"] or "pnm").strip("-") or "pnm"
    filename = f"pnm-contact-{safe_code}.vcf"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Content-Type-Options": "nosniff",
    }
    return Response(content=payload, media_type="text/x-vcard; charset=utf-8", headers=headers)


@app.get("/api/export/contacts.vcf")
def export_contacts_vcf(user: sqlite3.Row = Depends(current_user)) -> Response:
    tenant = CURRENT_TENANT.get()
    if tenant is None:
        default_row = require_tenant_exists(DEFAULT_TENANT_SLUG)
        tenant = tenant_context_from_row(default_row)

    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT id, first_name, last_name, pnm_code, phone_number, instagram_handle, photo_path
            FROM pnms
            ORDER BY last_name ASC, first_name ASC
            """
        ).fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail="No rushees available to export yet.")
        upsert_contact_download_records(
            conn,
            user_id=int(user["id"]),
            pnm_ids=[int(row["id"]) for row in rows],
            downloaded_at=now_iso(),
        )

    cards = [build_pnm_vcard(row, tenant.display_name) for row in rows]
    payload = ("\r\n".join(cards) + ("\r\n" if cards else "")).encode("utf-8")
    filename = f"pnm-contacts-{tenant.slug}-{timestamp_slug()}.vcf"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Content-Type-Options": "nosniff",
    }
    return Response(content=payload, media_type="text/x-vcard; charset=utf-8", headers=headers)


@app.get("/api/export/contacts-assigned.vcf")
def export_assigned_contacts_vcf(user: sqlite3.Row = Depends(require_officer)) -> Response:
    tenant = CURRENT_TENANT.get()
    if tenant is None:
        default_row = require_tenant_exists(DEFAULT_TENANT_SLUG)
        tenant = tenant_context_from_row(default_row)

    with db_session() as conn:
        if user["role"] == ROLE_HEAD:
            rows = conn.execute(
                """
                SELECT DISTINCT
                    p.id,
                    p.first_name,
                    p.last_name,
                    p.pnm_code,
                    p.phone_number,
                    p.instagram_handle,
                    p.photo_path
                FROM pnms p
                WHERE
                    p.assigned_officer_id IS NOT NULL
                    OR EXISTS (SELECT 1 FROM pnm_officer_assignments pa WHERE pa.pnm_id = p.id)
                ORDER BY p.last_name ASC, p.first_name ASC
                """
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT DISTINCT
                    p.id,
                    p.first_name,
                    p.last_name,
                    p.pnm_code,
                    p.phone_number,
                    p.instagram_handle,
                    p.photo_path
                FROM pnms p
                WHERE
                    EXISTS (
                        SELECT 1
                        FROM pnm_officer_assignments pa
                        WHERE pa.pnm_id = p.id
                          AND pa.officer_user_id = ?
                    )
                    OR (
                        p.assigned_officer_id = ?
                        AND NOT EXISTS (SELECT 1 FROM pnm_officer_assignments pa2 WHERE pa2.pnm_id = p.id)
                    )
                ORDER BY p.last_name ASC, p.first_name ASC
                """,
                (int(user["id"]), int(user["id"])),
            ).fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail="No assigned rushee contacts available yet.")

        upsert_contact_download_records(
            conn,
            user_id=int(user["id"]),
            pnm_ids=[int(row["id"]) for row in rows],
            downloaded_at=now_iso(),
        )

    cards = [build_pnm_vcard(row, tenant.display_name) for row in rows]
    payload = ("\r\n".join(cards) + ("\r\n" if cards else "")).encode("utf-8")
    suffix = "assigned"
    filename = f"pnm-contacts-{suffix}-{tenant.slug}-{timestamp_slug()}.vcf"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Content-Type-Options": "nosniff",
    }
    return Response(content=payload, media_type="text/x-vcard; charset=utf-8", headers=headers)


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
    stereotype = default_stereotype_tag_for_tenant()
    interests_csv, interests_norm = encode_interests([default_interest_tag_for_tenant()])
    emoji = payload.emoji if payload.emoji else "🛡️"
    city = payload.city if payload.city is not None else ""
    state_code = payload.state if payload.state is not None else ""

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
                    city,
                    state_code,
                    access_code_hash,
                    is_approved,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
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
                    city,
                    state_code,
                    hash_access_code(payload.access_code),
                    created_at,
                    created_at,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=400, detail=f"Could not register user: {exc}") from exc

    return {
        "message": "Registration submitted. Rush team approval is required before login.",
        "username": username,
    }


@app.post("/api/auth/register-member")
def register_member(payload: MemberRegisterRequest) -> dict[str, str]:
    try:
        validate_access_code_strength(payload.access_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    username = payload.username.strip()
    parts = [token for token in re.split(r"[._-]+", username) if token]
    first_name = normalize_name((parts[0] if parts else "Fraternity")[:48])
    last_name = normalize_name((parts[1] if len(parts) > 1 else "Member")[:48])
    pledge_class = "Brotherhood"
    stereotype = default_stereotype_tag_for_tenant()
    interests_csv, interests_norm = encode_interests([default_interest_tag_for_tenant()])
    city = payload.city if payload.city is not None else ""
    state_code = payload.state if payload.state is not None else ""

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
                    city,
                    state_code,
                    access_code_hash,
                    is_approved,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    username,
                    first_name,
                    last_name,
                    pledge_class,
                    ROLE_RUSHER,
                    None,
                    stereotype,
                    interests_csv,
                    interests_norm,
                    city,
                    state_code,
                    hash_access_code(payload.access_code),
                    created_at,
                    created_at,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=400, detail=f"Could not register member: {exc}") from exc

    return {
        "message": "Registration submitted. A rush team member must approve this account before login.",
        "username": username,
    }


@app.post("/api/auth/login")
def login(payload: LoginRequest, request: Request, response: Response) -> dict[str, Any]:
    throttle_key = login_throttle_key(request, payload.username, scope="tenant")
    assert_login_allowed(throttle_key)

    with db_session() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (payload.username.strip(),)).fetchone()
        if not row:
            record_login_failure(throttle_key)
            raise HTTPException(status_code=401, detail="Invalid username or password.")

        password_ok, needs_upgrade = verify_access_code(payload.access_code, row["access_code_hash"])
        if not password_ok:
            record_login_failure(throttle_key)
            raise HTTPException(status_code=401, detail="Invalid username or password.")

        if not bool(row["is_approved"]):
            raise HTTPException(status_code=403, detail="Username pending rush team approval.")

        token = secrets.token_urlsafe(32)
        now = now_iso()
        max_idle_seconds = user_session_idle_seconds(bool(payload.remember_me))
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, last_seen_at, max_idle_seconds) VALUES (?, ?, ?, ?, ?)",
            (token, row["id"], now, now, max_idle_seconds),
        )
        conn.execute("UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?", (now, now, row["id"]))
        if needs_upgrade:
            conn.execute(
                "UPDATE users SET access_code_hash = ?, updated_at = ? WHERE id = ?",
                (hash_access_code(payload.access_code), now_iso(), row["id"]),
            )

        secure_cookie = should_use_secure_cookie(request)
        response.set_cookie(
            key=SESSION_COOKIE,
            value=token,
            httponly=True,
            samesite=normalize_samesite(SESSION_COOKIE_SAMESITE),
            max_age=max_idle_seconds,
            secure=secure_cookie,
            path="/",
        )
        set_csrf_cookie(response, request)
        mark_response_private(response)
        record_login_success(throttle_key)

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
    secure_cookie = should_use_secure_cookie(request)
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        secure=secure_cookie,
        samesite=normalize_samesite(SESSION_COOKIE_SAMESITE),
    )
    response.delete_cookie(
        key=CSRF_COOKIE,
        path="/",
        secure=secure_cookie,
        samesite=normalize_samesite(SESSION_COOKIE_SAMESITE),
    )
    mark_response_private(response)
    return {"message": "Logged out."}


@app.get("/api/auth/me")
def auth_me(
    request: Request,
    response: Response,
    user: sqlite3.Row | None = Depends(current_user_optional),
) -> dict[str, Any]:
    if not request.cookies.get(CSRF_COOKIE):
        set_csrf_cookie(response, request)
    mark_response_private(response)
    if not user:
        return {"authenticated": False, "user": None}
    return {
        "authenticated": True,
        "user": user_payload(user, user["role"], user["id"]),
    }


@app.post("/api/auth/tutorial/complete")
def complete_tutorial(payload: TutorialCompleteRequest, user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    completed_at = now_iso()
    with db_session() as conn:
        conn.execute(
            """
            UPDATE users
            SET onboarding_mode = ?, onboarding_completed_at = ?, onboarding_version = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                payload.mode,
                completed_at,
                max(payload.version, ONBOARDING_TUTORIAL_VERSION),
                completed_at,
                user["id"],
            ),
        )
        refreshed = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
    return {
        "message": "Tutorial completed.",
        "user": user_payload(refreshed, refreshed["role"], refreshed["id"]),
    }


@app.get("/api/users/pending")
def pending_users(_: sqlite3.Row = Depends(require_officer)) -> dict[str, Any]:
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
def approve_user(user_id: int, approver: sqlite3.Row = Depends(require_officer)) -> dict[str, str]:
    with db_session() as conn:
        row = conn.execute("SELECT id, username, is_approved FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found.")
        if bool(row["is_approved"]):
            return {"message": "User already approved."}

        conn.execute(
            "UPDATE users SET is_approved = 1, approved_by = ?, approved_at = ?, updated_at = ? WHERE id = ?",
            (approver["id"], now_iso(), now_iso(), user_id),
        )
        append_audit_entry(
            conn,
            actor_user_id=int(approver["id"]),
            action_type="user_approve",
            entity_type="user",
            entity_id=user_id,
            payload={"username": row["username"]},
        )
        create_notification(
            conn,
            user_id=int(user_id),
            notif_type="approval",
            title="Account Approved",
            body="You can now sign in and start contributing.",
            link_path="/",
        )

    return {"message": "User approved."}


@app.post("/api/users/{user_id}/disapprove")
def disapprove_user(user_id: int, actor: sqlite3.Row = Depends(require_officer)) -> dict[str, str]:
    with db_session() as conn:
        row = conn.execute("SELECT id, username, role, is_approved FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found.")
        if int(row["id"]) == int(actor["id"]):
            raise HTTPException(status_code=400, detail="You cannot disapprove your own account.")
        if row["role"] == ROLE_HEAD:
            raise HTTPException(status_code=400, detail="Head Rush Officer accounts cannot be disapproved.")
        if not bool(row["is_approved"]):
            return {"message": "User already pending approval."}

        conn.execute(
            "UPDATE users SET is_approved = 0, approved_by = NULL, approved_at = NULL, updated_at = ? WHERE id = ?",
            (now_iso(), user_id),
        )
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        append_audit_entry(
            conn,
            actor_user_id=int(actor["id"]),
            action_type="user_disapprove",
            entity_type="user",
            entity_id=user_id,
            payload={"username": row["username"]},
        )

    return {"message": f"{row['username']} has been disapproved and moved to pending approval."}


@app.get("/api/admin/rush-officers")
def head_admin_officer_metrics(_: sqlite3.Row = Depends(require_head)) -> dict[str, Any]:
    with db_session() as conn:
        heads = conn.execute(
            """
            SELECT id, username, last_login_at, rating_count, total_lunches, lunches_per_week
            FROM users
            WHERE role = ? AND is_approved = 1
            ORDER BY username ASC
            """,
            (ROLE_HEAD,),
        ).fetchall()
        officers = conn.execute(
            """
            SELECT
                u.id,
                u.username,
                u.emoji,
                u.stereotype,
                u.interests,
                u.rating_count,
                u.avg_rating_given,
                u.total_lunches,
                u.lunches_per_week,
                u.last_login_at,
                COALESCE((SELECT AVG(r.total_score) FROM ratings r WHERE r.user_id = u.id), 0) AS avg_rating_total,
                COALESCE((SELECT COUNT(*) FROM pnms p WHERE p.assigned_officer_id = u.id), 0) AS assigned_pnms_count
            FROM users u
            WHERE u.role = ? AND u.is_approved = 1
            ORDER BY u.rating_count DESC, u.total_lunches DESC, u.username ASC
            """,
            (ROLE_RUSH_OFFICER,),
        ).fetchall()

    officer_payload = []
    for row in officers:
        participation_score = float(row["rating_count"]) * 1.5 + float(row["total_lunches"])
        officer_payload.append(
            {
                "user_id": row["id"],
                "username": row["username"],
                "emoji": row["emoji"],
                "stereotype": row["stereotype"],
                "interests": decode_interests(row["interests"]),
                "rating_count": int(row["rating_count"]),
                "avg_rating_given": round(float(row["avg_rating_given"]), 2),
                "avg_rating_total": round(float(row["avg_rating_total"]), 2),
                "total_lunches": int(row["total_lunches"]),
                "lunches_per_week": round(float(row["lunches_per_week"]), 2),
                "assigned_pnms_count": int(row["assigned_pnms_count"]),
                "last_login_at": row["last_login_at"],
                "participation_score": round(participation_score, 2),
            }
        )

    summary = {
        "head_count": len(heads),
        "officer_count": len(officer_payload),
        "total_officer_ratings": sum(item["rating_count"] for item in officer_payload),
        "total_officer_lunches": sum(item["total_lunches"] for item in officer_payload),
        "avg_officer_score_given": round(
            sum(item["avg_rating_total"] for item in officer_payload) / len(officer_payload), 2
        )
        if officer_payload
        else 0.0,
    }

    return {
        "summary": summary,
        "current_heads": [
            {
                "user_id": row["id"],
                "username": row["username"],
                "last_login_at": row["last_login_at"],
                "rating_count": int(row["rating_count"]),
                "total_lunches": int(row["total_lunches"]),
                "lunches_per_week": round(float(row["lunches_per_week"]), 2),
            }
            for row in heads
        ],
        "rush_officers": officer_payload,
    }


@app.post("/api/admin/officers/{user_id}/promote-head")
def promote_officer_to_head(
    user_id: int,
    payload: PromoteHeadRequest,
    actor: sqlite3.Row = Depends(require_head),
) -> dict[str, Any]:
    with db_session() as conn:
        target = conn.execute(
            "SELECT id, username, role, is_approved FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="User not found.")
        if not bool(target["is_approved"]):
            raise HTTPException(status_code=400, detail="User must be approved before role changes.")
        if target["role"] == ROLE_HEAD:
            return {"message": f"{target['username']} is already a Head Rush Officer.", "demoted_heads": 0}
        if target["role"] != ROLE_RUSH_OFFICER:
            raise HTTPException(status_code=400, detail="Only approved Rush Officers can be promoted to Head Rush Officer.")

        demoted_head_ids: list[int] = []
        if payload.demote_existing_heads:
            demoted_rows = conn.execute(
                "SELECT id FROM users WHERE role = ? AND id != ? AND is_approved = 1",
                (ROLE_HEAD, user_id),
            ).fetchall()
            demoted_head_ids = [int(row["id"]) for row in demoted_rows]
            if demoted_head_ids:
                demoted_emoji = payload.demoted_head_emoji or DEFAULT_RUSH_OFFICER_EMOJI
                conn.execute(
                    """
                    UPDATE users
                    SET role = ?, emoji = COALESCE(NULLIF(trim(emoji), ''), ?), updated_at = ?
                    WHERE id IN (SELECT CAST(value AS INTEGER) FROM json_each(?))
                    """,
                    (ROLE_RUSH_OFFICER, demoted_emoji, now_iso(), json.dumps(demoted_head_ids)),
                )

        conn.execute(
            "UPDATE users SET role = ?, emoji = NULL, updated_at = ? WHERE id = ?",
            (ROLE_HEAD, now_iso(), user_id),
        )
        append_audit_entry(
            conn,
            actor_user_id=int(actor["id"]),
            action_type="role_promote_head",
            entity_type="user",
            entity_id=user_id,
            payload={
                "username": target["username"],
                "demoted_head_count": len(demoted_head_ids),
                "demoted_head_ids": demoted_head_ids,
            },
        )
        refreshed = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    return {
        "message": f"{target['username']} promoted to Head Rush Officer.",
        "demoted_heads": len(demoted_head_ids),
        "user": {
            "user_id": refreshed["id"],
            "username": refreshed["username"],
            "role": refreshed["role"],
        },
    }


@app.get("/api/users")
def list_users(
    interest: str | None = None,
    stereotype: str | None = None,
    role: str | None = "all",
    state: str | None = None,
    city: str | None = None,
    sort: str | None = "location",
    user: sqlite3.Row = Depends(current_user),
) -> dict[str, Any]:
    try:
        interest_filter = parse_interest_filter(interest)
        role_filter = normalize_role_filter(role)
        state_filter = parse_state_filter(state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    normalized_stereotype = stereotype.strip().lower() if stereotype and stereotype.strip() else None
    city_token = normalize_city_value(city) if city is not None else ""
    city_filter = city_token.lower() if city_token else None
    sort_token = str(sort or "location").strip().lower() or "location"
    if sort_token not in {"location", "username", "role"}:
        raise HTTPException(status_code=400, detail="Sort must be one of: location, username, role.")

    with db_session() as conn:
        rows = conn.execute("SELECT * FROM users WHERE is_approved = 1").fetchall()

    filtered: list[sqlite3.Row] = []
    for row in rows:
        if role_filter and row["role"] != role_filter:
            continue
        if normalized_stereotype and row["stereotype"].lower() != normalized_stereotype:
            continue
        if not has_interest_match(row["interests_norm"], interest_filter):
            continue
        row_state = normalize_state_code(row["state_code"]) if "state_code" in row.keys() else ""
        if state_filter and row_state != state_filter:
            continue
        if city_filter:
            row_city = normalize_city_value(row["city"]) if "city" in row.keys() else ""
            if city_filter not in row_city.lower():
                continue
        filtered.append(row)

    if sort_token == "username":
        filtered.sort(key=lambda row: (str(row["username"]).lower(), int(row["id"])))
    elif sort_token == "role":
        filtered.sort(
            key=lambda row: (
                role_sort_value(row["role"]),
                str(row["username"]).lower(),
            )
        )
    else:
        filtered.sort(key=user_location_sort_key)

    return {"users": [user_payload(row, user["role"], user["id"]) for row in filtered]}


@app.patch("/api/users/me")
def update_self(payload: SelfUpdateRequest, user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    if (
        payload.stereotype is None
        and payload.interests is None
        and payload.emoji is None
        and payload.city is None
        and payload.state is None
    ):
        raise HTTPException(status_code=400, detail="No changes provided.")

    with db_session() as conn:
        existing = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="User not found.")

        stereotype_value = existing["stereotype"]
        interests_csv = existing["interests"]
        interests_norm = existing["interests_norm"]
        emoji_value = existing["emoji"]
        city_value = normalize_city_value(existing["city"]) if "city" in existing.keys() else ""
        state_code_value = normalize_state_code(existing["state_code"]) if "state_code" in existing.keys() else ""

        if payload.stereotype is not None:
            try:
                stereotype_value = enforce_allowed_stereotype(payload.stereotype)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        if payload.interests is not None:
            try:
                interests = enforce_allowed_interests(parse_interests(payload.interests))
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            interests_csv, interests_norm = encode_interests(interests)

        if payload.emoji is not None:
            if user["role"] != ROLE_RUSH_OFFICER:
                raise HTTPException(status_code=400, detail="Only Rush Officers can set emoji identifiers.")
            if not payload.emoji.strip():
                raise HTTPException(status_code=400, detail="Emoji cannot be empty for Rush Officers.")
            emoji_value = payload.emoji.strip()

        if payload.city is not None:
            city_value = payload.city
        if payload.state is not None:
            state_code_value = payload.state

        conn.execute(
            """
            UPDATE users
            SET stereotype = ?, interests = ?, interests_norm = ?, emoji = ?, city = ?, state_code = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                stereotype_value,
                interests_csv,
                interests_norm,
                emoji_value,
                city_value,
                state_code_value,
                now_iso(),
                user["id"],
            ),
        )
        refreshed = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()

    return {"user": user_payload(refreshed, refreshed["role"], refreshed["id"])}


@app.patch("/api/users/{user_id}/location")
def update_user_location(
    user_id: int,
    payload: UserLocationUpdateRequest,
    actor: sqlite3.Row = Depends(require_officer),
) -> dict[str, Any]:
    if payload.city is None and payload.state is None:
        raise HTTPException(status_code=400, detail="No location changes provided.")

    with db_session() as conn:
        existing = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="User not found.")

        city_value = normalize_city_value(existing["city"]) if "city" in existing.keys() else ""
        state_code_value = normalize_state_code(existing["state_code"]) if "state_code" in existing.keys() else ""

        if payload.city is not None:
            city_value = payload.city
        if payload.state is not None:
            state_code_value = payload.state

        conn.execute(
            "UPDATE users SET city = ?, state_code = ?, updated_at = ? WHERE id = ?",
            (city_value, state_code_value, now_iso(), user_id),
        )
        refreshed = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    return {"user": user_payload(refreshed, actor["role"], actor["id"])}


@app.post("/api/pnms")
def create_pnm(payload: PNMCreateRequest, user: sqlite3.Row = Depends(require_officer)) -> dict[str, Any]:
    try:
        interests = enforce_allowed_interests(parse_interests(payload.interests))
        instagram_handle = normalize_instagram_handle(payload.instagram_handle)
        phone_number = normalize_phone_number(payload.phone_number)
        stereotype = enforce_allowed_stereotype(payload.stereotype)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    interests_csv, interests_norm = encode_interests(interests)
    created_at = now_iso()
    first_name = normalize_name(payload.first_name)
    last_name = normalize_name(payload.last_name)
    hometown = payload.hometown.strip()
    hometown_state_code = resolve_pnm_state_code(hometown, payload.state)
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
                hometown_state_code,
                phone_number,
                instagram_handle,
                first_event_date,
                interests,
                interests_norm,
                stereotype,
                lunch_stats,
                notes,
                created_by,
                created_at,
                updated_at
            )
            VALUES ('TBD', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                first_name,
                last_name,
                payload.class_year,
                hometown,
                hometown_state_code,
                phone_number,
                instagram_handle,
                payload.first_event_date,
                interests_csv,
                interests_norm,
                stereotype,
                payload.lunch_stats.strip(),
                payload.notes.strip(),
                user["id"],
                created_at,
                created_at,
            ),
        )
        pnm_id = int(cursor.lastrowid)

        base = pnm_code_base(first_name, last_name, payload.first_event_date)
        code = ensure_unique_pnm_code(conn, pnm_id, base)
        conn.execute("UPDATE pnms SET pnm_code = ?, updated_at = ? WHERE id = ?", (code, now_iso(), pnm_id))

        if payload.auto_photo_from_instagram:
            fetched_photo = try_fetch_instagram_profile_photo(instagram_handle)
            if fetched_photo:
                photo_bytes, extension = fetched_photo
                try:
                    public_path, target_path = write_pnm_photo_bytes(pnm_id, photo_bytes, extension)
                except OSError:
                    public_path = None
                    target_path = None
                if public_path and target_path:
                    try:
                        now = now_iso()
                        conn.execute(
                            """
                            UPDATE pnms
                            SET photo_path = ?, photo_uploaded_at = ?, photo_uploaded_by = ?, updated_at = ?
                            WHERE id = ?
                            """,
                            (public_path, now, user["id"], now, pnm_id),
                        )
                    except Exception:
                        target_path.unlink(missing_ok=True)
                        raise

        evaluate_weekly_goal_completions(conn)
        row = conn.execute("SELECT * FROM pnms WHERE id = ?", (pnm_id,)).fetchone()
        links_by_pnm = fetch_assignment_links_for_pnms(conn, pnm_ids=[pnm_id])

    return {"pnm": pnm_payload_with_assignment_links(conn, row, own_rating=None, links_by_pnm=links_by_pnm)}


@app.get("/api/pnms")
def list_pnms(
    interest: str | None = None,
    stereotype: str | None = None,
    state: str | None = None,
    user: sqlite3.Row = Depends(current_user),
) -> dict[str, Any]:
    try:
        interest_filter = parse_interest_filter(interest)
        state_filter = parse_state_filter(state)
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
        links_by_pnm = fetch_assignment_links_for_pnms(
            conn,
            pnm_ids=[int(row["id"]) for row in rows],
        )
        filtered = []
        for row in rows:
            if normalized_stereotype and row["stereotype"].lower() != normalized_stereotype:
                continue
            if not has_interest_match(row["interests_norm"], interest_filter):
                continue
            if state_filter:
                hometown_state_code = pnm_state_code_for_row(row)
                if hometown_state_code != state_filter:
                    continue
            filtered.append(
                pnm_payload(
                    row,
                    own_rating_by_pnm.get(row["id"]),
                    assigned_officer=assigned_officer_payload_from_row(row),
                    assigned_officers=links_by_pnm.get(int(row["id"]), []),
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
        links_by_pnm = fetch_assignment_links_for_pnms(conn, pnm_ids=[pnm_id])
    return {"pnm": pnm_payload_with_assignment_links(conn, row, own, links_by_pnm)}


@app.patch("/api/pnms/{pnm_id}")
def update_pnm_details(
    pnm_id: int,
    payload: PNMUpdateRequest,
    head_user: sqlite3.Row = Depends(require_head),
) -> dict[str, Any]:
    if (
        payload.first_name is None
        and payload.last_name is None
        and payload.class_year is None
        and payload.hometown is None
        and payload.state is None
        and payload.phone_number is None
        and payload.instagram_handle is None
        and payload.first_event_date is None
        and payload.interests is None
        and payload.stereotype is None
        and payload.lunch_stats is None
        and payload.notes is None
    ):
        raise HTTPException(status_code=400, detail="No PNM changes provided.")

    with db_session() as conn:
        row = conn.execute("SELECT * FROM pnms WHERE id = ?", (pnm_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="PNM not found.")

        first_name = normalize_name(payload.first_name) if payload.first_name is not None else row["first_name"]
        last_name = normalize_name(payload.last_name) if payload.last_name is not None else row["last_name"]
        class_year = payload.class_year if payload.class_year is not None else row["class_year"]
        hometown = payload.hometown.strip() if payload.hometown is not None else row["hometown"]
        existing_state_code = resolve_pnm_state_code(
            row["hometown"],
            row["hometown_state_code"] if "hometown_state_code" in row.keys() else None,
        )
        if payload.state is not None:
            hometown_state_code = resolve_pnm_state_code(hometown, payload.state)
        elif payload.hometown is not None:
            hometown_state_code = resolve_pnm_state_code(hometown)
        else:
            hometown_state_code = existing_state_code
        phone_number_raw = payload.phone_number if payload.phone_number is not None else row["phone_number"]
        instagram_raw = payload.instagram_handle if payload.instagram_handle is not None else row["instagram_handle"]
        first_event_date = payload.first_event_date if payload.first_event_date is not None else row["first_event_date"]
        stereotype = row["stereotype"]
        lunch_stats = payload.lunch_stats.strip() if payload.lunch_stats is not None else row["lunch_stats"]
        notes = payload.notes.strip() if payload.notes is not None else row["notes"]

        if not hometown:
            raise HTTPException(status_code=400, detail="Hometown cannot be empty.")
        if payload.stereotype is not None:
            try:
                stereotype = enforce_allowed_stereotype(payload.stereotype)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        elif not stereotype:
            raise HTTPException(status_code=400, detail="Stereotype cannot be empty.")

        try:
            instagram_handle = normalize_instagram_handle(instagram_raw)
            phone_number = normalize_phone_number(phone_number_raw)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        interests_csv = row["interests"]
        interests_norm = row["interests_norm"]
        if payload.interests is not None:
            try:
                interests = enforce_allowed_interests(parse_interests(payload.interests))
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            interests_csv, interests_norm = encode_interests(interests)

        pnm_code = row["pnm_code"]
        if (
            first_name != row["first_name"]
            or last_name != row["last_name"]
            or first_event_date != row["first_event_date"]
        ):
            base = pnm_code_base(first_name, last_name, first_event_date)
            pnm_code = ensure_unique_pnm_code(conn, pnm_id, base)

        conn.execute(
            """
            UPDATE pnms
            SET
                pnm_code = ?,
                first_name = ?,
                last_name = ?,
                class_year = ?,
                hometown = ?,
                hometown_state_code = ?,
                phone_number = ?,
                instagram_handle = ?,
                first_event_date = ?,
                interests = ?,
                interests_norm = ?,
                stereotype = ?,
                lunch_stats = ?,
                notes = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                pnm_code,
                first_name,
                last_name,
                class_year,
                hometown,
                hometown_state_code,
                phone_number,
                instagram_handle,
                first_event_date,
                interests_csv,
                interests_norm,
                stereotype,
                lunch_stats,
                notes,
                now_iso(),
                pnm_id,
            ),
        )
        existing_photo_path = row["photo_path"] if "photo_path" in row.keys() else None
        if not has_local_photo_file(existing_photo_path):
            fetched_photo = try_fetch_instagram_profile_photo(instagram_handle)
            if fetched_photo:
                photo_bytes, extension = fetched_photo
                try:
                    public_path, target_path = write_pnm_photo_bytes(pnm_id, photo_bytes, extension)
                except OSError:
                    public_path = None
                    target_path = None
                if public_path and target_path:
                    try:
                        now = now_iso()
                        conn.execute(
                            """
                            UPDATE pnms
                            SET photo_path = ?, photo_uploaded_at = ?, photo_uploaded_by = ?, updated_at = ?
                            WHERE id = ?
                            """,
                            (public_path, now, head_user["id"], now, pnm_id),
                        )
                    except Exception:
                        target_path.unlink(missing_ok=True)
                        raise
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
        links_by_pnm = fetch_assignment_links_for_pnms(conn, pnm_ids=[pnm_id])

    return {
        "message": "PNM details updated.",
        "pnm": pnm_payload_with_assignment_links(conn, refreshed, own, links_by_pnm),
    }


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
            officer = resolve_assignable_officer_or_400(conn, assigned_user_id)
        else:
            officer = None

        now = now_iso()
        package_group_id = normalize_package_group_id(pnm_row["package_group_id"])
        target_rows = assignment_target_rows_for_pnm(
            conn,
            pnm_id=pnm_id,
            package_group_id=package_group_id,
        )
        if not target_rows:
            raise HTTPException(status_code=404, detail="PNM not found.")
        affected_pnm_ids: list[int] = []
        changed_assignment_count = 0

        old_assigned_id = int(pnm_row["assigned_officer_id"]) if pnm_row["assigned_officer_id"] is not None else None
        old_status = str(pnm_row["assignment_status"]).strip().lower() if "assignment_status" in pnm_row.keys() else "unassigned"
        if old_status not in ASSIGNMENT_STATUSES:
            old_status = "assigned" if old_assigned_id else "unassigned"
        next_status = old_status

        for target_row in target_rows:
            target_pnm_id = int(target_row["id"])
            previous_assigned = int(target_row["assigned_officer_id"]) if target_row["assigned_officer_id"] is not None else None
            previous_status = str(target_row["assignment_status"] or "").strip().lower()
            if previous_status not in ASSIGNMENT_STATUSES:
                previous_status = "assigned" if previous_assigned else "unassigned"
            assigned_by_value = head_user["id"] if assigned_user_id is not None else None
            assigned_at_value = now if assigned_user_id is not None else None

            if assigned_user_id is None:
                current_status = "unassigned"
            elif previous_assigned == assigned_user_id and previous_status in ASSIGNMENT_STATUSES:
                current_status = previous_status
            else:
                current_status = "assigned"
            if target_pnm_id == pnm_id:
                next_status = current_status

            conn.execute(
                """
                UPDATE pnms
                SET
                    assigned_officer_id = ?,
                    assigned_by = ?,
                    assigned_at = ?,
                    assignment_status = ?,
                    assignment_updated_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    assigned_user_id,
                    assigned_by_value,
                    assigned_at_value,
                    current_status,
                    now,
                    now,
                    target_pnm_id,
                ),
            )
            sync_primary_assignment_links_for_pnm(
                conn,
                pnm_id=target_pnm_id,
                primary_officer_user_id=assigned_user_id,
                assigned_by=assigned_by_value,
                assigned_at=assigned_at_value,
                updated_at=now,
                clear_all_if_unassigned=True,
            )
            if assigned_user_id != previous_assigned:
                changed_assignment_count += 1
            affected_pnm_ids.append(target_pnm_id)

        append_audit_entry(
            conn,
            actor_user_id=int(head_user["id"]),
            action_type="assignment_change",
            entity_type="pnm",
            entity_id=pnm_id,
            payload={
                "old_assigned_officer_id": old_assigned_id,
                "new_assigned_officer_id": assigned_user_id,
                "old_status": old_status,
                "new_status": next_status,
                "package_group_id": package_group_id or None,
                "affected_pnm_ids": affected_pnm_ids,
            },
        )
        if assigned_user_id is not None and changed_assignment_count > 0:
            notification_title = (
                f"Package Assignment ({len(affected_pnm_ids)}): {pnm_row['first_name']} {pnm_row['last_name']}"
                if len(affected_pnm_ids) > 1
                else f"New Assignment: {pnm_row['first_name']} {pnm_row['last_name']}"
            )
            notification_body = (
                f"Assigned by {head_user['username']} (package deal synced)."
                if len(affected_pnm_ids) > 1
                else f"Assigned by {head_user['username']}"
            )
            create_notification(
                conn,
                user_id=assigned_user_id,
                notif_type="assignment",
                title=notification_title,
                body=notification_body,
                link_path=f"/?pnm={pnm_id}",
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
        links_by_pnm = fetch_assignment_links_for_pnms(conn, pnm_ids=[pnm_id])

    affected_count = len(affected_pnm_ids)
    return {
        "message": (
            f"PNM assignment updated for {affected_count} linked rushee(s)."
            if affected_count > 1
            else "PNM assignment updated."
        ),
        "affected_pnm_ids": affected_pnm_ids,
        "package_group_id": package_group_id or None,
        "pnm": pnm_payload_with_assignment_links(conn, refreshed, own, links_by_pnm),
    }


@app.post("/api/pnms/{pnm_id}/assignees")
def add_pnm_assignee(
    pnm_id: int,
    payload: PnmAssigneeCreateRequest,
    head_user: sqlite3.Row = Depends(require_head),
) -> dict[str, Any]:
    with db_session() as conn:
        ensure_package_link_schema(conn)
        officer = resolve_assignable_officer_or_400(conn, payload.officer_user_id)
        pnm_row = conn.execute("SELECT * FROM pnms WHERE id = ?", (pnm_id,)).fetchone()
        if not pnm_row:
            raise HTTPException(status_code=404, detail="PNM not found.")

        package_group_id = normalize_package_group_id(pnm_row["package_group_id"])
        target_rows = assignment_target_rows_for_pnm(
            conn,
            pnm_id=pnm_id,
            package_group_id=package_group_id if payload.include_package else None,
        )
        if not target_rows:
            raise HTTPException(status_code=404, detail="PNM not found.")

        now = now_iso()
        affected_pnm_ids: list[int] = []
        added_links = 0
        promoted_to_primary = 0

        for target_row in target_rows:
            target_pnm_id = int(target_row["id"])
            target_primary_id = int(target_row["assigned_officer_id"]) if target_row["assigned_officer_id"] is not None else None
            existing_link = conn.execute(
                """
                SELECT id
                FROM pnm_officer_assignments
                WHERE pnm_id = ? AND officer_user_id = ?
                """,
                (target_pnm_id, int(officer["id"])),
            ).fetchone()
            if existing_link is None:
                added_links += 1

            if target_primary_id is None:
                conn.execute(
                    """
                    UPDATE pnms
                    SET
                        assigned_officer_id = ?,
                        assigned_by = ?,
                        assigned_at = ?,
                        assignment_status = 'assigned',
                        assignment_updated_at = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        int(officer["id"]),
                        int(head_user["id"]),
                        now,
                        now,
                        now,
                        target_pnm_id,
                    ),
                )
                sync_primary_assignment_links_for_pnm(
                    conn,
                    pnm_id=target_pnm_id,
                    primary_officer_user_id=int(officer["id"]),
                    assigned_by=int(head_user["id"]),
                    assigned_at=now,
                    updated_at=now,
                    clear_all_if_unassigned=False,
                )
                promoted_to_primary += 1
            elif target_primary_id == int(officer["id"]):
                sync_primary_assignment_links_for_pnm(
                    conn,
                    pnm_id=target_pnm_id,
                    primary_officer_user_id=int(officer["id"]),
                    assigned_by=int(target_row["assigned_by"]) if target_row["assigned_by"] is not None else int(head_user["id"]),
                    assigned_at=target_row["assigned_at"] or now,
                    updated_at=now,
                    clear_all_if_unassigned=False,
                )
            else:
                add_officer_assignment_link(
                    conn,
                    pnm_id=target_pnm_id,
                    officer_user_id=int(officer["id"]),
                    assigned_by=int(head_user["id"]),
                    assigned_at=now,
                )
                sync_primary_assignment_links_for_pnm(
                    conn,
                    pnm_id=target_pnm_id,
                    primary_officer_user_id=target_primary_id,
                    assigned_by=int(target_row["assigned_by"]) if target_row["assigned_by"] is not None else int(head_user["id"]),
                    assigned_at=target_row["assigned_at"] or now,
                    updated_at=now,
                    clear_all_if_unassigned=False,
                )

            affected_pnm_ids.append(target_pnm_id)

        append_audit_entry(
            conn,
            actor_user_id=int(head_user["id"]),
            action_type="assignment_add_assignee",
            entity_type="pnm",
            entity_id=pnm_id,
            payload={
                "officer_user_id": int(officer["id"]),
                "include_package": bool(payload.include_package),
                "package_group_id": package_group_id or None,
                "affected_pnm_ids": affected_pnm_ids,
                "added_links": added_links,
                "promoted_to_primary": promoted_to_primary,
            },
        )
        if payload.notify_officer and added_links > 0:
            create_notification(
                conn,
                user_id=int(officer["id"]),
                notif_type="assignment",
                title=f"Added to assignment: {pnm_row['first_name']} {pnm_row['last_name']}",
                body=f"Added by {head_user['username']}",
                link_path=f"/?pnm={pnm_id}",
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
        links_by_pnm = fetch_assignment_links_for_pnms(conn, pnm_ids=[pnm_id])

    if added_links <= 0:
        message = f"{officer['username']} is already on this assignment team."
    else:
        message = (
            f"Added {officer['username']} to {added_links} rushee assignment team(s)."
            + (" Package-linked rushees were updated." if payload.include_package and len(affected_pnm_ids) > 1 else "")
        )

    return {
        "message": message,
        "affected_pnm_ids": affected_pnm_ids,
        "package_group_id": package_group_id or None,
        "added_links": added_links,
        "promoted_to_primary": promoted_to_primary,
        "pnm": pnm_payload_with_assignment_links(conn, refreshed, own, links_by_pnm),
    }


@app.delete("/api/pnms/{pnm_id}/assignees/{officer_user_id}")
def remove_pnm_assignee(
    pnm_id: int,
    officer_user_id: int,
    include_package: bool = False,
    head_user: sqlite3.Row = Depends(require_head),
) -> dict[str, Any]:
    target_officer_id = int(officer_user_id)
    if target_officer_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid officer id.")

    with db_session() as conn:
        ensure_package_link_schema(conn)
        pnm_row = conn.execute("SELECT * FROM pnms WHERE id = ?", (pnm_id,)).fetchone()
        if not pnm_row:
            raise HTTPException(status_code=404, detail="PNM not found.")

        package_group_id = normalize_package_group_id(pnm_row["package_group_id"])
        target_rows = assignment_target_rows_for_pnm(
            conn,
            pnm_id=pnm_id,
            package_group_id=package_group_id if include_package else None,
        )
        if not target_rows:
            raise HTTPException(status_code=404, detail="PNM not found.")

        now = now_iso()
        affected_pnm_ids: list[int] = []
        removed_links = 0
        promoted_count = 0
        cleared_count = 0

        for target_row in target_rows:
            target_pnm_id = int(target_row["id"])
            primary_id = int(target_row["assigned_officer_id"]) if target_row["assigned_officer_id"] is not None else None
            link_exists = conn.execute(
                """
                SELECT id
                FROM pnm_officer_assignments
                WHERE pnm_id = ? AND officer_user_id = ?
                """,
                (target_pnm_id, target_officer_id),
            ).fetchone()
            is_primary = primary_id == target_officer_id
            if not link_exists and not is_primary:
                continue

            conn.execute(
                "DELETE FROM pnm_officer_assignments WHERE pnm_id = ? AND officer_user_id = ?",
                (target_pnm_id, target_officer_id),
            )

            if is_primary:
                fallback = conn.execute(
                    """
                    SELECT pa.officer_user_id, pa.assigned_by, pa.assigned_at
                    FROM pnm_officer_assignments pa
                    JOIN users u ON u.id = pa.officer_user_id
                    WHERE pa.pnm_id = ?
                      AND u.is_approved = 1
                      AND u.role = ?
                    ORDER BY
                        pa.is_primary DESC,
                        COALESCE(pa.assigned_at, pa.created_at, pa.updated_at) ASC,
                        pa.id ASC
                    LIMIT 1
                    """,
                    (target_pnm_id, ROLE_RUSH_OFFICER),
                ).fetchone()
                if fallback:
                    fallback_user_id = int(fallback["officer_user_id"])
                    fallback_assigned_by = (
                        int(fallback["assigned_by"]) if fallback["assigned_by"] is not None else int(head_user["id"])
                    )
                    fallback_assigned_at = fallback["assigned_at"] or now
                    next_status = str(target_row["assignment_status"] or "").strip().lower()
                    if next_status not in ASSIGNMENT_STATUSES or next_status == "unassigned":
                        next_status = "assigned"
                    conn.execute(
                        """
                        UPDATE pnms
                        SET
                            assigned_officer_id = ?,
                            assigned_by = ?,
                            assigned_at = ?,
                            assignment_status = ?,
                            assignment_updated_at = ?,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            fallback_user_id,
                            fallback_assigned_by,
                            fallback_assigned_at,
                            next_status,
                            now,
                            now,
                            target_pnm_id,
                        ),
                    )
                    sync_primary_assignment_links_for_pnm(
                        conn,
                        pnm_id=target_pnm_id,
                        primary_officer_user_id=fallback_user_id,
                        assigned_by=fallback_assigned_by,
                        assigned_at=fallback_assigned_at,
                        updated_at=now,
                        clear_all_if_unassigned=False,
                    )
                    promoted_count += 1
                else:
                    conn.execute(
                        """
                        UPDATE pnms
                        SET
                            assigned_officer_id = NULL,
                            assigned_by = NULL,
                            assigned_at = NULL,
                            assignment_status = 'unassigned',
                            assignment_due_date = NULL,
                            assignment_updated_at = ?,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (now, now, target_pnm_id),
                    )
                    sync_primary_assignment_links_for_pnm(
                        conn,
                        pnm_id=target_pnm_id,
                        primary_officer_user_id=None,
                        assigned_by=None,
                        assigned_at=None,
                        updated_at=now,
                        clear_all_if_unassigned=True,
                    )
                    cleared_count += 1
            else:
                if primary_id is not None:
                    sync_primary_assignment_links_for_pnm(
                        conn,
                        pnm_id=target_pnm_id,
                        primary_officer_user_id=primary_id,
                        assigned_by=int(target_row["assigned_by"]) if target_row["assigned_by"] is not None else int(head_user["id"]),
                        assigned_at=target_row["assigned_at"] or now,
                        updated_at=now,
                        clear_all_if_unassigned=False,
                    )

            removed_links += 1
            affected_pnm_ids.append(target_pnm_id)

        if removed_links <= 0:
            raise HTTPException(status_code=404, detail="Officer is not assigned to this rushee.")

        append_audit_entry(
            conn,
            actor_user_id=int(head_user["id"]),
            action_type="assignment_remove_assignee",
            entity_type="pnm",
            entity_id=pnm_id,
            payload={
                "officer_user_id": target_officer_id,
                "include_package": bool(include_package),
                "package_group_id": package_group_id or None,
                "affected_pnm_ids": affected_pnm_ids,
                "removed_links": removed_links,
                "promoted_count": promoted_count,
                "cleared_count": cleared_count,
            },
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
        links_by_pnm = fetch_assignment_links_for_pnms(conn, pnm_ids=[pnm_id])

    return {
        "message": f"Removed officer from {removed_links} assignment team(s).",
        "affected_pnm_ids": affected_pnm_ids,
        "package_group_id": package_group_id or None,
        "removed_links": removed_links,
        "promoted_count": promoted_count,
        "cleared_count": cleared_count,
        "pnm": pnm_payload_with_assignment_links(conn, refreshed, own, links_by_pnm),
    }


@app.post("/api/pnms/package/link")
def link_pnms_package_deal(
    payload: PnmPackageLinkRequest,
    user: sqlite3.Row = Depends(current_user),
) -> dict[str, Any]:
    requested_pnm_ids = sorted({int(item) for item in payload.pnm_ids if int(item) > 0})
    if len(requested_pnm_ids) < 2:
        raise HTTPException(status_code=400, detail="Select at least two rushees to link.")
    selected_placeholders = ",".join(["?"] * len(requested_pnm_ids))

    with db_session() as conn:
        ensure_package_link_schema(conn)
        selected_rows = conn.execute(
            f"SELECT * FROM pnms WHERE id IN ({selected_placeholders})",
            tuple(requested_pnm_ids),
        ).fetchall()
        selected_by_id: dict[int, sqlite3.Row] = {int(row["id"]): row for row in selected_rows}
        missing_ids = [pnm_id for pnm_id in requested_pnm_ids if pnm_id not in selected_by_id]
        if missing_ids:
            raise HTTPException(status_code=404, detail=f"PNM not found: {missing_ids[0]}")

        existing_group_ids = sorted(
            {
                group_id
                for group_id in (normalize_package_group_id(row["package_group_id"]) for row in selected_rows)
                if group_id
            }
        )
        linked_pnm_ids: set[int] = set(requested_pnm_ids)
        if existing_group_ids:
            group_placeholders = ",".join(["?"] * len(existing_group_ids))
            grouped_rows = conn.execute(
                f"""
                SELECT id
                FROM pnms
                WHERE package_group_id IN ({group_placeholders})
                """,
                tuple(existing_group_ids),
            ).fetchall()
            linked_pnm_ids.update(int(row["id"]) for row in grouped_rows)

        target_pnm_ids = sorted(linked_pnm_ids)
        target_placeholders = ",".join(["?"] * len(target_pnm_ids))
        target_rows = conn.execute(
            f"SELECT * FROM pnms WHERE id IN ({target_placeholders})",
            tuple(target_pnm_ids),
        ).fetchall()
        target_by_id: dict[int, sqlite3.Row] = {int(row["id"]): row for row in target_rows}

        package_group_id = new_package_group_id()
        now = now_iso()
        conn.execute(
            f"""
            UPDATE pnms
            SET package_group_id = ?, updated_at = ?
            WHERE id IN ({target_placeholders})
            """,
            (package_group_id, now, *target_pnm_ids),
        )

        assignment_synced = False
        synced_officer_id: int | None = None
        synced_status = "unassigned"
        if payload.sync_assignment and target_pnm_ids:
            template_row = next(
                (
                    selected_by_id[pnm_id]
                    for pnm_id in requested_pnm_ids
                    if selected_by_id[pnm_id]["assigned_officer_id"] is not None
                ),
                selected_by_id[requested_pnm_ids[0]],
            )
            synced_officer_id = (
                int(template_row["assigned_officer_id"]) if template_row["assigned_officer_id"] is not None else None
            )
            template_status = str(template_row["assignment_status"] or "").strip().lower()
            if template_status not in ASSIGNMENT_STATUSES:
                template_status = "assigned" if synced_officer_id is not None else "unassigned"
            if synced_officer_id is None:
                template_status = "unassigned"
            template_pnm_id = int(template_row["id"])
            template_links = fetch_assignment_links_for_pnms(conn, pnm_ids=[template_pnm_id]).get(template_pnm_id, [])
            template_secondary_officer_ids = [
                int(item["user_id"])
                for item in template_links
                if int(item.get("user_id") or 0) > 0 and int(item["user_id"]) != int(synced_officer_id or 0)
            ]
            synced_status = template_status
            priority = clamped_assignment_priority(
                int(template_row["assignment_priority"]) if template_row["assignment_priority"] is not None else None
            )
            due_date = template_row["assignment_due_date"] if synced_officer_id is not None else None
            notes = (template_row["assignment_notes"] or "").strip()

            for target_id in target_pnm_ids:
                target_row = target_by_id[target_id]
                previous_assigned = (
                    int(target_row["assigned_officer_id"]) if target_row["assigned_officer_id"] is not None else None
                )
                previous_status = str(target_row["assignment_status"] or "").strip().lower()
                if previous_status not in ASSIGNMENT_STATUSES:
                    previous_status = "assigned" if previous_assigned is not None else "unassigned"
                if synced_officer_id is None:
                    next_status = "unassigned"
                elif previous_assigned != synced_officer_id:
                    next_status = "assigned"
                else:
                    next_status = template_status
                if next_status not in ASSIGNMENT_STATUSES:
                    next_status = "assigned" if synced_officer_id is not None else "unassigned"

                assigned_by = target_row["assigned_by"]
                assigned_at = target_row["assigned_at"]
                if synced_officer_id is None:
                    assigned_by = None
                    assigned_at = None
                elif previous_assigned != synced_officer_id:
                    assigned_by = user["id"]
                    assigned_at = now

                conn.execute(
                    """
                    UPDATE pnms
                    SET
                        assigned_officer_id = ?,
                        assigned_by = ?,
                        assigned_at = ?,
                        assignment_status = ?,
                        assignment_priority = ?,
                        assignment_due_date = ?,
                        assignment_notes = ?,
                        assignment_updated_at = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        synced_officer_id,
                        assigned_by,
                        assigned_at,
                        next_status,
                        priority,
                        due_date,
                        notes,
                        now,
                        now,
                        target_id,
                    ),
                )
                sync_primary_assignment_links_for_pnm(
                    conn,
                    pnm_id=target_id,
                    primary_officer_user_id=synced_officer_id,
                    assigned_by=assigned_by,
                    assigned_at=assigned_at,
                    updated_at=now,
                    clear_all_if_unassigned=True,
                )
                if synced_officer_id is not None:
                    for extra_officer_id in template_secondary_officer_ids:
                        add_officer_assignment_link(
                            conn,
                            pnm_id=target_id,
                            officer_user_id=extra_officer_id,
                            assigned_by=int(user["id"]),
                            assigned_at=now,
                        )
            assignment_synced = True

        append_audit_entry(
            conn,
            actor_user_id=int(user["id"]),
            action_type="pnm_package_link",
            entity_type="pnm_package",
            entity_id=requested_pnm_ids[0] if requested_pnm_ids else None,
            payload={
                "requested_pnm_ids": requested_pnm_ids,
                "linked_pnm_ids": target_pnm_ids,
                "package_group_id": package_group_id,
                "sync_assignment": bool(payload.sync_assignment),
                "synced_officer_id": synced_officer_id,
                "synced_status": synced_status,
                "merged_existing_group_ids": existing_group_ids,
            },
        )

        refreshed_rows = conn.execute(
            f"""
            SELECT
                p.*,
                ao.id AS assigned_officer_id,
                ao.username AS assigned_officer_username,
                ao.role AS assigned_officer_role,
                ao.emoji AS assigned_officer_emoji
            FROM pnms p
            LEFT JOIN users ao ON ao.id = p.assigned_officer_id
            WHERE p.id IN ({target_placeholders})
            ORDER BY p.last_name ASC, p.first_name ASC
            """,
            tuple(target_pnm_ids),
        ).fetchall()
        links_by_pnm = fetch_assignment_links_for_pnms(conn, pnm_ids=target_pnm_ids)

    merged_count = max(0, len(target_pnm_ids) - len(requested_pnm_ids))
    return {
        "message": (
            f"Linked {len(target_pnm_ids)} rushees into package deal {package_group_label(package_group_id)}."
            + (f" Merged {merged_count} existing linked rushee(s)." if merged_count else "")
            + (" Assignment settings were synced." if assignment_synced else "")
        ),
        "package_group_id": package_group_id,
        "package_group_label": package_group_label(package_group_id),
        "linked_count": len(target_pnm_ids),
        "linked_pnm_ids": target_pnm_ids,
        "requested_pnm_ids": requested_pnm_ids,
        "assignment_synced": assignment_synced,
        "pnms": [
            pnm_payload(
                row,
                own_rating=None,
                assigned_officer=assigned_officer_payload_from_row(row),
                assigned_officers=links_by_pnm.get(int(row["id"]), []),
            )
            for row in refreshed_rows
        ],
    }


@app.post("/api/pnms/{pnm_id}/package/unlink")
def unlink_pnm_package_deal(
    pnm_id: int,
    user: sqlite3.Row = Depends(current_user),
) -> dict[str, Any]:
    with db_session() as conn:
        ensure_package_link_schema(conn)
        row = conn.execute(
            "SELECT id, first_name, last_name, package_group_id FROM pnms WHERE id = ?",
            (pnm_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="PNM not found.")

        package_group_id = normalize_package_group_id(row["package_group_id"])
        if not package_group_id:
            return {
                "message": "PNM is not currently linked in a package deal.",
                "package_group_id": None,
                "affected_pnm_ids": [pnm_id],
            }

        member_rows = conn.execute(
            """
            SELECT id
            FROM pnms
            WHERE package_group_id = ?
            ORDER BY id ASC
            """,
            (package_group_id,),
        ).fetchall()
        member_ids = [int(item["id"]) for item in member_rows]
        now = now_iso()
        conn.execute(
            "UPDATE pnms SET package_group_id = NULL, updated_at = ? WHERE id = ?",
            (now, pnm_id),
        )
        affected_pnm_ids = [pnm_id]
        collapsed_group = False

        remaining_ids = [item for item in member_ids if item != pnm_id]
        if len(remaining_ids) == 1:
            conn.execute(
                "UPDATE pnms SET package_group_id = NULL, updated_at = ? WHERE id = ?",
                (now, remaining_ids[0]),
            )
            affected_pnm_ids.append(remaining_ids[0])
            collapsed_group = True

        append_audit_entry(
            conn,
            actor_user_id=int(user["id"]),
            action_type="pnm_package_unlink",
            entity_type="pnm_package",
            entity_id=pnm_id,
            payload={
                "package_group_id": package_group_id,
                "affected_pnm_ids": affected_pnm_ids,
                "collapsed_group": collapsed_group,
            },
        )

    return {
        "message": (
            f"Removed {row['first_name']} {row['last_name']} from package deal {package_group_label(package_group_id)}."
            + (" Remaining single-member package was cleared." if collapsed_group else "")
        ),
        "package_group_id": package_group_id,
        "package_group_label": package_group_label(package_group_id),
        "affected_pnm_ids": affected_pnm_ids,
    }


@app.get("/api/assignments/overview")
def assignments_overview(
    include_completed: bool = True,
    user: sqlite3.Row = Depends(require_officer),
) -> dict[str, Any]:
    with db_session() as conn:
        if user["role"] == ROLE_HEAD:
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
                ORDER BY
                    CASE
                        WHEN p.assignment_status = 'needs_help' THEN 0
                        WHEN p.assignment_status = 'in_progress' THEN 1
                        WHEN p.assignment_status = 'assigned' THEN 2
                        WHEN p.assignment_status = 'unassigned' THEN 3
                        ELSE 4
                    END ASC,
                    p.assignment_priority DESC,
                    p.weighted_total DESC,
                    p.last_name ASC,
                    p.first_name ASC
                """
            ).fetchall()
        else:
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
                WHERE
                    p.assigned_officer_id IS NULL
                    OR p.assigned_officer_id = ?
                    OR EXISTS (
                        SELECT 1
                        FROM pnm_officer_assignments pa
                        WHERE pa.pnm_id = p.id
                          AND pa.officer_user_id = ?
                    )
                ORDER BY
                    CASE
                        WHEN p.assignment_status = 'needs_help' THEN 0
                        WHEN p.assignment_status = 'in_progress' THEN 1
                        WHEN p.assignment_status = 'assigned' THEN 2
                        WHEN p.assignment_status = 'unassigned' THEN 3
                        ELSE 4
                    END ASC,
                    p.assignment_priority DESC,
                    p.weighted_total DESC,
                    p.last_name ASC,
                    p.first_name ASC
                """,
                (user["id"], user["id"]),
            ).fetchall()
        links_by_pnm = fetch_assignment_links_for_pnms(
            conn,
            pnm_ids=[int(row["id"]) for row in pnm_rows],
        )

        officer_rows = conn.execute(
            """
            SELECT
                u.id,
                u.username,
                u.role,
                u.emoji,
                u.stereotype,
                u.interests_norm,
                COUNT(p.id) AS total_assigned,
                SUM(CASE WHEN p.assignment_status IN ('assigned', 'in_progress', 'needs_help') THEN 1 ELSE 0 END) AS active_assignments,
                SUM(CASE WHEN p.assignment_status = 'completed' THEN 1 ELSE 0 END) AS completed_assignments
            FROM users u
            LEFT JOIN pnms p ON p.assigned_officer_id = u.id
            WHERE u.is_approved = 1 AND u.role = ?
            GROUP BY u.id, u.username, u.role, u.emoji, u.stereotype, u.interests_norm
            ORDER BY active_assignments ASC, total_assigned ASC, u.username ASC
            """,
            (ROLE_RUSH_OFFICER,),
        ).fetchall()

    assignments: list[dict[str, Any]] = []
    status_counts = {status_key: 0 for status_key in ASSIGNMENT_STATUSES}
    due_counts = {"none": 0, "done": 0, "overdue": 0, "due_soon": 0, "upcoming": 0}
    escalation_rows: list[dict[str, Any]] = []
    unassigned_rows: list[sqlite3.Row] = []
    for row in pnm_rows:
        status_token = str(row["assignment_status"] or "").strip().lower()
        if status_token not in ASSIGNMENT_STATUSES:
            status_token = "assigned" if row["assigned_officer_id"] else "unassigned"
        due_state = assignment_due_state(status_token, row["assignment_due_date"])
        if not include_completed and status_token == "completed":
            continue
        status_counts[status_token] += 1
        due_counts[due_state] = int(due_counts.get(due_state, 0)) + 1
        if status_token in {"needs_help"} or due_state in {"overdue", "due_soon"}:
            escalation_rows.append(
                {
                    "pnm_id": int(row["id"]),
                    "pnm_code": row["pnm_code"],
                    "name": f"{row['first_name']} {row['last_name']}",
                    "assignment_status": status_token,
                    "assignment_due_state": due_state,
                    "assignment_due_date": row["assignment_due_date"],
                    "assigned_officer_username": row["assigned_officer_username"] or "",
                    "package_group_id": normalize_package_group_id(row["package_group_id"]) or None,
                    "package_group_label": package_group_label(normalize_package_group_id(row["package_group_id"])),
                    "priority": clamped_assignment_priority(
                        int(row["assignment_priority"]) if row["assignment_priority"] is not None else None
                    ),
                }
            )
        if row["assigned_officer_id"] is None or status_token == "unassigned":
            unassigned_rows.append(row)
        assignments.append(
            {
                "pnm_id": int(row["id"]),
                "pnm_code": row["pnm_code"],
                "name": f"{row['first_name']} {row['last_name']}",
                "weighted_total": round(float(row["weighted_total"]), 2),
                "rating_count": int(row["rating_count"]),
                "total_lunches": int(row["total_lunches"]),
                "assignment_status": status_token,
                "assignment_status_label": ASSIGNMENT_STATUS_LABELS.get(status_token, status_token.title()),
                "assignment_priority": clamped_assignment_priority(
                    int(row["assignment_priority"]) if row["assignment_priority"] is not None else None
                ),
                "assignment_due_date": row["assignment_due_date"],
                "assignment_due_state": due_state,
                "assignment_notes": row["assignment_notes"] or "",
                "assignment_updated_at": row["assignment_updated_at"],
                "funnel_stage": row["funnel_stage"] if "funnel_stage" in row.keys() else "sourced",
                "assigned_officer": assigned_officer_payload_from_row(row),
                "assigned_officers": merge_assigned_officers_for_pnm_row(
                    row,
                    links_by_pnm.get(int(row["id"]), []),
                ),
                "package_group_id": normalize_package_group_id(row["package_group_id"]) or None,
                "package_group_label": package_group_label(normalize_package_group_id(row["package_group_id"])),
                "interests_norm": split_normalized_csv(row["interests_norm"]),
                "stereotype_norm": (row["stereotype"] or "").strip().lower(),
            }
        )

    officer_loads: list[dict[str, Any]] = []
    officer_lookup: list[dict[str, Any]] = []
    for row in officer_rows:
        active_assignments = int(row["active_assignments"] or 0)
        total_assigned = int(row["total_assigned"] or 0)
        completed_assignments = int(row["completed_assignments"] or 0)
        capacity_ratio = round(active_assignments / max(1, OFFICER_CAPACITY_TARGET), 2)
        payload = {
            "user_id": int(row["id"]),
            "username": row["username"],
            "role": row["role"],
            "emoji": row["emoji"],
            "total_assigned": total_assigned,
            "active_assignments": active_assignments,
            "completed_assignments": completed_assignments,
            "capacity_target": OFFICER_CAPACITY_TARGET,
            "capacity_ratio": capacity_ratio,
            "is_over_capacity": active_assignments > OFFICER_CAPACITY_TARGET,
            "remaining_capacity": max(0, OFFICER_CAPACITY_TARGET - active_assignments),
            "stereotype_norm": (row["stereotype"] or "").strip().lower(),
            "interests_norm": split_normalized_csv(row["interests_norm"] or ""),
        }
        officer_loads.append(payload)
        officer_lookup.append(payload)

    recommendations: list[dict[str, Any]] = []
    for pnm_row in sorted(
        unassigned_rows,
        key=lambda item: (
            clamped_assignment_priority(int(item["assignment_priority"]) if item["assignment_priority"] is not None else None) * -1,
            float(item["weighted_total"]) * -1,
            int(item["id"]),
        ),
    )[:24]:
        pnm_interests = split_normalized_csv(pnm_row["interests_norm"] or "")
        pnm_stereotype = (pnm_row["stereotype"] or "").strip().lower()
        ranked_officers: list[tuple[float, dict[str, Any], int, bool]] = []
        for officer in officer_lookup:
            shared_interest_count = len(pnm_interests & officer["interests_norm"])
            stereotype_match = bool(pnm_stereotype and officer["stereotype_norm"] == pnm_stereotype)
            score = (
                shared_interest_count * 3.0
                + (1.25 if stereotype_match else 0.0)
                - officer["active_assignments"] * 0.75
            )
            ranked_officers.append((score, officer, shared_interest_count, stereotype_match))
        ranked_officers.sort(
            key=lambda item: (
                item[0],
                -item[1]["active_assignments"],
                item[1]["username"].lower(),
            ),
            reverse=True,
        )
        top_suggestions = [
            {
                "user_id": candidate["user_id"],
                "username": candidate["username"],
                "role": candidate["role"],
                "emoji": candidate["emoji"],
                "score": round(score, 2),
                "shared_interest_count": shared_count,
                "stereotype_match": stereotype_match,
                "active_assignments": candidate["active_assignments"],
                "capacity_ratio": candidate["capacity_ratio"],
            }
            for score, candidate, shared_count, stereotype_match in ranked_officers[:3]
        ]
        if not top_suggestions:
            continue
        recommendations.append(
            {
                "pnm_id": int(pnm_row["id"]),
                "pnm_code": pnm_row["pnm_code"],
                "name": f"{pnm_row['first_name']} {pnm_row['last_name']}",
                "assignment_priority": clamped_assignment_priority(
                    int(pnm_row["assignment_priority"]) if pnm_row["assignment_priority"] is not None else None
                ),
                "weighted_total": round(float(pnm_row["weighted_total"]), 2),
                "top_suggestions": top_suggestions,
            }
        )

    for assignment in assignments:
        assignment.pop("interests_norm", None)
        assignment.pop("stereotype_norm", None)
    for load in officer_loads:
        load.pop("interests_norm", None)
        load.pop("stereotype_norm", None)

    return {
        "assignments": assignments,
        "status_counts": status_counts,
        "due_counts": due_counts,
        "officer_loads": officer_loads,
        "recommendations": recommendations,
        "escalations": escalation_rows[:40],
        "capacity_target": OFFICER_CAPACITY_TARGET,
    }


@app.get("/api/assignments/mine")
def assignments_mine(
    include_completed: bool = True,
    user: sqlite3.Row = Depends(require_officer),
) -> dict[str, Any]:
    with db_session() as conn:
        if user["role"] == ROLE_HEAD:
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
                WHERE
                    p.assigned_officer_id IS NOT NULL
                    OR EXISTS (SELECT 1 FROM pnm_officer_assignments pa WHERE pa.pnm_id = p.id)
                ORDER BY p.assignment_priority DESC, p.weighted_total DESC, p.last_name ASC, p.first_name ASC
                """
            ).fetchall()
        else:
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
                WHERE
                    EXISTS (
                        SELECT 1
                        FROM pnm_officer_assignments pa
                        WHERE pa.pnm_id = p.id
                          AND pa.officer_user_id = ?
                    )
                    OR (
                        p.assigned_officer_id = ?
                        AND NOT EXISTS (
                            SELECT 1 FROM pnm_officer_assignments pa2 WHERE pa2.pnm_id = p.id
                        )
                    )
                ORDER BY p.assignment_priority DESC, p.weighted_total DESC, p.last_name ASC, p.first_name ASC
                """,
                (int(user["id"]), int(user["id"])),
            ).fetchall()

        links_by_pnm = fetch_assignment_links_for_pnms(
            conn,
            pnm_ids=[int(row["id"]) for row in rows],
        )

    assignments: list[dict[str, Any]] = []
    for row in rows:
        assignment_status = str(row["assignment_status"] or "").strip().lower()
        if assignment_status not in ASSIGNMENT_STATUSES:
            assignment_status = "assigned" if row["assigned_officer_id"] else "unassigned"
        if not include_completed and assignment_status == "completed":
            continue

        assigned_officers = merge_assigned_officers_for_pnm_row(row, links_by_pnm.get(int(row["id"]), []))
        assigned_to_me = any(int(item["user_id"]) == int(user["id"]) for item in assigned_officers)
        if user["role"] != ROLE_HEAD and not assigned_to_me:
            continue

        assignments.append(
            {
                "pnm_id": int(row["id"]),
                "pnm_code": row["pnm_code"],
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "phone_number": row["phone_number"] if "phone_number" in row.keys() else "",
                "weighted_total": round(float(row["weighted_total"]), 2),
                "rating_count": int(row["rating_count"]),
                "total_lunches": int(row["total_lunches"]),
                "assigned_at": row["assigned_at"],
                "assignment_status": assignment_status,
                "assignment_status_label": ASSIGNMENT_STATUS_LABELS.get(assignment_status, assignment_status.title()),
                "assignment_due_date": row["assignment_due_date"],
                "assignment_due_state": assignment_due_state(assignment_status, row["assignment_due_date"]),
                "assignment_priority": clamped_assignment_priority(
                    int(row["assignment_priority"]) if row["assignment_priority"] is not None else None
                ),
                "assigned_officer": assigned_officer_payload_from_row(row),
                "assigned_officers": assigned_officers,
                "assigned_to_me": assigned_to_me,
                "package_group_id": normalize_package_group_id(row["package_group_id"]) or None,
                "package_group_label": package_group_label(normalize_package_group_id(row["package_group_id"])),
            }
        )

    return {
        "assignments": assignments,
        "count": len(assignments),
        "is_head_view": user["role"] == ROLE_HEAD,
        "user_id": int(user["id"]),
        "username": user["username"],
    }


@app.patch("/api/pnms/{pnm_id}/assignment")
def update_pnm_assignment(
    pnm_id: int,
    payload: PnmAssignmentUpdateRequest,
    head_user: sqlite3.Row = Depends(require_head),
) -> dict[str, Any]:
    requested_fields = set(payload.model_fields_set)
    if not requested_fields:
        raise HTTPException(status_code=400, detail="No assignment changes provided.")

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

        old_assigned_officer_id = int(row["assigned_officer_id"]) if row["assigned_officer_id"] is not None else None
        old_status = str(row["assignment_status"] or "").strip().lower()
        if old_status not in ASSIGNMENT_STATUSES:
            old_status = "assigned" if old_assigned_officer_id else "unassigned"
        package_group_id = normalize_package_group_id(row["package_group_id"])
        target_rows = assignment_target_rows_for_pnm(
            conn,
            pnm_id=pnm_id,
            package_group_id=package_group_id,
        )
        if not target_rows:
            raise HTTPException(status_code=404, detail="PNM not found.")

        assigned_officer_id = old_assigned_officer_id
        if "officer_user_id" in requested_fields:
            assigned_officer_id = payload.officer_user_id

        if assigned_officer_id is not None:
            resolve_assignable_officer_or_400(conn, assigned_officer_id)

        if "assignment_status" in requested_fields and payload.assignment_status is not None:
            status_token = payload.assignment_status
        else:
            if assigned_officer_id is None:
                status_token = "unassigned"
            elif old_assigned_officer_id != assigned_officer_id:
                status_token = "assigned"
            else:
                status_token = old_status
        if assigned_officer_id is None:
            status_token = "unassigned"
        if status_token not in ASSIGNMENT_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid assignment status.")

        if "assignment_priority" in requested_fields:
            priority = clamped_assignment_priority(payload.assignment_priority)
        else:
            priority = clamped_assignment_priority(int(row["assignment_priority"]) if row["assignment_priority"] is not None else None)

        if "assignment_due_date" in requested_fields:
            due_date = payload.assignment_due_date
        else:
            due_date = row["assignment_due_date"]
        if assigned_officer_id is None and "assignment_due_date" not in requested_fields:
            due_date = None

        if "assignment_notes" in requested_fields:
            notes = payload.assignment_notes or ""
        else:
            notes = row["assignment_notes"] or ""
        notes = notes.strip()

        now = now_iso()
        affected_pnm_ids: list[int] = []
        officer_changed_for_any = False
        resolved_primary_status = status_token

        for target_row in target_rows:
            target_pnm_id = int(target_row["id"])
            previous_assigned_officer_id = (
                int(target_row["assigned_officer_id"]) if target_row["assigned_officer_id"] is not None else None
            )
            previous_status = str(target_row["assignment_status"] or "").strip().lower()
            if previous_status not in ASSIGNMENT_STATUSES:
                previous_status = "assigned" if previous_assigned_officer_id else "unassigned"

            if "assignment_status" in requested_fields and payload.assignment_status is not None:
                next_status = status_token
            else:
                if assigned_officer_id is None:
                    next_status = "unassigned"
                elif previous_assigned_officer_id != assigned_officer_id:
                    next_status = "assigned"
                else:
                    next_status = previous_status
            if next_status not in ASSIGNMENT_STATUSES:
                next_status = "assigned" if assigned_officer_id is not None else "unassigned"

            assigned_by = target_row["assigned_by"]
            assigned_at = target_row["assigned_at"]
            if assigned_officer_id is None:
                assigned_by = None
                assigned_at = None
            elif previous_assigned_officer_id != assigned_officer_id:
                assigned_by = head_user["id"]
                assigned_at = now

            target_due_date = due_date
            if assigned_officer_id is None and "assignment_due_date" not in requested_fields:
                target_due_date = None

            conn.execute(
                """
                UPDATE pnms
                SET
                    assigned_officer_id = ?,
                    assigned_by = ?,
                    assigned_at = ?,
                    assignment_status = ?,
                    assignment_priority = ?,
                    assignment_due_date = ?,
                    assignment_notes = ?,
                    assignment_updated_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    assigned_officer_id,
                    assigned_by,
                    assigned_at,
                    next_status,
                    priority,
                    target_due_date,
                    notes,
                    now,
                    now,
                    target_pnm_id,
                ),
            )
            sync_primary_assignment_links_for_pnm(
                conn,
                pnm_id=target_pnm_id,
                primary_officer_user_id=assigned_officer_id,
                assigned_by=assigned_by,
                assigned_at=assigned_at,
                updated_at=now,
                clear_all_if_unassigned=True,
            )
            if previous_assigned_officer_id != assigned_officer_id:
                officer_changed_for_any = True
            affected_pnm_ids.append(target_pnm_id)
            if target_pnm_id == pnm_id:
                resolved_primary_status = next_status

        if assigned_officer_id is not None and payload.notify_officer and officer_changed_for_any:
            assignment_title = (
                f"Package Assignment ({len(affected_pnm_ids)}): {row['first_name']} {row['last_name']}"
                if len(affected_pnm_ids) > 1
                else f"Assigned: {row['first_name']} {row['last_name']}"
            )
            create_notification(
                conn,
                user_id=assigned_officer_id,
                notif_type="assignment",
                title=assignment_title,
                body=f"Status: {ASSIGNMENT_STATUS_LABELS.get(resolved_primary_status, resolved_primary_status)}",
                link_path=f"/?pnm={pnm_id}",
            )
        if resolved_primary_status == "needs_help":
            helper_rows = conn.execute(
                "SELECT id FROM users WHERE role = ? AND is_approved = 1",
                (ROLE_HEAD,),
            ).fetchall()
            helper_title = (
                f"Needs Help Package ({len(affected_pnm_ids)}): {row['first_name']} {row['last_name']}"
                if len(affected_pnm_ids) > 1
                else f"Needs Help: {row['first_name']} {row['last_name']}"
            )
            create_notifications_for_users(
                conn,
                [int(item["id"]) for item in helper_rows],
                notif_type="assignment_alert",
                title=helper_title,
                body=notes[:220] or "Assignment was marked as needs help.",
                link_path=f"/?pnm={pnm_id}",
            )

        append_audit_entry(
            conn,
            actor_user_id=int(head_user["id"]),
            action_type="assignment_update",
            entity_type="pnm",
            entity_id=pnm_id,
            payload={
                "old_assigned_officer_id": old_assigned_officer_id,
                "new_assigned_officer_id": assigned_officer_id,
                "old_status": old_status,
                "new_status": resolved_primary_status,
                "old_priority": row["assignment_priority"],
                "new_priority": priority,
                "old_due_date": row["assignment_due_date"],
                "new_due_date": due_date,
                "package_group_id": package_group_id or None,
                "affected_pnm_ids": affected_pnm_ids,
            },
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
        links_by_pnm = fetch_assignment_links_for_pnms(conn, pnm_ids=[pnm_id])

    affected_count = len(affected_pnm_ids)
    return {
        "message": (
            f"PNM assignment details updated for {affected_count} linked rushee(s)."
            if affected_count > 1
            else "PNM assignment details updated."
        ),
        "affected_pnm_ids": affected_pnm_ids,
        "package_group_id": package_group_id or None,
        "pnm": pnm_payload_with_assignment_links(conn, refreshed, own, links_by_pnm),
    }


@app.patch("/api/pnms/{pnm_id}/stage")
def update_pnm_funnel_stage(
    pnm_id: int,
    payload: PnmFunnelStageUpdateRequest,
    user: sqlite3.Row = Depends(require_officer),
) -> dict[str, Any]:
    next_stage = payload.stage
    reason = payload.reason.strip()
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

        old_stage = str(row["funnel_stage"] or "").strip().lower() or "sourced"
        if old_stage not in PNM_FUNNEL_STAGES:
            old_stage = "sourced"
        old_reason = str(row["funnel_stage_reason"] or "").strip()
        if old_stage == next_stage and old_reason == reason:
            own = fetch_own_rating(conn, pnm_id, user["id"])
            links_by_pnm = fetch_assignment_links_for_pnms(conn, pnm_ids=[pnm_id])
            return {
                "message": "Funnel stage unchanged.",
                "pnm": pnm_payload_with_assignment_links(conn, row, own, links_by_pnm),
            }

        changed_at = now_iso()
        conn.execute(
            """
            UPDATE pnms
            SET funnel_stage = ?, funnel_stage_reason = ?, funnel_stage_updated_at = ?, funnel_stage_updated_by = ?, updated_at = ?
            WHERE id = ?
            """,
            (next_stage, reason, changed_at, user["id"], changed_at, pnm_id),
        )
        conn.execute(
            """
            INSERT INTO pnm_stage_history (pnm_id, from_stage, to_stage, reason, changed_by, changed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (pnm_id, old_stage, next_stage, reason, user["id"], changed_at),
        )
        append_audit_entry(
            conn,
            actor_user_id=int(user["id"]),
            action_type="funnel_stage_change",
            entity_type="pnm",
            entity_id=pnm_id,
            payload={
                "from_stage": old_stage,
                "to_stage": next_stage,
                "reason": reason,
            },
        )

        if next_stage in {"bid", "accepted", "declined"}:
            head_rows = conn.execute(
                "SELECT id FROM users WHERE role = ? AND is_approved = 1 AND id != ?",
                (ROLE_HEAD, user["id"]),
            ).fetchall()
            create_notifications_for_users(
                conn,
                [int(item["id"]) for item in head_rows],
                notif_type="funnel_stage",
                title=f"Stage updated: {row['first_name']} {row['last_name']}",
                body=f"{old_stage.title()} -> {next_stage.title()}",
                link_path=f"/meeting?pnm={pnm_id}",
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
        links_by_pnm = fetch_assignment_links_for_pnms(conn, pnm_ids=[pnm_id])

    return {
        "message": "PNM funnel stage updated.",
        "pnm": pnm_payload_with_assignment_links(conn, refreshed, own, links_by_pnm),
        "change": {
            "from_stage": old_stage,
            "to_stage": next_stage,
            "reason": reason,
            "changed_at": changed_at,
            "changed_by": int(user["id"]),
            "changed_by_username": user["username"],
        },
    }


@app.get("/api/pnms/{pnm_id}/stage-history")
def pnm_funnel_stage_history(
    pnm_id: int,
    limit: int = 120,
    _: sqlite3.Row = Depends(current_user),
) -> dict[str, Any]:
    max_limit = max(1, min(400, int(limit)))
    with db_session() as conn:
        exists = conn.execute("SELECT id, funnel_stage FROM pnms WHERE id = ?", (pnm_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="PNM not found.")
        rows = conn.execute(
            """
            SELECT
                h.id,
                h.from_stage,
                h.to_stage,
                h.reason,
                h.changed_by,
                h.changed_at,
                u.username AS changed_by_username
            FROM pnm_stage_history h
            JOIN users u ON u.id = h.changed_by
            WHERE h.pnm_id = ?
            ORDER BY h.changed_at DESC, h.id DESC
            LIMIT ?
            """,
            (pnm_id, max_limit),
        ).fetchall()
    return {
        "pnm_id": pnm_id,
        "current_stage": exists["funnel_stage"] if exists["funnel_stage"] else "sourced",
        "history": [
            {
                "id": int(row["id"]),
                "from_stage": row["from_stage"],
                "to_stage": row["to_stage"],
                "reason": row["reason"] or "",
                "changed_by": int(row["changed_by"]),
                "changed_by_username": row["changed_by_username"],
                "changed_at": row["changed_at"],
            }
            for row in rows
        ],
    }


@app.get("/api/funnel/summary")
def funnel_summary(_: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    with db_session() as conn:
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS pnm_total,
                COALESCE(SUM(CASE WHEN funnel_stage = 'accepted' THEN 1 ELSE 0 END), 0) AS accepted_count,
                COALESCE(SUM(CASE WHEN funnel_stage = 'declined' THEN 1 ELSE 0 END), 0) AS declined_count
            FROM pnms
            """
        ).fetchone()
        stage_rows = conn.execute(
            """
            SELECT
                funnel_stage,
                COUNT(*) AS count,
                COALESCE(AVG(weighted_total), 0) AS avg_weighted_total
            FROM pnms
            GROUP BY funnel_stage
            """
        ).fetchall()
        transition_rows = conn.execute(
            """
            SELECT
                from_stage,
                to_stage,
                COUNT(*) AS transition_count
            FROM pnm_stage_history
            GROUP BY from_stage, to_stage
            ORDER BY transition_count DESC, from_stage ASC, to_stage ASC
            LIMIT 40
            """
        ).fetchall()
        recent_rows = conn.execute(
            """
            SELECT
                h.pnm_id,
                h.from_stage,
                h.to_stage,
                h.reason,
                h.changed_at,
                p.pnm_code,
                p.first_name,
                p.last_name,
                u.username AS changed_by_username
            FROM pnm_stage_history h
            JOIN pnms p ON p.id = h.pnm_id
            JOIN users u ON u.id = h.changed_by
            ORDER BY h.changed_at DESC, h.id DESC
            LIMIT 30
            """
        ).fetchall()

    stage_counts: dict[str, int] = {stage: 0 for stage in PNM_FUNNEL_STAGES}
    stage_avg_scores: dict[str, float] = {stage: 0.0 for stage in PNM_FUNNEL_STAGES}
    for row in stage_rows:
        stage_name = str(row["funnel_stage"] or "").strip().lower()
        if stage_name not in stage_counts:
            continue
        stage_counts[stage_name] = int(row["count"])
        stage_avg_scores[stage_name] = round(float(row["avg_weighted_total"]), 2)

    conversion_steps: list[dict[str, Any]] = []
    previous_count = None
    for stage_name in PNM_FUNNEL_STAGES:
        count = stage_counts[stage_name]
        conversion_from_previous = None
        if previous_count is not None and previous_count > 0:
            conversion_from_previous = round((count / previous_count) * 100, 1)
        conversion_steps.append(
            {
                "stage": stage_name,
                "count": count,
                "avg_weighted_total": stage_avg_scores[stage_name],
                "conversion_from_previous_pct": conversion_from_previous,
            }
        )
        previous_count = count

    pnm_total = int(totals["pnm_total"] or 0)
    accepted_count = int(totals["accepted_count"] or 0)
    declined_count = int(totals["declined_count"] or 0)
    bid_count = stage_counts["bid"] + stage_counts["accepted"] + stage_counts["declined"]
    bid_conversion_pct = round((accepted_count / bid_count) * 100, 1) if bid_count > 0 else 0.0
    overall_acceptance_pct = round((accepted_count / pnm_total) * 100, 1) if pnm_total > 0 else 0.0

    return {
        "total_pnms": pnm_total,
        "accepted_count": accepted_count,
        "declined_count": declined_count,
        "bid_count": bid_count,
        "bid_conversion_pct": bid_conversion_pct,
        "overall_acceptance_pct": overall_acceptance_pct,
        "stages": conversion_steps,
        "transitions": [
            {
                "from_stage": row["from_stage"],
                "to_stage": row["to_stage"],
                "count": int(row["transition_count"]),
            }
            for row in transition_rows
        ],
        "recent_changes": [
            {
                "pnm_id": int(row["pnm_id"]),
                "pnm_code": row["pnm_code"],
                "name": f"{row['first_name']} {row['last_name']}",
                "from_stage": row["from_stage"],
                "to_stage": row["to_stage"],
                "reason": row["reason"] or "",
                "changed_at": row["changed_at"],
                "changed_by_username": row["changed_by_username"],
            }
            for row in recent_rows
        ],
    }


@app.post("/api/pnms/{pnm_id}/photo")
async def upload_pnm_photo(
    pnm_id: int,
    photo: UploadFile = File(...),
    user: sqlite3.Row = Depends(require_officer),
) -> dict[str, Any]:
    content = await photo.read(MAX_PNM_PHOTO_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Image file cannot be empty.")
    if len(content) > MAX_PNM_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail=f"Image too large. Max size is {MAX_PNM_PHOTO_BYTES // (1024 * 1024)} MB.")
    extension = detect_image_extension(photo.content_type, content)
    if extension is None:
        raise HTTPException(status_code=400, detail="Unsupported image type. Use JPG, PNG, or WEBP.")

    try:
        public_path, target_path = write_pnm_photo_bytes(pnm_id, content, extension)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Unable to save photo: {exc}") from exc

    old_photo_path: str | None = None
    payload_pnm: dict[str, Any] | None = None

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
            links_by_pnm = fetch_assignment_links_for_pnms(conn, pnm_ids=[pnm_id])
            payload_pnm = pnm_payload_with_assignment_links(conn, refreshed, own, links_by_pnm)
    except Exception:
        target_path.unlink(missing_ok=True)
        raise

    if old_photo_path and old_photo_path != public_path:
        remove_photo_if_present(old_photo_path)

    return {
        "message": "PNM photo uploaded.",
        "pnm": payload_pnm,
    }


@app.post("/api/pnms/{pnm_id}/photo/refresh-instagram")
def refresh_pnm_photo_from_instagram(
    pnm_id: int,
    user: sqlite3.Row = Depends(require_officer),
) -> dict[str, Any]:
    old_photo_path: str | None = None
    refreshed_photo_path: str | None = None
    payload_pnm: dict[str, Any] | None = None

    with db_session() as conn:
        row = conn.execute("SELECT * FROM pnms WHERE id = ?", (pnm_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="PNM not found.")
        instagram_handle = row["instagram_handle"]
        if not instagram_handle:
            raise HTTPException(status_code=400, detail="PNM does not have an Instagram handle.")
        old_photo_path = row["photo_path"]

        fetched_photo = try_fetch_instagram_profile_photo(instagram_handle)
        if not fetched_photo:
            raise HTTPException(
                status_code=502,
                detail="Could not fetch Instagram profile image right now. Try again in a minute.",
            )

        photo_bytes, extension = fetched_photo
        try:
            public_path, target_path = write_pnm_photo_bytes(pnm_id, photo_bytes, extension)
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"Unable to save image: {exc}") from exc

        try:
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
            links_by_pnm = fetch_assignment_links_for_pnms(conn, pnm_ids=[pnm_id])
            refreshed_photo_path = refreshed["photo_path"]
            payload_pnm = pnm_payload_with_assignment_links(conn, refreshed, own, links_by_pnm)
        except Exception:
            target_path.unlink(missing_ok=True)
            raise

    if old_photo_path and old_photo_path != refreshed_photo_path:
        remove_photo_if_present(old_photo_path)

    return {
        "message": "Instagram photo refreshed.",
        "pnm": payload_pnm,
    }


@app.get("/api/pnms/{pnm_id}/meeting")
def pnm_meeting_view(pnm_id: int, user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    tenant = current_tenant()
    criteria_by_field = rating_criteria_by_field(list(tenant.rating_criteria))

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

        package_group_id = normalize_package_group_id(pnm_row["package_group_id"])
        linked_rows: list[sqlite3.Row] = []
        if package_group_id:
            linked_rows = conn.execute(
                """
                SELECT id, pnm_code, first_name, last_name
                FROM pnms
                WHERE package_group_id = ? AND id != ?
                ORDER BY last_name ASC, first_name ASC
                """,
                (package_group_id, pnm_id),
            ).fetchall()

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
            SELECT l.lunch_date, l.start_time, l.end_time, l.location, l.notes, l.created_at, u.username, u.role
            FROM lunches l
            JOIN users u ON u.id = l.user_id
            WHERE l.pnm_id = ?
            ORDER BY l.lunch_date DESC, l.created_at DESC
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
        trend_rows = conn.execute(
            """
            SELECT
                rh.id,
                rh.user_id,
                rh.total_score,
                rh.event_type,
                rh.changed_at,
                u.role
            FROM rating_history rh
            JOIN users u ON u.id = rh.user_id
            WHERE rh.pnm_id = ?
            ORDER BY rh.changed_at ASC, rh.id ASC
            """,
            (pnm_id,),
        ).fetchall()
        stage_rows = conn.execute(
            """
            SELECT
                h.id,
                h.from_stage,
                h.to_stage,
                h.reason,
                h.changed_at,
                u.username AS changed_by_username
            FROM pnm_stage_history h
            JOIN users u ON u.id = h.changed_by
            WHERE h.pnm_id = ?
            ORDER BY h.changed_at DESC, h.id DESC
            LIMIT 20
            """,
            (pnm_id,),
        ).fetchall()
        rating_comment_rows = conn.execute(
            """
            SELECT
                rce.id,
                rce.rating_id,
                rce.user_id,
                rce.event_type,
                rce.old_total,
                rce.new_total,
                rce.delta_total,
                rce.comment,
                rce.changed_at,
                u.username,
                u.role,
                u.emoji
            FROM rating_comment_events rce
            JOIN users u ON u.id = rce.user_id
            WHERE rce.pnm_id = ?
            ORDER BY rce.changed_at DESC, rce.id DESC
            """,
            (pnm_id,),
        ).fetchall()
        ranking_rows = conn.execute(
            """
            SELECT
                id,
                avg_good_with_girls,
                avg_will_make_it,
                avg_personable,
                avg_alcohol_control,
                avg_instagram_marketability,
                weighted_total
            FROM pnms
            ORDER BY id ASC
            """
        ).fetchall()
        links_by_pnm = fetch_assignment_links_for_pnms(conn, pnm_ids=[pnm_id])

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
    cohort_size = len(ranking_rows)
    weighted_values = [float(row["weighted_total"]) for row in ranking_rows]
    weighted_target = float(pnm_row["weighted_total"])
    weighted_rank = 1 + sum(1 for value in weighted_values if value > weighted_target + 1e-9) if weighted_values else None
    weighted_percentile = (
        round((sum(1 for value in weighted_values if value <= weighted_target + 1e-9) / len(weighted_values)) * 100, 1)
        if weighted_values
        else None
    )

    category_rankings: list[dict[str, Any]] = []
    for field in RATING_FIELDS:
        column = PNM_AVERAGE_COLUMN_BY_FIELD[field]
        values = [float(row[column]) for row in ranking_rows]
        target_value = float(pnm_row[column])
        rank = 1 + sum(1 for value in values if value > target_value + 1e-9) if values else 1
        percentile = (
            round((sum(1 for value in values if value <= target_value + 1e-9) / len(values)) * 100, 1)
            if values
            else 100.0
        )
        criteria_entry = criteria_by_field.get(field, {})
        configured_max_raw = criteria_entry.get("max", RATING_FIELD_LIMITS.get(field, 10))
        try:
            configured_max = int(configured_max_raw)
        except (TypeError, ValueError):
            configured_max = int(RATING_FIELD_LIMITS.get(field, 10))
        configured_max = max(1, min(int(RATING_FIELD_LIMITS.get(field, configured_max)), configured_max))
        label = sanitize_short_text(
            criteria_entry.get("label") if isinstance(criteria_entry.get("label"), str) else "",
            field.replace("_", " ").title(),
            max_length=60,
        )
        short_label = sanitize_short_text(
            criteria_entry.get("short_label") if isinstance(criteria_entry.get("short_label"), str) else "",
            label,
            max_length=20,
        )
        leader_value = max(values) if values else target_value
        category_rankings.append(
            {
                "field": field,
                "label": label,
                "short_label": short_label,
                "max": configured_max,
                "value": round(target_value, 2),
                "rank": rank,
                "cohort_size": len(values),
                "percentile": percentile,
                "leader_value": round(float(leader_value), 2),
                "points_from_leader": round(float(leader_value) - target_value, 2),
            }
        )

    rating_update_comments: list[dict[str, Any]] = []
    for row in rating_comment_rows:
        from_me = int(row["user_id"]) == int(user["id"])
        if not can_view_identity and not from_me:
            continue
        comment = str(row["comment"] or "").strip()
        if not comment:
            continue
        entry: dict[str, Any] = {
            "event_id": int(row["id"]),
            "rating_id": int(row["rating_id"]),
            "from_me": from_me,
            "event_type": row["event_type"],
            "old_total": int(row["old_total"]) if row["old_total"] is not None else None,
            "new_total": int(row["new_total"]),
            "delta_total": int(row["delta_total"]),
            "comment": comment,
            "changed_at": row["changed_at"],
        }
        if can_view_identity:
            entry["author"] = {"username": row["username"], "role": row["role"], "emoji": row["emoji"]}
        elif from_me:
            entry["author"] = {"username": "You", "role": row["role"], "emoji": None}
        rating_update_comments.append(entry)

    lunch_comment_history: list[dict[str, Any]] = []
    for row in lunch_rows:
        notes = str(row["notes"] or "").strip()
        if not notes:
            continue
        lunch_comment_history.append(
            {
                "lunch_date": row["lunch_date"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "location": row["location"],
                "notes": notes,
                "created_at": row["created_at"],
                "username": row["username"],
                "role": row["role"],
            }
        )

    rush_comment_timeline: list[dict[str, Any]] = []
    for row in rating_update_comments:
        author = row.get("author") or {}
        rush_comment_timeline.append(
            {
                "source": "rating_update",
                "occurred_at": row["changed_at"],
                "comment": row["comment"],
                "username": author.get("username") or ("You" if row.get("from_me") else "Member"),
                "role": author.get("role") or "",
                "delta_total": row["delta_total"],
                "new_total": row["new_total"],
                "event_type": row["event_type"],
            }
        )
    for row in lunch_comment_history:
        rush_comment_timeline.append(
            {
                "source": "lunch_note",
                "occurred_at": row["created_at"] or row["lunch_date"],
                "comment": row["notes"],
                "username": row["username"],
                "role": row["role"],
                "lunch_date": row["lunch_date"],
                "location": row["location"],
            }
        )
    rush_comment_timeline.sort(key=lambda item: str(item.get("occurred_at") or ""), reverse=True)

    summary = {
        "ratings_count": len(score_values),
        "highest_rating_total": max(score_values) if score_values else None,
        "lowest_rating_total": min(score_values) if score_values else None,
        "weighted_total": round(float(pnm_row["weighted_total"]), 2),
        "total_lunches": int(pnm_row["total_lunches"]),
        "cohort_size": cohort_size,
        "weighted_total_rank": weighted_rank,
        "weighted_total_percentile": weighted_percentile,
    }
    trend_points = build_rating_trend_points(trend_rows)
    trend_start = trend_points[0]["weighted_total"] if trend_points else None
    trend_end = trend_points[-1]["weighted_total"] if trend_points else None
    trend_delta = (trend_end - trend_start) if trend_start is not None and trend_end is not None else None

    return {
        "pnm": pnm_payload_with_assignment_links(conn, pnm_row, own, links_by_pnm),
        "can_view_rater_identity": can_view_identity,
        "summary": summary,
        "rating_trend": {
            "points": trend_points,
            "events_count": len(trend_rows),
            "start_weighted_total": trend_start,
            "end_weighted_total": trend_end,
            "delta_weighted_total": round(float(trend_delta), 2) if trend_delta is not None else None,
        },
        "funnel_history": [
            {
                "id": int(row["id"]),
                "from_stage": row["from_stage"],
                "to_stage": row["to_stage"],
                "reason": row["reason"] or "",
                "changed_at": row["changed_at"],
                "changed_by_username": row["changed_by_username"],
            }
            for row in stage_rows
        ],
        "category_rankings": category_rankings,
        "ratings": ratings,
        "lunches": [
            {
                "lunch_date": row["lunch_date"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "location": row["location"],
                "notes": row["notes"],
                "created_at": row["created_at"],
                "username": row["username"],
                "role": row["role"],
            }
            for row in lunch_rows
        ],
        "rating_update_comments": rating_update_comments,
        "lunch_comment_history": lunch_comment_history,
        "rush_comment_timeline": rush_comment_timeline,
        "matches": matches[:10],
        "linked_pnms": [
            {
                "pnm_id": int(row["id"]),
                "pnm_code": row["pnm_code"],
                "first_name": row["first_name"],
                "last_name": row["last_name"],
            }
            for row in linked_rows
        ],
    }


@app.delete("/api/pnms/{pnm_id}")
def delete_pnm(pnm_id: int, user: sqlite3.Row = Depends(require_head)) -> dict[str, str]:
    with db_session() as conn:
        row = conn.execute(
            "SELECT id, pnm_code, first_name, last_name, photo_path, package_group_id FROM pnms WHERE id = ?",
            (pnm_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="PNM not found.")

        rating_users = conn.execute("SELECT DISTINCT user_id FROM ratings WHERE pnm_id = ?", (pnm_id,)).fetchall()
        lunch_users = conn.execute("SELECT DISTINCT user_id FROM lunches WHERE pnm_id = ?", (pnm_id,)).fetchall()
        affected_users = {int(item["user_id"]) for item in rating_users + lunch_users}
        photo_path = row["photo_path"]
        display_name = f"{row['first_name']} {row['last_name']}"

        conn.execute("DELETE FROM engagement_events WHERE pnm_id = ?", (pnm_id,))
        conn.execute("DELETE FROM pnms WHERE id = ?", (pnm_id,))
        package_group_id = normalize_package_group_id(row["package_group_id"])
        if package_group_id:
            remaining = conn.execute(
                "SELECT id FROM pnms WHERE package_group_id = ? ORDER BY id ASC",
                (package_group_id,),
            ).fetchall()
            if len(remaining) == 1:
                conn.execute(
                    "UPDATE pnms SET package_group_id = NULL, updated_at = ? WHERE id = ?",
                    (now_iso(), int(remaining[0]["id"])),
                )
        append_audit_entry(
            conn,
            actor_user_id=int(user["id"]),
            action_type="pnm_delete",
            entity_type="pnm",
            entity_id=pnm_id,
            payload={"pnm_code": row["pnm_code"], "name": display_name},
        )
        sync_engagement_events_from_sources(conn)
        for user_id in affected_users:
            recalc_member_rating_stats(conn, user_id)
            recalc_member_lunch_stats(conn, user_id)

    remove_photo_if_present(photo_path)
    return {"message": f"Deleted PNM {display_name} ({row['pnm_code']})."}


@app.post("/api/ratings")
def upsert_rating(payload: RatingUpsertRequest, user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    tenant = current_tenant()
    score_data = {
        "good_with_girls": payload.good_with_girls,
        "will_make_it": payload.will_make_it,
        "personable": payload.personable,
        "alcohol_control": payload.alcohol_control,
        "instagram_marketability": payload.instagram_marketability,
    }
    validate_score_data_against_criteria(score_data, list(tenant.rating_criteria))
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
                write_rating_history_event(
                    conn,
                    rating_id=int(existing["id"]),
                    pnm_id=payload.pnm_id,
                    user_id=int(user["id"]),
                    event_type="update",
                    scores=new_payload,
                    changed_at=now,
                )
                write_rating_comment_event(
                    conn,
                    rating_id=int(existing["id"]),
                    pnm_id=payload.pnm_id,
                    user_id=int(user["id"]),
                    event_type="update",
                    old_total=int(existing["total_score"]),
                    new_total=new_total,
                    delta_total=delta_total,
                    comment=comment,
                    changed_at=now,
                )
                append_audit_entry(
                    conn,
                    actor_user_id=int(user["id"]),
                    action_type="rating_update",
                    entity_type="rating",
                    entity_id=int(existing["id"]),
                    payload={
                        "pnm_id": payload.pnm_id,
                        "old_total": int(existing["total_score"]),
                        "new_total": new_total,
                        "delta_total": delta_total,
                        "comment": comment,
                    },
                )
        else:
            cursor = conn.execute(
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
            rating_id = int(cursor.lastrowid or 0)
            create_payload = {
                "good_with_girls": payload.good_with_girls,
                "will_make_it": payload.will_make_it,
                "personable": payload.personable,
                "alcohol_control": payload.alcohol_control,
                "instagram_marketability": payload.instagram_marketability,
                "total_score": new_total,
            }
            write_rating_history_event(
                conn,
                rating_id=rating_id,
                pnm_id=payload.pnm_id,
                user_id=int(user["id"]),
                event_type="create",
                scores=create_payload,
                changed_at=now,
            )
            write_rating_comment_event(
                conn,
                rating_id=rating_id,
                pnm_id=payload.pnm_id,
                user_id=int(user["id"]),
                event_type="create",
                old_total=None,
                new_total=new_total,
                delta_total=0,
                comment=(payload.comment or "").strip(),
                changed_at=now,
            )
            append_audit_entry(
                conn,
                actor_user_id=int(user["id"]),
                action_type="rating_create",
                entity_type="rating",
                entity_id=rating_id,
                payload={"pnm_id": payload.pnm_id, "new_total": new_total},
            )

        recalc_pnm_rating_stats(conn, payload.pnm_id)
        recalc_member_rating_stats(conn, user["id"])
        evaluate_weekly_goal_completions(conn)

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
        links_by_pnm = fetch_assignment_links_for_pnms(conn, pnm_ids=[payload.pnm_id])

    return {
        "rating": rating_payload(updated_rating),
        "change": change_event,
        "pnm": pnm_payload(
            updated_pnm,
            rating_payload(updated_rating),
            assigned_officer=assigned_officer_payload_from_row(updated_pnm),
            assigned_officers=links_by_pnm.get(int(updated_pnm["id"]), []),
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
        if user["role"] == ROLE_RUSHER and row["user_id"] != user["id"]:
            continue
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
    tenant = current_tenant()
    if payload.end_time and not payload.start_time:
        raise HTTPException(status_code=400, detail="End time requires a start time.")
    if payload.start_time and payload.end_time:
        start_hour, start_min = parse_clock_value(payload.start_time) or (0, 0)
        end_hour, end_min = parse_clock_value(payload.end_time) or (0, 0)
        if end_hour * 60 + end_min <= start_hour * 60 + start_min:
            raise HTTPException(status_code=400, detail="End time must be after start time.")

    with db_session() as conn:
        pnm = conn.execute(
            "SELECT id, pnm_code, first_name, last_name FROM pnms WHERE id = ?",
            (payload.pnm_id,),
        ).fetchone()
        if not pnm:
            raise HTTPException(status_code=404, detail="PNM not found.")

        try:
            now = now_iso()
            cursor = conn.execute(
                """
                INSERT INTO lunches (pnm_id, user_id, lunch_date, start_time, end_time, location, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.pnm_id,
                    user["id"],
                    payload.lunch_date,
                    payload.start_time,
                    payload.end_time,
                    payload.location.strip(),
                    payload.notes.strip(),
                    now,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(
                status_code=409,
                detail="Duplicate lunch log for this member, PNM, and date is not allowed.",
            ) from exc

        lunch_id = int(cursor.lastrowid or 0)
        sync_engagement_event_from_lunch(conn, lunch_id)
        append_audit_entry(
            conn,
            actor_user_id=int(user["id"]),
            action_type="lunch_create",
            entity_type="lunch",
            entity_id=lunch_id,
            payload={
                "pnm_id": payload.pnm_id,
                "lunch_date": payload.lunch_date,
                "start_time": payload.start_time,
                "end_time": payload.end_time,
            },
        )
        recalc_member_lunch_stats(conn, user["id"])
        recalc_pnm_lunch_stats(conn, payload.pnm_id)
        evaluate_weekly_goal_completions(conn)

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
        links_by_pnm = fetch_assignment_links_for_pnms(conn, pnm_ids=[payload.pnm_id])

    try:
        google_calendar_url = build_google_calendar_event_url(
            pnm_name=f"{pnm['first_name']} {pnm['last_name']}",
            pnm_code=pnm["pnm_code"],
            lunch_date=payload.lunch_date,
            notes=payload.notes.strip(),
            location=payload.location.strip(),
            start_time=payload.start_time,
            end_time=payload.end_time,
            logged_by_username=user["username"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "message": "Lunch scheduled.",
        "member": user_payload(refreshed_user, refreshed_user["role"], refreshed_user["id"]),
        "pnm": pnm_payload(
            refreshed_pnm,
            own_rating=None,
            assigned_officer=assigned_officer_payload_from_row(refreshed_pnm),
            assigned_officers=links_by_pnm.get(int(refreshed_pnm["id"]), []),
        ),
        "lunch": {
            "lunch_id": lunch_id,
            "pnm_id": payload.pnm_id,
            "lunch_date": payload.lunch_date,
            "start_time": payload.start_time,
            "end_time": payload.end_time,
            "location": payload.location.strip(),
            "notes": payload.notes.strip(),
            "google_calendar_url": google_calendar_url,
            "calendar_feed_path": f"/{tenant.slug}/calendar/rush.ics?token={tenant.calendar_share_token}",
            "calendar_lunch_feed_path": f"/{tenant.slug}/calendar/lunches.ics?token={tenant.calendar_share_token}",
        },
    }


@app.get("/api/pnms/{pnm_id}/lunches")
def pnm_lunches(pnm_id: int, _: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    with db_session() as conn:
        target = conn.execute("SELECT id FROM pnms WHERE id = ?", (pnm_id,)).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="PNM not found.")

        rows = conn.execute(
            """
            SELECT l.lunch_date, l.start_time, l.end_time, l.location, l.notes, l.created_at, u.username
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
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "location": row["location"],
                "notes": row["notes"],
                "created_at": row["created_at"],
                "username": row["username"],
            }
            for row in rows
        ]
    }


@app.get("/api/lunches/scheduled")
def scheduled_lunches(
    request: Request,
    limit: int = 120,
    _: sqlite3.Row = Depends(current_user),
) -> dict[str, Any]:
    tenant = current_tenant()
    capped_limit = max(10, min(int(limit), 400))
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT
                l.id,
                l.pnm_id,
                l.user_id,
                l.lunch_date,
                l.start_time,
                l.end_time,
                l.location,
                l.notes,
                l.created_at,
                p.pnm_code,
                p.first_name,
                p.last_name,
                ao.username AS assigned_officer_username,
                u.username AS scheduled_by_username
            FROM lunches l
            JOIN pnms p ON p.id = l.pnm_id
            JOIN users u ON u.id = l.user_id
            LEFT JOIN users ao ON ao.id = p.assigned_officer_id
            WHERE l.lunch_date >= date('now')
            ORDER BY l.lunch_date ASC, COALESCE(l.start_time, '23:59') ASC, l.id ASC
            LIMIT ?
            """,
            (capped_limit,),
        ).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        google_calendar_url = None
        try:
            google_calendar_url = build_google_calendar_event_url(
                pnm_name=f"{row['first_name']} {row['last_name']}",
                pnm_code=row["pnm_code"],
                lunch_date=row["lunch_date"],
                notes=row["notes"] or "",
                location=row["location"] or "",
                start_time=row["start_time"],
                end_time=row["end_time"],
                logged_by_username=row["scheduled_by_username"],
            )
        except ValueError:
            # Keep the event visible even if legacy malformed time values exist.
            google_calendar_url = None

        items.append(
            {
                "lunch_id": int(row["id"]),
                "pnm_id": int(row["pnm_id"]),
                "lunch_date": row["lunch_date"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "location": row["location"] or "",
                "notes": row["notes"] or "",
                "created_at": row["created_at"],
                "pnm_code": row["pnm_code"],
                "pnm_name": f"{row['first_name']} {row['last_name']}",
                "assigned_officer_username": row["assigned_officer_username"] or "",
                "scheduled_by_username": row["scheduled_by_username"],
                "google_calendar_url": google_calendar_url,
            }
        )

    return {
        "lunches": items,
        "calendar_share": calendar_share_payload(request, tenant),
    }


def calendar_share_payload(request: Request, tenant: TenantContext) -> dict[str, Any]:
    feed_path = f"/{tenant.slug}/calendar/rush.ics?token={tenant.calendar_share_token}"
    lunch_feed_path = f"/{tenant.slug}/calendar/lunches.ics?token={tenant.calendar_share_token}"
    base_origin = app_base_origin(request)
    feed_url = f"{base_origin}{feed_path}"
    lunch_feed_url = f"{base_origin}{lunch_feed_path}"
    return {
        "feed_url": feed_url,
        "rush_feed_url": feed_url,
        "lunch_feed_url": lunch_feed_url,
        "lunch_webcal_url": build_webcal_url(lunch_feed_url),
        "lunch_google_subscribe_url": build_google_subscribe_url(lunch_feed_url),
        "webcal_url": build_webcal_url(feed_url),
        "google_subscribe_url": build_google_subscribe_url(feed_url),
        "timezone": CALENDAR_TIMEZONE,
    }


@app.get("/api/mobile/home")
def mobile_home_payload(request: Request, _: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    tenant = current_tenant()
    with db_session() as conn:
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS pnm_count,
                COALESCE(SUM(rating_count), 0) AS rating_count,
                COALESCE(SUM(total_lunches), 0) AS lunch_count
            FROM pnms
            """
        ).fetchone()
        rows = conn.execute(
            """
            SELECT
                p.id,
                p.pnm_code,
                p.first_name,
                p.last_name,
                p.weighted_total,
                p.rating_count,
                p.total_lunches,
                p.first_event_date,
                ao.username AS assigned_officer_username
            FROM pnms p
            LEFT JOIN users ao ON ao.id = p.assigned_officer_id
            ORDER BY p.weighted_total DESC, p.rating_count DESC, p.total_lunches DESC, p.last_name ASC, p.first_name ASC
            LIMIT 10
            """
        ).fetchall()

    leaderboard: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        leaderboard.append(
            {
                "rank": index,
                "pnm_id": row["id"],
                "pnm_code": row["pnm_code"],
                "name": f"{row['first_name']} {row['last_name']}",
                "weighted_total": round(float(row["weighted_total"]), 2),
                "rating_count": int(row["rating_count"]),
                "total_lunches": int(row["total_lunches"]),
                "days_since_first_event": (date.today() - date.fromisoformat(row["first_event_date"])).days,
                "assigned_officer_username": row["assigned_officer_username"] or "",
            }
        )

    return {
        "stats": {
            "pnm_count": int(totals["pnm_count"]),
            "rating_count": int(totals["rating_count"]),
            "lunch_count": int(totals["lunch_count"]),
        },
        "leaderboard": leaderboard,
        "calendar_share": calendar_share_payload(request, tenant),
    }


@app.get("/api/mobile/pnms")
def mobile_pnms_payload(_: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    with db_session() as conn:
        ensure_package_link_schema(conn)
        rows = conn.execute(
            """
            SELECT
                p.id,
                p.pnm_code,
                p.first_name,
                p.last_name,
                p.phone_number,
                p.instagram_handle,
                p.interests,
                p.first_event_date,
                p.weighted_total,
                p.rating_count,
                p.total_lunches,
                p.photo_path,
                p.package_group_id,
                ao.username AS assigned_officer_username
            FROM pnms p
            LEFT JOIN users ao ON ao.id = p.assigned_officer_id
            ORDER BY p.weighted_total DESC, p.last_name ASC, p.first_name ASC
            LIMIT 300
            """
        ).fetchall()
        links_by_pnm = fetch_assignment_links_for_pnms(
            conn,
            pnm_ids=[int(row["id"]) for row in rows],
        )

    return {
        "pnms": [
            {
                "pnm_id": row["id"],
                "pnm_code": row["pnm_code"],
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "phone_number": row["phone_number"],
                "instagram_handle": row["instagram_handle"],
                "interests": decode_interests(row["interests"]),
                "weighted_total": round(float(row["weighted_total"]), 2),
                "rating_count": int(row["rating_count"]),
                "total_lunches": int(row["total_lunches"]),
                "days_since_first_event": (date.today() - date.fromisoformat(row["first_event_date"])).days,
                "photo_url": resolve_pnm_photo_url(row["photo_path"], row["instagram_handle"]),
                "package_group_id": normalize_package_group_id(row["package_group_id"]) or None,
                "package_group_label": package_group_label(normalize_package_group_id(row["package_group_id"])),
                "assigned_officer": (
                    {"username": row["assigned_officer_username"]}
                    if row["assigned_officer_username"]
                    else None
                ),
                "assigned_officers": merge_assigned_officers_for_pnm_row(
                    row,
                    links_by_pnm.get(int(row["id"]), []),
                ),
            }
            for row in rows
        ]
    }


@app.get("/api/mobile/members")
def mobile_members_payload(user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    with db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE is_approved = 1 ORDER BY role ASC, username ASC LIMIT 400"
        ).fetchall()
    return {"users": [user_payload(row, user["role"], user["id"]) for row in rows]}


@app.get("/api/calendar/share")
def calendar_share_links(request: Request, _: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    tenant = current_tenant()
    return calendar_share_payload(request, tenant)


@app.get("/calendar/lunches.ics")
def public_lunch_calendar_feed(token: str | None = None) -> Response:
    tenant = current_tenant()
    expected_token = tenant.calendar_share_token.strip()
    if not token or not expected_token or not hmac.compare_digest(token, expected_token):
        raise HTTPException(status_code=401, detail="Invalid calendar token.")

    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT
                l.id,
                l.lunch_date,
                l.start_time,
                l.end_time,
                l.location,
                l.notes,
                l.created_at,
                p.pnm_code,
                p.first_name,
                p.last_name,
                u.username
            FROM lunches l
            JOIN pnms p ON p.id = l.pnm_id
            JOIN users u ON u.id = l.user_id
            ORDER BY l.lunch_date ASC, COALESCE(l.start_time, '00:00') ASC, l.id ASC
            """
        ).fetchall()

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Rush Evaluation//Lunch Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        fold_ical_line(f"X-WR-CALNAME:{escape_ical_text(f'{tenant.display_name} Lunch Calendar')}"),
        fold_ical_line(f"X-WR-TIMEZONE:{escape_ical_text(CALENDAR_TIMEZONE)}"),
    ]

    for row in rows:
        lunch_day = date.fromisoformat(row["lunch_date"])
        try:
            start_clock = parse_clock_value(row["start_time"])
        except ValueError:
            start_clock = None
        try:
            end_clock = parse_clock_value(row["end_time"])
        except ValueError:
            end_clock = None

        summary = f"Lunch with {row['first_name']} {row['last_name']}"
        description_parts = [
            f"PNM Code: {row['pnm_code']}",
            f"Logged by: {row['username']}",
        ]
        if row["notes"]:
            description_parts.append(f"Notes: {row['notes']}")
        description = "\n".join(description_parts)

        lines.append("BEGIN:VEVENT")
        lines.append(fold_ical_line(f"UID:lunch-{tenant.slug}-{row['id']}@rush-evaluation"))
        lines.append(fold_ical_line(f"DTSTAMP:{format_utc_ical(row['created_at'])}"))
        lines.append(fold_ical_line(f"SUMMARY:{escape_ical_text(summary)}"))
        lines.append(fold_ical_line(f"DESCRIPTION:{escape_ical_text(description)}"))
        if row["location"]:
            lines.append(fold_ical_line(f"LOCATION:{escape_ical_text(row['location'])}"))

        if start_clock:
            start_dt = datetime(lunch_day.year, lunch_day.month, lunch_day.day, start_clock[0], start_clock[1], 0)
            if end_clock:
                end_dt = datetime(lunch_day.year, lunch_day.month, lunch_day.day, end_clock[0], end_clock[1], 0)
                if end_dt <= start_dt:
                    end_dt = start_dt + timedelta(hours=1)
            else:
                end_dt = start_dt + timedelta(hours=1)
            lines.append(
                fold_ical_line(f"DTSTART;TZID={CALENDAR_TIMEZONE}:{format_google_event_stamp(start_dt)}")
            )
            lines.append(
                fold_ical_line(f"DTEND;TZID={CALENDAR_TIMEZONE}:{format_google_event_stamp(end_dt)}")
            )
        else:
            next_day = lunch_day + timedelta(days=1)
            lines.append(fold_ical_line(f"DTSTART;VALUE=DATE:{lunch_day.strftime('%Y%m%d')}"))
            lines.append(fold_ical_line(f"DTEND;VALUE=DATE:{next_day.strftime('%Y%m%d')}"))

        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    payload = "\r\n".join(lines) + "\r\n"
    return Response(
        content=payload,
        media_type="text/calendar; charset=utf-8",
        headers={"Cache-Control": "public, max-age=300"},
    )


@app.get("/calendar/rush.ics")
def public_rush_calendar_feed(token: str | None = None) -> Response:
    tenant = current_tenant()
    expected_token = tenant.calendar_share_token.strip()
    if not token or not expected_token or not hmac.compare_digest(token, expected_token):
        raise HTTPException(status_code=401, detail="Invalid calendar token.")

    with db_session() as conn:
        lunch_rows = conn.execute(
            """
            SELECT
                l.id,
                l.lunch_date,
                l.start_time,
                l.end_time,
                l.location,
                l.notes,
                l.created_at,
                p.pnm_code,
                p.first_name,
                p.last_name,
                u.username
            FROM lunches l
            JOIN pnms p ON p.id = l.pnm_id
            JOIN users u ON u.id = l.user_id
            ORDER BY l.lunch_date ASC, COALESCE(l.start_time, '00:00') ASC, l.id ASC
            """
        ).fetchall()
        event_rows = conn.execute(
            """
            SELECT
                e.id,
                e.title,
                e.event_type,
                e.event_date,
                e.start_time,
                e.end_time,
                e.location,
                e.details,
                e.is_official,
                e.created_at,
                u.username
            FROM rush_events e
            JOIN users u ON u.id = e.created_by
            WHERE e.is_cancelled = 0
            ORDER BY e.event_date ASC, COALESCE(e.start_time, '00:00') ASC, e.id ASC
            """
        ).fetchall()

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Rush Evaluation//Rush Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        fold_ical_line(f"X-WR-CALNAME:{escape_ical_text(f'{tenant.display_name} Rush Calendar')}"),
        fold_ical_line(f"X-WR-TIMEZONE:{escape_ical_text(CALENDAR_TIMEZONE)}"),
    ]

    for row in event_rows:
        event_day = date.fromisoformat(row["event_date"])
        try:
            start_clock = parse_clock_value(row["start_time"])
        except ValueError:
            start_clock = None
        try:
            end_clock = parse_clock_value(row["end_time"])
        except ValueError:
            end_clock = None
        type_label = row["event_type"].replace("_", " ").title()
        summary = f"{row['title']} ({type_label})"
        details_parts = [
            f"Type: {type_label}",
            f"Official: {'Yes' if bool(row['is_official']) else 'No'}",
            f"Created by: {row['username']}",
        ]
        if row["details"]:
            details_parts.append(f"Details: {row['details']}")
        description = "\n".join(details_parts)

        lines.append("BEGIN:VEVENT")
        lines.append(fold_ical_line(f"UID:rush-event-{tenant.slug}-{row['id']}@rush-evaluation"))
        lines.append(fold_ical_line(f"DTSTAMP:{format_utc_ical(row['created_at'])}"))
        lines.append(fold_ical_line(f"SUMMARY:{escape_ical_text(summary)}"))
        lines.append(fold_ical_line(f"DESCRIPTION:{escape_ical_text(description)}"))
        if row["location"]:
            lines.append(fold_ical_line(f"LOCATION:{escape_ical_text(row['location'])}"))
        lines.append(fold_ical_line(f"CATEGORIES:{escape_ical_text(type_label)}"))

        if start_clock:
            start_dt = datetime(event_day.year, event_day.month, event_day.day, start_clock[0], start_clock[1], 0)
            if end_clock:
                end_dt = datetime(event_day.year, event_day.month, event_day.day, end_clock[0], end_clock[1], 0)
                if end_dt <= start_dt:
                    end_dt = start_dt + timedelta(hours=1)
            else:
                end_dt = start_dt + timedelta(hours=1)
            lines.append(fold_ical_line(f"DTSTART;TZID={CALENDAR_TIMEZONE}:{format_google_event_stamp(start_dt)}"))
            lines.append(fold_ical_line(f"DTEND;TZID={CALENDAR_TIMEZONE}:{format_google_event_stamp(end_dt)}"))
        else:
            next_day = event_day + timedelta(days=1)
            lines.append(fold_ical_line(f"DTSTART;VALUE=DATE:{event_day.strftime('%Y%m%d')}"))
            lines.append(fold_ical_line(f"DTEND;VALUE=DATE:{next_day.strftime('%Y%m%d')}"))

        lines.append("END:VEVENT")

    for row in lunch_rows:
        lunch_day = date.fromisoformat(row["lunch_date"])
        try:
            start_clock = parse_clock_value(row["start_time"])
        except ValueError:
            start_clock = None
        try:
            end_clock = parse_clock_value(row["end_time"])
        except ValueError:
            end_clock = None

        summary = f"Lunch with {row['first_name']} {row['last_name']}"
        description_parts = [
            f"PNM Code: {row['pnm_code']}",
            f"Logged by: {row['username']}",
        ]
        if row["notes"]:
            description_parts.append(f"Notes: {row['notes']}")
        description = "\n".join(description_parts)

        lines.append("BEGIN:VEVENT")
        lines.append(fold_ical_line(f"UID:lunch-{tenant.slug}-{row['id']}@rush-evaluation"))
        lines.append(fold_ical_line(f"DTSTAMP:{format_utc_ical(row['created_at'])}"))
        lines.append(fold_ical_line(f"SUMMARY:{escape_ical_text(summary)}"))
        lines.append(fold_ical_line(f"DESCRIPTION:{escape_ical_text(description)}"))
        if row["location"]:
            lines.append(fold_ical_line(f"LOCATION:{escape_ical_text(row['location'])}"))
        lines.append(fold_ical_line("CATEGORIES:Lunch"))

        if start_clock:
            start_dt = datetime(lunch_day.year, lunch_day.month, lunch_day.day, start_clock[0], start_clock[1], 0)
            if end_clock:
                end_dt = datetime(lunch_day.year, lunch_day.month, lunch_day.day, end_clock[0], end_clock[1], 0)
                if end_dt <= start_dt:
                    end_dt = start_dt + timedelta(hours=1)
            else:
                end_dt = start_dt + timedelta(hours=1)
            lines.append(fold_ical_line(f"DTSTART;TZID={CALENDAR_TIMEZONE}:{format_google_event_stamp(start_dt)}"))
            lines.append(fold_ical_line(f"DTEND;TZID={CALENDAR_TIMEZONE}:{format_google_event_stamp(end_dt)}"))
        else:
            next_day = lunch_day + timedelta(days=1)
            lines.append(fold_ical_line(f"DTSTART;VALUE=DATE:{lunch_day.strftime('%Y%m%d')}"))
            lines.append(fold_ical_line(f"DTEND;VALUE=DATE:{next_day.strftime('%Y%m%d')}"))

        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    payload = "\r\n".join(lines) + "\r\n"
    return Response(
        content=payload,
        media_type="text/calendar; charset=utf-8",
        headers={"Cache-Control": "public, max-age=300"},
    )


def engagement_event_payload(row: sqlite3.Row) -> dict[str, Any]:
    keys = set(row.keys())
    pnm_id = int(row["pnm_id"]) if "pnm_id" in keys and row["pnm_id"] is not None else None
    pnm_name = None
    pnm_code = None
    if pnm_id is not None:
        first_name = row["pnm_first_name"] if "pnm_first_name" in keys else None
        last_name = row["pnm_last_name"] if "pnm_last_name" in keys else None
        if first_name and last_name:
            pnm_name = f"{first_name} {last_name}"
        pnm_code = row["pnm_code"] if "pnm_code" in keys else None

    title = row["title"]
    details = row["details"] if "details" in keys else ""
    owner_username = row["owner_username"] if "owner_username" in keys else None
    google_calendar_url = None
    try:
        if row["event_type"] == "lunch" and pnm_name and pnm_code:
            google_calendar_url = build_google_calendar_event_url(
                pnm_name=pnm_name,
                pnm_code=pnm_code,
                lunch_date=row["event_date"],
                notes=details or "",
                location=row["location"] or "",
                start_time=row["start_time"],
                end_time=row["end_time"],
                logged_by_username=owner_username or row["created_by_username"] or "BidBoard",
            )
        else:
            google_calendar_url = build_google_calendar_generic_event_url(
                title=title,
                event_date=row["event_date"],
                details=details or "",
                location=row["location"] or "",
                start_time=row["start_time"],
                end_time=row["end_time"],
            )
    except ValueError:
        google_calendar_url = None

    return {
        "event_id": int(row["id"]),
        "event_type": row["event_type"],
        "status": row["status"],
        "title": title,
        "event_date": row["event_date"],
        "start_time": row["start_time"],
        "end_time": row["end_time"],
        "location": row["location"] or "",
        "details": details or "",
        "pnm": (
            {
                "pnm_id": pnm_id,
                "pnm_code": pnm_code,
                "name": pnm_name,
            }
            if pnm_id is not None
            else None
        ),
        "owner": (
            {
                "user_id": int(row["owner_user_id"]),
                "username": owner_username,
                "role": row["owner_role"] if "owner_role" in keys else None,
                "emoji": row["owner_emoji"] if "owner_emoji" in keys else None,
            }
            if "owner_user_id" in keys and row["owner_user_id"] is not None
            else None
        ),
        "source_type": row["source_type"],
        "source_id": row["source_id"],
        "created_by": int(row["created_by"]),
        "created_by_username": row["created_by_username"] if "created_by_username" in keys else None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "google_calendar_url": google_calendar_url,
    }


@app.get("/api/events")
def list_engagement_events(
    request: Request,
    event_type: str | None = None,
    status_value: str | None = Query(default=None, alias="status"),
    pnm_id: int | None = None,
    owner_user_id: int | None = None,
    source_type: str | None = None,
    include_past: bool = False,
    include_cancelled: bool = False,
    limit: int = 500,
    _: sqlite3.Row = Depends(current_user),
) -> dict[str, Any]:
    where_clauses: list[str] = []
    params: list[Any] = []

    if event_type:
        try:
            normalized_event_type = normalize_engagement_event_type(event_type)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        where_clauses.append("e.event_type = ?")
        params.append(normalized_event_type)

    if status_value:
        try:
            normalized_status = normalize_engagement_event_status(status_value)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        where_clauses.append("e.status = ?")
        params.append(normalized_status)
    elif not include_cancelled:
        where_clauses.append("e.status != 'cancelled'")

    if pnm_id is not None:
        where_clauses.append("e.pnm_id = ?")
        params.append(pnm_id)
    if owner_user_id is not None:
        where_clauses.append("e.owner_user_id = ?")
        params.append(owner_user_id)
    if source_type:
        normalized_source = source_type.strip().lower()
        if normalized_source not in {"manual", "lunch", "rush_event"}:
            raise HTTPException(status_code=400, detail="Source type must be manual, lunch, or rush_event.")
        where_clauses.append("e.source_type = ?")
        params.append(normalized_source)
    if not include_past:
        where_clauses.append("e.event_date >= date('now', '-3 day')")

    safe_limit = max(1, min(1200, int(limit)))
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    with db_session() as conn:
        rows = conn.execute(
            f"""
            SELECT
                e.*,
                p.pnm_code,
                p.first_name AS pnm_first_name,
                p.last_name AS pnm_last_name,
                owner.username AS owner_username,
                owner.role AS owner_role,
                owner.emoji AS owner_emoji,
                creator.username AS created_by_username
            FROM engagement_events e
            LEFT JOIN pnms p ON p.id = e.pnm_id
            LEFT JOIN users owner ON owner.id = e.owner_user_id
            LEFT JOIN users creator ON creator.id = e.created_by
            {where_sql}
            ORDER BY e.event_date ASC, COALESCE(e.start_time, '23:59') ASC, e.id ASC
            LIMIT ?
            """,
            (*params, safe_limit),
        ).fetchall()

    events = [engagement_event_payload(row) for row in rows]
    type_counts: dict[str, int] = {event_name: 0 for event_name in ENGAGEMENT_EVENT_TYPES}
    status_counts: dict[str, int] = {status_name: 0 for status_name in ENGAGEMENT_EVENT_STATUSES}
    for item in events:
        type_counts[item["event_type"]] = int(type_counts.get(item["event_type"], 0)) + 1
        status_counts[item["status"]] = int(status_counts.get(item["status"], 0)) + 1
    return {
        "events": events,
        "count": len(events),
        "type_counts": type_counts,
        "status_counts": status_counts,
        "calendar_share": calendar_share_payload(request, current_tenant()),
    }


@app.post("/api/events")
def create_engagement_event(
    payload: EngagementEventCreateRequest,
    user: sqlite3.Row = Depends(require_head),
) -> dict[str, Any]:
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty.")
    details = payload.details.strip()
    location = payload.location.strip()
    if payload.event_type == "lunch" and payload.pnm_id is None:
        raise HTTPException(status_code=400, detail="Lunch events require a PNM.")

    with db_session() as conn:
        owner_user_id = payload.owner_user_id if payload.owner_user_id is not None else int(user["id"])
        owner = conn.execute(
            "SELECT id, username, role, emoji FROM users WHERE id = ? AND is_approved = 1",
            (owner_user_id,),
        ).fetchone()
        if not owner:
            raise HTTPException(status_code=404, detail="Owner user not found.")

        if payload.pnm_id is not None:
            pnm = conn.execute("SELECT id FROM pnms WHERE id = ?", (payload.pnm_id,)).fetchone()
            if not pnm:
                raise HTTPException(status_code=404, detail="PNM not found.")

        now = now_iso()
        cursor = conn.execute(
            """
            INSERT INTO engagement_events (
                event_type,
                status,
                title,
                event_date,
                start_time,
                end_time,
                location,
                details,
                pnm_id,
                owner_user_id,
                source_type,
                source_id,
                created_by,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'manual', NULL, ?, ?, ?)
            """,
            (
                payload.event_type,
                payload.status,
                title,
                payload.event_date,
                payload.start_time,
                payload.end_time,
                location,
                details,
                payload.pnm_id,
                owner_user_id,
                user["id"],
                now,
                now,
            ),
        )
        event_id = int(cursor.lastrowid or 0)
        append_audit_entry(
            conn,
            actor_user_id=int(user["id"]),
            action_type="event_create",
            entity_type="engagement_event",
            entity_id=event_id,
            payload={
                "event_type": payload.event_type,
                "status": payload.status,
                "event_date": payload.event_date,
                "owner_user_id": owner_user_id,
                "pnm_id": payload.pnm_id,
            },
        )
        if int(owner_user_id) != int(user["id"]):
            create_notification(
                conn,
                user_id=int(owner_user_id),
                notif_type="event",
                title=f"Event Assigned: {title}",
                body=f"{payload.event_date} | {payload.start_time or 'All Day'}",
                link_path="/calendar",
            )

        row = conn.execute(
            """
            SELECT
                e.*,
                p.pnm_code,
                p.first_name AS pnm_first_name,
                p.last_name AS pnm_last_name,
                owner.username AS owner_username,
                owner.role AS owner_role,
                owner.emoji AS owner_emoji,
                creator.username AS created_by_username
            FROM engagement_events e
            LEFT JOIN pnms p ON p.id = e.pnm_id
            LEFT JOIN users owner ON owner.id = e.owner_user_id
            LEFT JOIN users creator ON creator.id = e.created_by
            WHERE e.id = ?
            """,
            (event_id,),
        ).fetchone()
    return {"event": engagement_event_payload(row)}


@app.patch("/api/events/{event_id}")
def update_engagement_event(
    event_id: int,
    payload: EngagementEventUpdateRequest,
    user: sqlite3.Row = Depends(require_officer),
) -> dict[str, Any]:
    requested_fields = set(payload.model_fields_set)
    if not requested_fields:
        raise HTTPException(status_code=400, detail="No event changes provided.")

    with db_session() as conn:
        row = conn.execute("SELECT * FROM engagement_events WHERE id = ?", (event_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Event not found.")

        if row["source_type"] != "manual":
            disallowed = requested_fields - {"status"}
            if disallowed:
                raise HTTPException(
                    status_code=400,
                    detail="Linked events can only update status here. Edit lunches/rush events from their native APIs.",
                )

        if int(user["id"]) != int(row["created_by"]) and user["role"] != ROLE_HEAD:
            if not (row["source_type"] == "lunch" and row["owner_user_id"] == user["id"]):
                raise HTTPException(status_code=403, detail="You cannot edit this event.")

        event_type_token = row["event_type"]
        if "event_type" in requested_fields and payload.event_type is not None:
            event_type_token = payload.event_type
        status_token = row["status"]
        if "status" in requested_fields and payload.status is not None:
            status_token = payload.status
        title = row["title"]
        if "title" in requested_fields and payload.title is not None:
            title = payload.title.strip()
        event_date = row["event_date"]
        if "event_date" in requested_fields and payload.event_date is not None:
            event_date = payload.event_date
        start_time = row["start_time"]
        if "start_time" in requested_fields:
            start_time = payload.start_time
        end_time = row["end_time"]
        if "end_time" in requested_fields:
            end_time = payload.end_time
        location = row["location"]
        if "location" in requested_fields and payload.location is not None:
            location = payload.location.strip()
        details = row["details"]
        if "details" in requested_fields and payload.details is not None:
            details = payload.details.strip()
        pnm_id = row["pnm_id"]
        if "pnm_id" in requested_fields:
            pnm_id = payload.pnm_id
        owner_user_id = row["owner_user_id"]
        if "owner_user_id" in requested_fields:
            owner_user_id = payload.owner_user_id

        if end_time and not start_time:
            raise HTTPException(status_code=400, detail="End time requires a start time.")
        if start_time and end_time:
            start_value = parse_clock_value(start_time)
            end_value = parse_clock_value(end_time)
            if start_value and end_value and (end_value[0] * 60 + end_value[1]) <= (start_value[0] * 60 + start_value[1]):
                raise HTTPException(status_code=400, detail="End time must be after start time.")
        if event_type_token == "lunch" and pnm_id is None:
            raise HTTPException(status_code=400, detail="Lunch events require a PNM.")

        if pnm_id is not None:
            pnm_exists = conn.execute("SELECT id FROM pnms WHERE id = ?", (pnm_id,)).fetchone()
            if not pnm_exists:
                raise HTTPException(status_code=404, detail="PNM not found.")
        if owner_user_id is not None:
            owner_exists = conn.execute("SELECT id FROM users WHERE id = ? AND is_approved = 1", (owner_user_id,)).fetchone()
            if not owner_exists:
                raise HTTPException(status_code=404, detail="Owner user not found.")

        conn.execute(
            """
            UPDATE engagement_events
            SET
                event_type = ?,
                status = ?,
                title = ?,
                event_date = ?,
                start_time = ?,
                end_time = ?,
                location = ?,
                details = ?,
                pnm_id = ?,
                owner_user_id = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                event_type_token,
                status_token,
                title,
                event_date,
                start_time,
                end_time,
                location,
                details,
                pnm_id,
                owner_user_id,
                now_iso(),
                event_id,
            ),
        )
        append_audit_entry(
            conn,
            actor_user_id=int(user["id"]),
            action_type="event_update",
            entity_type="engagement_event",
            entity_id=event_id,
            payload={
                "source_type": row["source_type"],
                "old_status": row["status"],
                "new_status": status_token,
                "old_event_date": row["event_date"],
                "new_event_date": event_date,
            },
        )
        refreshed = conn.execute(
            """
            SELECT
                e.*,
                p.pnm_code,
                p.first_name AS pnm_first_name,
                p.last_name AS pnm_last_name,
                owner.username AS owner_username,
                owner.role AS owner_role,
                owner.emoji AS owner_emoji,
                creator.username AS created_by_username
            FROM engagement_events e
            LEFT JOIN pnms p ON p.id = e.pnm_id
            LEFT JOIN users owner ON owner.id = e.owner_user_id
            LEFT JOIN users creator ON creator.id = e.created_by
            WHERE e.id = ?
            """,
            (event_id,),
        ).fetchone()
    return {"event": engagement_event_payload(refreshed)}


def rush_event_payload(row: sqlite3.Row) -> dict[str, Any]:
    details = row["details"] if "details" in row.keys() else ""
    google_calendar_url = None
    try:
        google_calendar_url = build_google_calendar_generic_event_url(
            title=row["title"],
            event_date=row["event_date"],
            details=details,
            location=row["location"] or "",
            start_time=row["start_time"],
            end_time=row["end_time"],
        )
    except ValueError:
        google_calendar_url = None
    return {
        "event_id": int(row["id"]),
        "title": row["title"],
        "event_type": row["event_type"],
        "event_date": row["event_date"],
        "start_time": row["start_time"],
        "end_time": row["end_time"],
        "location": row["location"],
        "details": details,
        "is_official": bool(row["is_official"]),
        "is_cancelled": bool(row["is_cancelled"]) if "is_cancelled" in row.keys() else False,
        "created_by": int(row["created_by"]),
        "created_by_username": row["created_by_username"] if "created_by_username" in row.keys() else None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "google_calendar_url": google_calendar_url,
    }


@app.get("/api/rush-events")
def list_rush_events(
    include_past: bool = False,
    limit: int = 300,
    _: sqlite3.Row = Depends(current_user),
) -> dict[str, Any]:
    max_limit = max(1, min(1000, int(limit)))
    with db_session() as conn:
        if include_past:
            rows = conn.execute(
                """
                SELECT
                    e.*,
                    u.username AS created_by_username
                FROM rush_events e
                JOIN users u ON u.id = e.created_by
                WHERE e.is_cancelled = 0
                ORDER BY e.event_date ASC, COALESCE(e.start_time, '23:59') ASC, e.id ASC
                LIMIT ?
                """,
                (max_limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT
                    e.*,
                    u.username AS created_by_username
                FROM rush_events e
                JOIN users u ON u.id = e.created_by
                WHERE e.is_cancelled = 0
                  AND e.event_date >= date('now', '-3 day')
                ORDER BY e.event_date ASC, COALESCE(e.start_time, '23:59') ASC, e.id ASC
                LIMIT ?
                """,
                (max_limit,),
            ).fetchall()
    return {"events": [rush_event_payload(row) for row in rows]}


@app.post("/api/rush-events")
def create_rush_event(payload: RushEventCreateRequest, user: sqlite3.Row = Depends(require_head)) -> dict[str, Any]:
    if payload.end_time and not payload.start_time:
        raise HTTPException(status_code=400, detail="End time requires a start time.")
    if payload.start_time and payload.end_time and payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="End time must be after start time.")

    now = now_iso()
    title = payload.title.strip()
    details = payload.details.strip()
    location = payload.location.strip()

    with db_session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO rush_events (
                title,
                event_type,
                event_date,
                start_time,
                end_time,
                location,
                details,
                is_official,
                is_cancelled,
                created_by,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
            """,
            (
                title,
                payload.event_type,
                payload.event_date,
                payload.start_time,
                payload.end_time,
                location,
                details,
                1 if payload.is_official else 0,
                user["id"],
                now,
                now,
            ),
        )
        event_id = int(cursor.lastrowid)
        sync_engagement_event_from_rush_event(conn, event_id)
        append_audit_entry(
            conn,
            actor_user_id=int(user["id"]),
            action_type="rush_event_create",
            entity_type="rush_event",
            entity_id=event_id,
            payload={
                "event_type": payload.event_type,
                "event_date": payload.event_date,
                "is_official": bool(payload.is_official),
            },
        )
        created = conn.execute(
            """
            SELECT
                e.*,
                u.username AS created_by_username
            FROM rush_events e
            JOIN users u ON u.id = e.created_by
            WHERE e.id = ?
            """,
            (event_id,),
        ).fetchone()
        evaluate_weekly_goal_completions(conn)

        recipient_rows = conn.execute(
            "SELECT id FROM users WHERE is_approved = 1 AND id != ?",
            (user["id"],),
        ).fetchall()
        recipients = [int(row["id"]) for row in recipient_rows]
        event_clock = payload.start_time or "All Day"
        create_notifications_for_users(
            conn,
            recipients,
            notif_type="rush_event",
            title=f"New Rush Event: {title}",
            body=f"{payload.event_date} | {event_clock}",
            link_path="/calendar",
        )

    return {"event": rush_event_payload(created)}


@app.patch("/api/rush-events/{event_id}")
def update_rush_event(
    event_id: int,
    payload: RushEventUpdateRequest,
    user: sqlite3.Row = Depends(require_head),
) -> dict[str, Any]:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM rush_events WHERE id = ?", (event_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Rush event not found.")

        title = payload.title.strip() if payload.title is not None else row["title"]
        event_type = payload.event_type if payload.event_type is not None else row["event_type"]
        event_date = payload.event_date if payload.event_date is not None else row["event_date"]
        start_time = payload.start_time if payload.start_time is not None else row["start_time"]
        end_time = payload.end_time if payload.end_time is not None else row["end_time"]
        location = payload.location.strip() if payload.location is not None else row["location"]
        details = payload.details.strip() if payload.details is not None else row["details"]
        is_official = payload.is_official if payload.is_official is not None else bool(row["is_official"])
        is_cancelled = payload.is_cancelled if payload.is_cancelled is not None else bool(row["is_cancelled"])

        if end_time and not start_time:
            raise HTTPException(status_code=400, detail="End time requires a start time.")
        if start_time and end_time and end_time <= start_time:
            raise HTTPException(status_code=400, detail="End time must be after start time.")

        conn.execute(
            """
            UPDATE rush_events
            SET
                title = ?,
                event_type = ?,
                event_date = ?,
                start_time = ?,
                end_time = ?,
                location = ?,
                details = ?,
                is_official = ?,
                is_cancelled = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                title,
                event_type,
                event_date,
                start_time,
                end_time,
                location,
                details,
                1 if is_official else 0,
                1 if is_cancelled else 0,
                now_iso(),
                event_id,
            ),
        )
        sync_engagement_event_from_rush_event(conn, event_id)
        append_audit_entry(
            conn,
            actor_user_id=int(user["id"]),
            action_type="rush_event_update",
            entity_type="rush_event",
            entity_id=event_id,
            payload={
                "event_type": event_type,
                "event_date": event_date,
                "is_cancelled": bool(is_cancelled),
            },
        )
        refreshed = conn.execute(
            """
            SELECT
                e.*,
                u.username AS created_by_username
            FROM rush_events e
            JOIN users u ON u.id = e.created_by
            WHERE e.id = ?
            """,
            (event_id,),
        ).fetchone()

    return {"event": rush_event_payload(refreshed)}


@app.delete("/api/rush-events/{event_id}")
def delete_rush_event(event_id: int, user: sqlite3.Row = Depends(require_head)) -> dict[str, str]:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM rush_events WHERE id = ?", (event_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Rush event not found.")
        conn.execute("UPDATE rush_events SET is_cancelled = 1, updated_at = ? WHERE id = ?", (now_iso(), event_id))
        sync_engagement_event_from_rush_event(conn, event_id)
        append_audit_entry(
            conn,
            actor_user_id=int(user["id"]),
            action_type="rush_event_cancel",
            entity_type="rush_event",
            entity_id=event_id,
            payload={"event_type": row["event_type"], "event_date": row["event_date"]},
        )
    return {"message": "Rush event removed."}


@app.get("/api/rush-calendar")
def rush_calendar(
    request: Request,
    include_past: bool = False,
    limit: int = 500,
    _: sqlite3.Row = Depends(current_user),
) -> dict[str, Any]:
    max_limit = max(20, min(1200, int(limit)))
    with db_session() as conn:
        if include_past:
            event_rows = conn.execute(
                """
                SELECT
                    e.*,
                    u.username AS created_by_username
                FROM rush_events e
                JOIN users u ON u.id = e.created_by
                WHERE e.is_cancelled = 0
                ORDER BY e.event_date ASC, COALESCE(e.start_time, '23:59') ASC, e.id ASC
                LIMIT ?
                """,
                (max_limit,),
            ).fetchall()
            lunch_rows = conn.execute(
                """
                SELECT
                    l.*,
                    p.pnm_code,
                    p.first_name,
                    p.last_name,
                    u.username,
                    ao.username AS assigned_officer_username
                FROM lunches l
                JOIN pnms p ON p.id = l.pnm_id
                JOIN users u ON u.id = l.user_id
                LEFT JOIN users ao ON ao.id = p.assigned_officer_id
                ORDER BY l.lunch_date ASC, COALESCE(l.start_time, '23:59') ASC, l.id ASC
                LIMIT ?
                """,
                (max_limit,),
            ).fetchall()
        else:
            event_rows = conn.execute(
                """
                SELECT
                    e.*,
                    u.username AS created_by_username
                FROM rush_events e
                JOIN users u ON u.id = e.created_by
                WHERE e.is_cancelled = 0
                  AND e.event_date >= date('now', '-3 day')
                ORDER BY e.event_date ASC, COALESCE(e.start_time, '23:59') ASC, e.id ASC
                LIMIT ?
                """,
                (max_limit,),
            ).fetchall()
            lunch_rows = conn.execute(
                """
                SELECT
                    l.*,
                    p.pnm_code,
                    p.first_name,
                    p.last_name,
                    u.username,
                    ao.username AS assigned_officer_username
                FROM lunches l
                JOIN pnms p ON p.id = l.pnm_id
                JOIN users u ON u.id = l.user_id
                LEFT JOIN users ao ON ao.id = p.assigned_officer_id
                WHERE l.lunch_date >= date('now', '-3 day')
                ORDER BY l.lunch_date ASC, COALESCE(l.start_time, '23:59') ASC, l.id ASC
                LIMIT ?
                """,
                (max_limit,),
            ).fetchall()

    items: list[dict[str, Any]] = []
    for row in event_rows:
        event = rush_event_payload(row)
        items.append(
            {
                "item_type": "rush_event",
                "event_id": event["event_id"],
                "title": event["title"],
                "event_type": event["event_type"],
                "event_date": event["event_date"],
                "start_time": event["start_time"],
                "end_time": event["end_time"],
                "location": event["location"],
                "details": event["details"],
                "is_official": event["is_official"],
                "created_by_username": event["created_by_username"],
                "google_calendar_url": event["google_calendar_url"],
            }
        )

    for row in lunch_rows:
        pnm_name = f"{row['first_name']} {row['last_name']}"
        google_calendar_url = None
        try:
            google_calendar_url = build_google_calendar_event_url(
                pnm_name=pnm_name,
                pnm_code=row["pnm_code"],
                lunch_date=row["lunch_date"],
                notes=row["notes"] or "",
                location=row["location"] or "",
                start_time=row["start_time"],
                end_time=row["end_time"],
                logged_by_username=row["username"],
            )
        except ValueError:
            google_calendar_url = None
        items.append(
            {
                "item_type": "lunch",
                "lunch_id": int(row["id"]),
                "title": f"Lunch with {pnm_name}",
                "event_type": "lunch",
                "event_date": row["lunch_date"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "location": row["location"],
                "details": row["notes"] or "",
                "is_official": True,
                "created_by_username": row["username"],
                "pnm_code": row["pnm_code"],
                "pnm_name": pnm_name,
                "assigned_officer_username": row["assigned_officer_username"] or "",
                "google_calendar_url": google_calendar_url,
            }
        )

    items.sort(
        key=lambda item: (
            item["event_date"],
            item["start_time"] or "23:59",
            0 if item["item_type"] == "rush_event" else 1,
            item.get("event_id") or item.get("lunch_id") or 0,
        )
    )
    if len(items) > max_limit:
        items = items[:max_limit]

    today = date.today()
    week_start, week_end = week_bounds_for(today)
    week_start_s = week_start.isoformat()
    week_end_s = week_end.isoformat()
    official_count = sum(1 for item in items if item["item_type"] == "rush_event" and item["is_official"])
    lunch_count = sum(1 for item in items if item["item_type"] == "lunch")
    this_week_count = sum(1 for item in items if week_start_s <= item["event_date"] <= week_end_s)

    return {
        "items": items,
        "stats": {
            "total_count": len(items),
            "official_event_count": official_count,
            "lunch_count": lunch_count,
            "this_week_count": this_week_count,
        },
        "calendar_share": calendar_share_payload(request, current_tenant()),
    }


@app.get("/api/tasks/weekly")
def list_weekly_goals(
    include_archived: bool = False,
    _: sqlite3.Row = Depends(current_user),
) -> dict[str, Any]:
    with db_session() as conn:
        if include_archived:
            rows = conn.execute(
                """
                SELECT
                    g.*,
                    assignee.username AS assigned_username,
                    creator.username AS created_by_username
                FROM weekly_goals g
                LEFT JOIN users assignee ON assignee.id = g.assigned_user_id
                LEFT JOIN users creator ON creator.id = g.created_by
                ORDER BY g.week_start DESC, g.created_at DESC
                """
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT
                    g.*,
                    assignee.username AS assigned_username,
                    creator.username AS created_by_username
                FROM weekly_goals g
                LEFT JOIN users assignee ON assignee.id = g.assigned_user_id
                LEFT JOIN users creator ON creator.id = g.created_by
                WHERE g.is_archived = 0
                ORDER BY g.week_start DESC, g.created_at DESC
                """
            ).fetchall()
        goals = [weekly_goal_payload(conn, row) for row in rows]

    total = len(goals)
    active_count = sum(1 for goal in goals if goal["status"] == "active")
    completed_count = sum(1 for goal in goals if goal["is_completed"])
    overdue_count = sum(1 for goal in goals if goal["status"] == "overdue")
    completion_rate = round((completed_count / total) * 100, 1) if total else 0.0

    return {
        "goals": goals,
        "summary": {
            "total": total,
            "active": active_count,
            "completed": completed_count,
            "overdue": overdue_count,
            "completion_rate": completion_rate,
        },
        "metric_options": [
            {"value": metric, "label": label}
            for metric, label in WEEKLY_GOAL_METRIC_LABELS.items()
        ],
    }


@app.post("/api/tasks/weekly")
def create_weekly_goal(payload: WeeklyGoalCreateRequest, user: sqlite3.Row = Depends(require_officer)) -> dict[str, Any]:
    try:
        week_start, week_end = resolve_goal_week_span(payload.week_start, payload.week_end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with db_session() as conn:
        assigned_user_id = payload.assigned_user_id
        if assigned_user_id is not None:
            assigned = conn.execute(
                "SELECT id, username FROM users WHERE id = ? AND is_approved = 1",
                (assigned_user_id,),
            ).fetchone()
            if not assigned:
                raise HTTPException(status_code=404, detail="Assigned user not found.")
        created_at = now_iso()
        cursor = conn.execute(
            """
            INSERT INTO weekly_goals (
                title,
                description,
                metric_type,
                target_count,
                manual_progress,
                week_start,
                week_end,
                assigned_user_id,
                created_by,
                is_archived,
                completed_at,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, 0, NULL, ?, ?)
            """,
            (
                payload.title.strip(),
                payload.description.strip(),
                payload.metric_type,
                payload.target_count,
                week_start,
                week_end,
                assigned_user_id,
                user["id"],
                created_at,
                created_at,
            ),
        )
        goal_id = int(cursor.lastrowid)
        evaluate_weekly_goal_completions(conn)
        row = conn.execute(
            """
            SELECT
                g.*,
                assignee.username AS assigned_username,
                creator.username AS created_by_username
            FROM weekly_goals g
            LEFT JOIN users assignee ON assignee.id = g.assigned_user_id
            LEFT JOIN users creator ON creator.id = g.created_by
            WHERE g.id = ?
            """,
            (goal_id,),
        ).fetchone()

        if row["assigned_user_id"] is not None and int(row["assigned_user_id"]) != int(user["id"]):
            create_notification(
                conn,
                user_id=int(row["assigned_user_id"]),
                notif_type="goal_assigned",
                title=f"New Weekly Goal: {row['title']}",
                body=f"Target: {row['target_count']} {WEEKLY_GOAL_METRIC_LABELS.get(row['metric_type'], row['metric_type'])}",
                link_path="/calendar",
            )
        elif row["assigned_user_id"] is None:
            officer_rows = conn.execute(
                "SELECT id FROM users WHERE is_approved = 1 AND role IN (?, ?)",
                (ROLE_HEAD, ROLE_RUSH_OFFICER),
            ).fetchall()
            create_notifications_for_users(
                conn,
                [int(item["id"]) for item in officer_rows if int(item["id"]) != int(user["id"])],
                notif_type="goal_created",
                title=f"Team Weekly Goal: {row['title']}",
                body=f"Target: {row['target_count']} {WEEKLY_GOAL_METRIC_LABELS.get(row['metric_type'], row['metric_type'])}",
                link_path="/calendar",
            )

        goal_payload = weekly_goal_payload(conn, row)

    return {"goal": goal_payload}


@app.patch("/api/tasks/weekly/{goal_id}")
def update_weekly_goal(
    goal_id: int,
    payload: WeeklyGoalUpdateRequest,
    user: sqlite3.Row = Depends(require_officer),
) -> dict[str, Any]:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM weekly_goals WHERE id = ?", (goal_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Weekly goal not found.")
        if user["role"] != ROLE_HEAD and int(row["created_by"]) != int(user["id"]):
            raise HTTPException(status_code=403, detail="Only heads or goal creators can edit goals.")

        assigned_user_id = row["assigned_user_id"]
        if payload.assigned_user_id is not None:
            assigned = conn.execute(
                "SELECT id FROM users WHERE id = ? AND is_approved = 1",
                (payload.assigned_user_id,),
            ).fetchone()
            if not assigned:
                raise HTTPException(status_code=404, detail="Assigned user not found.")
            assigned_user_id = payload.assigned_user_id

        metric_type = payload.metric_type if payload.metric_type is not None else row["metric_type"]
        target_count = int(payload.target_count) if payload.target_count is not None else int(row["target_count"])
        title = payload.title.strip() if payload.title is not None else row["title"]
        description = payload.description.strip() if payload.description is not None else row["description"]
        week_start_raw = payload.week_start if payload.week_start is not None else row["week_start"]
        week_end_raw = payload.week_end if payload.week_end is not None else row["week_end"]
        try:
            week_start, week_end = resolve_goal_week_span(week_start_raw, week_end_raw)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        is_archived = bool(payload.is_archived) if payload.is_archived is not None else bool(row["is_archived"])
        completed_at = row["completed_at"]
        if payload.complete_now is True:
            completed_at = now_iso()
        elif payload.complete_now is False:
            completed_at = None

        conn.execute(
            """
            UPDATE weekly_goals
            SET
                title = ?,
                description = ?,
                metric_type = ?,
                target_count = ?,
                week_start = ?,
                week_end = ?,
                assigned_user_id = ?,
                is_archived = ?,
                completed_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                title,
                description,
                metric_type,
                target_count,
                week_start,
                week_end,
                assigned_user_id,
                1 if is_archived else 0,
                completed_at,
                now_iso(),
                goal_id,
            ),
        )
        evaluate_weekly_goal_completions(conn)
        refreshed = conn.execute(
            """
            SELECT
                g.*,
                assignee.username AS assigned_username,
                creator.username AS created_by_username
            FROM weekly_goals g
            LEFT JOIN users assignee ON assignee.id = g.assigned_user_id
            LEFT JOIN users creator ON creator.id = g.created_by
            WHERE g.id = ?
            """,
            (goal_id,),
        ).fetchone()
        goal_payload = weekly_goal_payload(conn, refreshed)

    return {"goal": goal_payload}


@app.post("/api/tasks/weekly/{goal_id}/progress")
def add_weekly_goal_progress(
    goal_id: int,
    payload: WeeklyGoalProgressRequest,
    user: sqlite3.Row = Depends(require_officer),
) -> dict[str, Any]:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM weekly_goals WHERE id = ?", (goal_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Weekly goal not found.")
        if row["metric_type"] != "manual":
            raise HTTPException(status_code=400, detail="Only manual goals support direct progress updates.")
        if user["role"] != ROLE_HEAD and int(row["created_by"]) != int(user["id"]):
            if row["assigned_user_id"] is None or int(row["assigned_user_id"]) != int(user["id"]):
                raise HTTPException(status_code=403, detail="Only heads, creators, or assignees can update this goal.")
        next_progress = int(row["manual_progress"] or 0) + int(payload.delta)
        conn.execute(
            "UPDATE weekly_goals SET manual_progress = ?, updated_at = ? WHERE id = ?",
            (next_progress, now_iso(), goal_id),
        )
        evaluate_weekly_goal_completions(conn)
        refreshed = conn.execute(
            """
            SELECT
                g.*,
                assignee.username AS assigned_username,
                creator.username AS created_by_username
            FROM weekly_goals g
            LEFT JOIN users assignee ON assignee.id = g.assigned_user_id
            LEFT JOIN users creator ON creator.id = g.created_by
            WHERE g.id = ?
            """,
            (goal_id,),
        ).fetchone()
        goal_payload = weekly_goal_payload(conn, refreshed)
    return {"goal": goal_payload}


@app.get("/api/notifications")
def list_notifications(
    limit: int = 80,
    user: sqlite3.Row = Depends(current_user),
) -> dict[str, Any]:
    max_limit = max(1, min(250, int(limit)))
    with db_session() as conn:
        unread_row = conn.execute(
            "SELECT COUNT(*) AS c FROM notifications WHERE user_id = ? AND is_read = 0",
            (user["id"],),
        ).fetchone()
        rows = conn.execute(
            """
            SELECT *
            FROM notifications
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (user["id"], max_limit),
        ).fetchall()
    return {
        "unread_count": int(unread_row["c"]),
        "notifications": [
            {
                "notification_id": int(row["id"]),
                "notif_type": row["notif_type"],
                "title": row["title"],
                "body": row["body"],
                "link_path": row["link_path"],
                "is_read": bool(row["is_read"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ],
    }


@app.get("/api/notifications/digest")
def notification_digest(
    period: str = "daily",
    include_read: bool = False,
    max_items: int = 40,
    user: sqlite3.Row = Depends(current_user),
) -> dict[str, Any]:
    try:
        period_token = normalize_digest_period(period)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    window_modifier = "-1 day" if period_token == "daily" else "-6 day"
    safe_limit = max(5, min(200, int(max_items)))

    with db_session() as conn:
        unread_row = conn.execute(
            "SELECT COUNT(*) AS c FROM notifications WHERE user_id = ? AND is_read = 0",
            (user["id"],),
        ).fetchone()

        if include_read:
            digest_rows = conn.execute(
                """
                SELECT *
                FROM notifications
                WHERE user_id = ?
                  AND date(created_at) >= date('now', ?)
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (user["id"], window_modifier, safe_limit),
            ).fetchall()
            type_rows = conn.execute(
                """
                SELECT notif_type, COUNT(*) AS c
                FROM notifications
                WHERE user_id = ?
                  AND date(created_at) >= date('now', ?)
                GROUP BY notif_type
                ORDER BY c DESC, notif_type ASC
                """,
                (user["id"], window_modifier),
            ).fetchall()
        else:
            digest_rows = conn.execute(
                """
                SELECT *
                FROM notifications
                WHERE user_id = ?
                  AND is_read = 0
                  AND date(created_at) >= date('now', ?)
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (user["id"], window_modifier, safe_limit),
            ).fetchall()
            type_rows = conn.execute(
                """
                SELECT notif_type, COUNT(*) AS c
                FROM notifications
                WHERE user_id = ?
                  AND is_read = 0
                  AND date(created_at) >= date('now', ?)
                GROUP BY notif_type
                ORDER BY c DESC, notif_type ASC
                """,
                (user["id"], window_modifier),
            ).fetchall()

        assignment_where = ""
        assignment_params: list[Any] = []
        if user["role"] != ROLE_HEAD:
            assignment_where = (
                "WHERE EXISTS (SELECT 1 FROM pnm_officer_assignments pa WHERE pa.pnm_id = p.id AND pa.officer_user_id = ?) "
                "OR (p.assigned_officer_id = ? AND NOT EXISTS (SELECT 1 FROM pnm_officer_assignments pa2 WHERE pa2.pnm_id = p.id))"
            )
            assignment_params = [user["id"], user["id"]]

        assignment_rows = conn.execute(
            f"""
            SELECT
                p.id,
                p.pnm_code,
                p.first_name,
                p.last_name,
                p.assignment_status,
                p.assignment_due_date
            FROM pnms p
            {assignment_where}
            ORDER BY p.assignment_priority DESC, p.weighted_total DESC, p.last_name ASC
            """,
            tuple(assignment_params),
        ).fetchall()

        touchpoint_rows = conn.execute(
            f"""
            SELECT
                p.id,
                p.pnm_code,
                p.first_name,
                p.last_name,
                p.assignment_status,
                MAX(l.lunch_date) AS last_lunch_date
            FROM pnms p
            LEFT JOIN lunches l ON l.pnm_id = p.id
            {assignment_where}
            GROUP BY p.id, p.pnm_code, p.first_name, p.last_name, p.assignment_status
            ORDER BY p.weighted_total DESC, p.last_name ASC
            LIMIT 300
            """,
            tuple(assignment_params),
        ).fetchall()

    by_type = [{"notif_type": row["notif_type"], "count": int(row["c"])} for row in type_rows]
    assignment_alerts: dict[str, int] = {"overdue": 0, "due_soon": 0, "needs_help": 0, "unassigned": 0}
    flagged_assignments: list[dict[str, Any]] = []
    for row in assignment_rows:
        status_token = str(row["assignment_status"] or "").strip().lower() or "unassigned"
        if status_token not in ASSIGNMENT_STATUSES:
            status_token = "unassigned"
        due_state = assignment_due_state(status_token, row["assignment_due_date"])
        if status_token == "needs_help":
            assignment_alerts["needs_help"] += 1
        if status_token == "unassigned":
            assignment_alerts["unassigned"] += 1
        if due_state == "overdue":
            assignment_alerts["overdue"] += 1
        elif due_state == "due_soon":
            assignment_alerts["due_soon"] += 1
        if status_token == "needs_help" or due_state in {"overdue", "due_soon"}:
            flagged_assignments.append(
                {
                    "pnm_id": int(row["id"]),
                    "pnm_code": row["pnm_code"],
                    "name": f"{row['first_name']} {row['last_name']}",
                    "assignment_status": status_token,
                    "due_state": due_state,
                    "due_date": row["assignment_due_date"],
                }
            )

    stale_touchpoints: list[dict[str, Any]] = []
    for row in touchpoint_rows:
        last_lunch = row["last_lunch_date"]
        is_stale = (last_lunch is None) or str(last_lunch) < (date.today() - timedelta(days=10)).isoformat()
        if not is_stale:
            continue
        stale_touchpoints.append(
            {
                "pnm_id": int(row["id"]),
                "pnm_code": row["pnm_code"],
                "name": f"{row['first_name']} {row['last_name']}",
                "assignment_status": row["assignment_status"] or "unassigned",
                "last_lunch_date": last_lunch,
            }
        )

    return {
        "period": period_token,
        "include_read": include_read,
        "window_start": (date.today() - timedelta(days=1 if period_token == "daily" else 6)).isoformat(),
        "unread_count": int(unread_row["c"]),
        "digest_count": len(digest_rows),
        "by_type": by_type,
        "assignment_alerts": assignment_alerts,
        "flagged_assignments": flagged_assignments[:30],
        "stale_touchpoints": stale_touchpoints[:30],
        "notifications": [
            {
                "notification_id": int(row["id"]),
                "notif_type": row["notif_type"],
                "title": row["title"],
                "body": row["body"],
                "link_path": row["link_path"],
                "is_read": bool(row["is_read"]),
                "created_at": row["created_at"],
            }
            for row in digest_rows
        ],
    }


@app.post("/api/notifications/digest")
def broadcast_notification_digest(
    payload: NotificationDigestBroadcastRequest,
    head_user: sqlite3.Row = Depends(require_head),
) -> dict[str, Any]:
    window_modifier = "-1 day" if payload.period == "daily" else "-6 day"
    with db_session() as conn:
        if payload.recipients == "all_approved":
            recipient_rows = conn.execute(
                "SELECT id, username FROM users WHERE is_approved = 1 AND id != ?",
                (head_user["id"],),
            ).fetchall()
        else:
            recipient_rows = conn.execute(
                """
                SELECT id, username
                FROM users
                WHERE is_approved = 1
                  AND role IN (?, ?)
                  AND id != ?
                """,
                (ROLE_HEAD, ROLE_RUSH_OFFICER, head_user["id"]),
            ).fetchall()

        dispatched = 0
        for recipient in recipient_rows:
            if payload.include_read:
                notif_count = conn.execute(
                    """
                    SELECT COUNT(*) AS c
                    FROM notifications
                    WHERE user_id = ?
                      AND date(created_at) >= date('now', ?)
                    """,
                    (recipient["id"], window_modifier),
                ).fetchone()
            else:
                notif_count = conn.execute(
                    """
                    SELECT COUNT(*) AS c
                    FROM notifications
                    WHERE user_id = ?
                      AND is_read = 0
                      AND date(created_at) >= date('now', ?)
                    """,
                    (recipient["id"], window_modifier),
                ).fetchone()

            alert_rows = conn.execute(
                """
                SELECT assignment_status, assignment_due_date
                FROM pnms
                WHERE
                    EXISTS (
                        SELECT 1
                        FROM pnm_officer_assignments pa
                        WHERE pa.pnm_id = pnms.id
                          AND pa.officer_user_id = ?
                    )
                    OR (
                        assigned_officer_id = ?
                        AND NOT EXISTS (
                            SELECT 1
                            FROM pnm_officer_assignments pa2
                            WHERE pa2.pnm_id = pnms.id
                        )
                    )
                """,
                (recipient["id"], recipient["id"]),
            ).fetchall()
            overdue_count = 0
            due_soon_count = 0
            needs_help_count = 0
            for alert_row in alert_rows:
                status_token = str(alert_row["assignment_status"] or "").strip().lower() or "unassigned"
                if status_token == "needs_help":
                    needs_help_count += 1
                due_state = assignment_due_state(status_token, alert_row["assignment_due_date"])
                if due_state == "overdue":
                    overdue_count += 1
                elif due_state == "due_soon":
                    due_soon_count += 1

            body = (
                f"{payload.period.title()} digest: {int(notif_count['c'] or 0)} notification(s), "
                f"{overdue_count} overdue assignment(s), {due_soon_count} due soon, {needs_help_count} needs-help."
            )
            create_notification(
                conn,
                user_id=int(recipient["id"]),
                notif_type="digest",
                title=f"{payload.period.title()} Team Digest",
                body=body[:500],
                link_path="/calendar",
            )
            dispatched += 1

        append_audit_entry(
            conn,
            actor_user_id=int(head_user["id"]),
            action_type="digest_broadcast",
            entity_type="notification",
            entity_id=None,
            payload={
                "period": payload.period,
                "recipients": payload.recipients,
                "dispatched": dispatched,
                "include_read": payload.include_read,
            },
        )

    return {
        "message": f"Digest sent to {dispatched} user(s).",
        "period": payload.period,
        "recipients": payload.recipients,
        "dispatched": dispatched,
    }


@app.post("/api/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    with db_session() as conn:
        cursor = conn.execute(
            """
            UPDATE notifications
            SET is_read = 1
            WHERE id = ? AND user_id = ?
            """,
            (notification_id, user["id"]),
        )
        if cursor.rowcount <= 0:
            raise HTTPException(status_code=404, detail="Notification not found.")
        unread_row = conn.execute(
            "SELECT COUNT(*) AS c FROM notifications WHERE user_id = ? AND is_read = 0",
            (user["id"],),
        ).fetchone()
    return {"message": "Notification marked read.", "unread_count": int(unread_row["c"])}


@app.post("/api/notifications/read-all")
def mark_all_notifications_read(user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    with db_session() as conn:
        conn.execute(
            "UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0",
            (user["id"],),
        )
    return {"message": "All notifications marked read.", "unread_count": 0}


@app.get("/api/chat/officer")
def list_officer_chat_messages(
    limit: int = 140,
    user: sqlite3.Row = Depends(require_officer),
) -> dict[str, Any]:
    max_limit = max(10, min(400, int(limit)))
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT
                m.*,
                u.username,
                u.role,
                u.emoji
            FROM officer_chat_messages m
            JOIN users u ON u.id = m.sender_id
            ORDER BY m.id DESC
            LIMIT ?
            """,
            (max_limit,),
        ).fetchall()
        message_ids = [int(row["id"]) for row in rows]
        tags_by_message: dict[int, list[str]] = {}
        mentions_by_message: dict[int, list[dict[str, Any]]] = {}
        if message_ids:
            message_ids_json = json.dumps(message_ids)
            tag_rows = conn.execute(
                """
                SELECT message_id, tag
                FROM officer_chat_tags
                WHERE message_id IN (SELECT CAST(value AS INTEGER) FROM json_each(?))
                ORDER BY tag ASC
                """,
                (message_ids_json,),
            ).fetchall()
            for tag_row in tag_rows:
                message_id = int(tag_row["message_id"])
                tags_by_message.setdefault(message_id, []).append(tag_row["tag"])
            mention_rows = conn.execute(
                """
                SELECT
                    m.message_id,
                    u.id AS user_id,
                    u.username
                FROM officer_chat_mentions m
                JOIN users u ON u.id = m.user_id
                WHERE m.message_id IN (SELECT CAST(value AS INTEGER) FROM json_each(?))
                ORDER BY m.id ASC
                """,
                (message_ids_json,),
            ).fetchall()
            for mention_row in mention_rows:
                message_id = int(mention_row["message_id"])
                mentions_by_message.setdefault(message_id, []).append(
                    {"user_id": int(mention_row["user_id"]), "username": mention_row["username"]}
                )

    messages = []
    for row in reversed(rows):
        message_id = int(row["id"])
        mentions = mentions_by_message.get(message_id, [])
        messages.append(
            {
                "message_id": message_id,
                "message": row["message"],
                "tags": tags_by_message.get(message_id, []),
                "mentions": mentions,
                "mentions_me": any(int(mention["user_id"]) == int(user["id"]) for mention in mentions),
                "created_at": row["created_at"],
                "edited_at": row["edited_at"],
                "from_me": int(row["sender_id"]) == int(user["id"]),
                "sender": {
                    "user_id": int(row["sender_id"]),
                    "username": row["username"],
                    "role": row["role"],
                    "emoji": row["emoji"],
                },
            }
        )

    return {"messages": messages}


@app.post("/api/chat/officer")
def create_officer_chat_message(
    payload: OfficerChatMessageCreateRequest,
    user: sqlite3.Row = Depends(require_officer),
) -> dict[str, Any]:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    tags = parse_chat_tags(payload.tags, message)
    mention_usernames = extract_message_mentions(message)
    tags_csv = ",".join(tags)

    with db_session() as conn:
        created_at = now_iso()
        cursor = conn.execute(
            """
            INSERT INTO officer_chat_messages (sender_id, message, tags, created_at, edited_at)
            VALUES (?, ?, ?, ?, NULL)
            """,
            (user["id"], message, tags_csv, created_at),
        )
        message_id = int(cursor.lastrowid)
        for tag in tags:
            conn.execute(
                "INSERT OR IGNORE INTO officer_chat_tags (message_id, tag, created_at) VALUES (?, ?, ?)",
                (message_id, tag, created_at),
            )

        mentioned_rows: list[sqlite3.Row] = []
        if mention_usernames:
            mentioned_rows = conn.execute(
                """
                SELECT id, username
                FROM users
                WHERE is_approved = 1
                  AND lower(username) IN (SELECT CAST(value AS TEXT) FROM json_each(?))
                """,
                (json.dumps(mention_usernames),),
            ).fetchall()
            for mentioned in mentioned_rows:
                conn.execute(
                    "INSERT OR IGNORE INTO officer_chat_mentions (message_id, user_id, created_at) VALUES (?, ?, ?)",
                    (message_id, int(mentioned["id"]), created_at),
                )
                if int(mentioned["id"]) != int(user["id"]):
                    create_notification(
                        conn,
                        user_id=int(mentioned["id"]),
                        notif_type="chat_mention",
                        title=f"Mentioned by {user['username']}",
                        body=message[:220],
                        link_path="/calendar",
                    )

        evaluate_weekly_goal_completions(conn)

        sender = conn.execute(
            "SELECT id, username, role, emoji FROM users WHERE id = ?",
            (user["id"],),
        ).fetchone()

    mentions = [{"user_id": int(item["id"]), "username": item["username"]} for item in mentioned_rows]
    return {
        "message": {
            "message_id": message_id,
            "message": message,
            "tags": tags,
            "mentions": mentions,
            "mentions_me": any(int(item["id"]) == int(user["id"]) for item in mentioned_rows),
            "created_at": created_at,
            "edited_at": None,
            "from_me": True,
            "sender": {
                "user_id": int(sender["id"]),
                "username": sender["username"],
                "role": sender["role"],
                "emoji": sender["emoji"],
            },
        }
    }


@app.get("/api/chat/officer/stats")
def officer_chat_stats(_: sqlite3.Row = Depends(require_officer)) -> dict[str, Any]:
    with db_session() as conn:
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS total_messages,
                SUM(CASE WHEN created_at >= datetime('now', '-1 day') THEN 1 ELSE 0 END) AS messages_last_24h,
                SUM(CASE WHEN created_at >= datetime('now', '-6 day') THEN 1 ELSE 0 END) AS messages_last_7d,
                MAX(created_at) AS last_message_at
            FROM officer_chat_messages
            """
        ).fetchone()
        active_senders = conn.execute(
            """
            SELECT COUNT(DISTINCT sender_id) AS c
            FROM officer_chat_messages
            WHERE created_at >= datetime('now', '-6 day')
            """
        ).fetchone()
        top_senders = conn.execute(
            """
            SELECT
                u.id,
                u.username,
                u.role,
                COUNT(*) AS message_count
            FROM officer_chat_messages m
            JOIN users u ON u.id = m.sender_id
            WHERE m.created_at >= datetime('now', '-6 day')
            GROUP BY u.id, u.username, u.role
            ORDER BY message_count DESC, u.username ASC
            LIMIT 8
            """
        ).fetchall()
        top_tags = conn.execute(
            """
            SELECT tag, COUNT(*) AS usage_count
            FROM officer_chat_tags
            GROUP BY tag
            ORDER BY usage_count DESC, tag ASC
            LIMIT 12
            """
        ).fetchall()
        top_mentions = conn.execute(
            """
            SELECT
                u.id,
                u.username,
                COUNT(*) AS mention_count
            FROM officer_chat_mentions m
            JOIN users u ON u.id = m.user_id
            GROUP BY u.id, u.username
            ORDER BY mention_count DESC, u.username ASC
            LIMIT 8
            """
        ).fetchall()

    return {
        "summary": {
            "total_messages": int(totals["total_messages"] or 0),
            "messages_last_24h": int(totals["messages_last_24h"] or 0),
            "messages_last_7d": int(totals["messages_last_7d"] or 0),
            "active_senders_7d": int(active_senders["c"] or 0),
            "last_message_at": totals["last_message_at"],
        },
        "top_senders": [
            {
                "user_id": int(row["id"]),
                "username": row["username"],
                "role": row["role"],
                "message_count": int(row["message_count"]),
            }
            for row in top_senders
        ],
        "top_tags": [
            {"tag": row["tag"], "usage_count": int(row["usage_count"])}
            for row in top_tags
        ],
        "top_mentions": [
            {
                "user_id": int(row["id"]),
                "username": row["username"],
                "mention_count": int(row["mention_count"]),
            }
            for row in top_mentions
        ],
    }


@app.get("/api/dashboard/command-center")
def dashboard_command_center(
    window_hours: int = Query(default=72, ge=24, le=168),
    limit: int = Query(default=30, ge=1, le=100),
    user: sqlite3.Row = Depends(require_officer),
) -> dict[str, Any]:
    window_hours = max(24, min(int(window_hours), 168))
    limit = max(1, min(int(limit), 100))
    now_dt = datetime.now(timezone.utc)
    cutoff_dt = now_dt - timedelta(hours=window_hours)
    cutoff_iso = cutoff_dt.isoformat()

    def parse_timestamp(raw_value: Any) -> datetime | None:
        token = str(raw_value or "").strip()
        if not token:
            return None
        candidate = token.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            try:
                parsed_day = date.fromisoformat(token)
            except ValueError:
                return None
            parsed = datetime(parsed_day.year, parsed_day.month, parsed_day.day, tzinfo=timezone.utc)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            parsed = parsed.astimezone(timezone.utc)
        return parsed

    def newest_timestamp(values: list[str | None]) -> str | None:
        latest_dt: datetime | None = None
        latest_raw: str | None = None
        for raw in values:
            parsed = parse_timestamp(raw)
            if not parsed:
                continue
            if latest_dt is None or parsed > latest_dt:
                latest_dt = parsed
                latest_raw = parsed.isoformat()
        return latest_raw

    urgency_rank = {
        "needs_help": 4,
        "in_progress": 3,
        "assigned": 2,
        "unassigned": 1,
        "completed": 0,
    }

    with db_session() as conn:
        own_rows = conn.execute("SELECT * FROM ratings WHERE user_id = ?", (user["id"],)).fetchall()
        own_rating_by_pnm = {int(row["pnm_id"]): rating_payload(row) for row in own_rows}
        own_updated_at_by_pnm = {int(row["pnm_id"]): row["updated_at"] for row in own_rows}

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
        pnm_ids = [int(row["id"]) for row in pnm_rows]
        links_by_pnm = fetch_assignment_links_for_pnms(conn, pnm_ids=pnm_ids)

        lunch_rows = conn.execute(
            """
            SELECT
                l.pnm_id,
                MAX(COALESCE(l.created_at, l.lunch_date)) AS last_lunch_at
            FROM lunches l
            WHERE l.pnm_id IN (SELECT CAST(value AS INTEGER) FROM json_each(?))
            GROUP BY l.pnm_id
            """,
            (json.dumps(pnm_ids),),
        ).fetchall() if pnm_ids else []
        lunch_by_pnm = {int(row["pnm_id"]): row["last_lunch_at"] for row in lunch_rows}

        rating_touch_rows = conn.execute(
            """
            SELECT pnm_id, MAX(last_seen_at) AS last_rating_activity_at
            FROM (
                SELECT rce.pnm_id, rce.changed_at AS last_seen_at
                FROM rating_comment_events rce
                WHERE rce.pnm_id IN (SELECT CAST(value AS INTEGER) FROM json_each(?))
                UNION ALL
                SELECT r.pnm_id, r.updated_at AS last_seen_at
                FROM ratings r
                WHERE r.pnm_id IN (SELECT CAST(value AS INTEGER) FROM json_each(?))
            ) combined
            GROUP BY pnm_id
            """,
            (json.dumps(pnm_ids), json.dumps(pnm_ids)),
        ).fetchall() if pnm_ids else []
        rating_touch_by_pnm = {int(row["pnm_id"]): row["last_rating_activity_at"] for row in rating_touch_rows}

        recent_change_rows = conn.execute(
            """
            SELECT
                rce.id,
                rce.rating_id,
                rce.pnm_id,
                rce.event_type,
                rce.old_total,
                rce.new_total,
                rce.delta_total,
                rce.comment,
                rce.changed_at,
                u.id AS changed_by_user_id,
                u.username AS changed_by_username,
                u.role AS changed_by_role,
                u.emoji AS changed_by_emoji,
                p.pnm_code,
                p.first_name,
                p.last_name
            FROM rating_comment_events rce
            JOIN users u ON u.id = rce.user_id
            JOIN pnms p ON p.id = rce.pnm_id
            WHERE rce.changed_at >= ?
            ORDER BY rce.changed_at DESC
            LIMIT ?
            """,
            (cutoff_iso, max(30, limit * 3)),
        ).fetchall()

    queue_rows: list[dict[str, Any]] = []
    stale_rows: list[dict[str, Any]] = []

    for row in pnm_rows:
        pnm_id = int(row["id"])
        own_rating = own_rating_by_pnm.get(pnm_id)
        pnm = pnm_payload(
            row,
            own_rating,
            assigned_officer=assigned_officer_payload_from_row(row),
            assigned_officers=links_by_pnm.get(pnm_id, []),
        )

        last_lunch_at = lunch_by_pnm.get(pnm_id)
        last_rating_activity_at = rating_touch_by_pnm.get(pnm_id)
        last_touchpoint_at = newest_timestamp([last_lunch_at, last_rating_activity_at])
        last_touchpoint_dt = parse_timestamp(last_touchpoint_at)
        has_recent_touchpoint = bool(last_touchpoint_dt and last_touchpoint_dt >= cutoff_dt)

        last_rating_by_me_at = own_updated_at_by_pnm.get(pnm_id)
        last_rating_by_me_dt = parse_timestamp(last_rating_by_me_at)
        has_recent_rating_by_me = bool(last_rating_by_me_dt and last_rating_by_me_dt >= cutoff_dt)

        needs_rating_update = False
        stale_reason = ""
        if not last_rating_by_me_dt:
            needs_rating_update = True
            stale_reason = "never_rated"
        elif last_touchpoint_dt and last_rating_by_me_dt < last_touchpoint_dt:
            needs_rating_update = True
            stale_reason = "rating_older_than_recent_touchpoint"
        elif has_recent_touchpoint and not has_recent_rating_by_me:
            needs_rating_update = True
            stale_reason = "no_recent_rating"

        assignment_status = str(pnm.get("assignment_status") or "").strip().lower()
        assignment_urgency = urgency_rank.get(assignment_status, 0)
        assigned_to_me = any(
            int(item.get("user_id") or 0) == int(user["id"])
            for item in (pnm.get("assigned_officers") or [])
            if isinstance(item, dict)
        ) or int(pnm.get("assigned_officer_id") or 0) == int(user["id"])

        touchpoint_epoch = int(last_touchpoint_dt.timestamp()) if last_touchpoint_dt else 0
        weighted_total = float(pnm.get("weighted_total") or 0.0)
        priority_score = (
            (1_000_000_000 if has_recent_touchpoint else 0)
            + (100_000_000 if needs_rating_update else 0)
            + (10_000_000 if assigned_to_me else 0)
            + assignment_urgency * 1_000_000
            + touchpoint_epoch
            + weighted_total
        )

        queue_item = {
            "pnm_id": pnm_id,
            "pnm_code": pnm["pnm_code"],
            "name": f"{pnm['first_name']} {pnm['last_name']}",
            "photo_url": pnm["photo_url"],
            "weighted_total": round(weighted_total, 2),
            "rating_count": int(pnm["rating_count"]),
            "total_lunches": int(pnm["total_lunches"]),
            "assigned_officer_username": (pnm.get("assigned_officer") or {}).get("username", ""),
            "assigned_officers": pnm.get("assigned_officers") or [],
            "own_rating": pnm.get("own_rating"),
            "last_touchpoint_at": last_touchpoint_at,
            "last_lunch_at": newest_timestamp([last_lunch_at]),
            "last_rating_by_me_at": last_rating_by_me_dt.isoformat() if last_rating_by_me_dt else None,
            "needs_rating_update": needs_rating_update,
            "stale_reason": stale_reason,
            "priority_score": round(float(priority_score), 2),
            "assignment_status": pnm.get("assignment_status"),
            "assignment_status_label": pnm.get("assignment_status_label"),
            "is_assigned_to_me": assigned_to_me,
            "_sort_recent": 1 if has_recent_touchpoint else 0,
            "_sort_needs": 1 if needs_rating_update else 0,
            "_sort_assigned_to_me": 1 if assigned_to_me else 0,
            "_sort_urgency": assignment_urgency,
            "_sort_touch_epoch": touchpoint_epoch,
            "_sort_weighted_total": weighted_total,
        }
        queue_rows.append(queue_item)
        if needs_rating_update:
            stale_rows.append(queue_item)

    queue_rows.sort(
        key=lambda item: (
            -int(item["_sort_recent"]),
            -int(item["_sort_needs"]),
            -int(item["_sort_assigned_to_me"]),
            -int(item["_sort_urgency"]),
            -int(item["_sort_touch_epoch"]),
            -float(item["_sort_weighted_total"]),
            str(item["name"]).lower(),
        )
    )

    stale_rows.sort(
        key=lambda item: (
            -int(item["_sort_recent"]),
            -int(item["_sort_assigned_to_me"]),
            -int(item["_sort_urgency"]),
            -int(item["_sort_touch_epoch"]),
            str(item["name"]).lower(),
        )
    )

    for row in queue_rows:
        row.pop("_sort_recent", None)
        row.pop("_sort_needs", None)
        row.pop("_sort_assigned_to_me", None)
        row.pop("_sort_urgency", None)
        row.pop("_sort_touch_epoch", None)
        row.pop("_sort_weighted_total", None)

    recent_rating_changes: list[dict[str, Any]] = []
    for row in recent_change_rows:
        recent_rating_changes.append(
            {
                "event_id": int(row["id"]),
                "rating_id": int(row["rating_id"]),
                "pnm_id": int(row["pnm_id"]),
                "pnm_code": row["pnm_code"],
                "pnm_name": f"{row['first_name']} {row['last_name']}",
                "event_type": row["event_type"],
                "old_total": int(row["old_total"]) if row["old_total"] is not None else None,
                "new_total": int(row["new_total"]),
                "delta_total": int(row["delta_total"]),
                "comment": row["comment"] or "",
                "changed_at": row["changed_at"],
                "changed_by": {
                    "user_id": int(row["changed_by_user_id"]),
                    "username": row["changed_by_username"],
                    "role": row["changed_by_role"],
                    "emoji": row["changed_by_emoji"],
                },
            }
        )

    queue = queue_rows[:limit]
    stale_alerts = stale_rows[: min(40, limit)]

    return {
        "queue": queue,
        "stale_alerts": stale_alerts,
        "recent_rating_changes": recent_rating_changes,
        "summary": {
            "window_hours": window_hours,
            "queue_count": len(queue),
            "queue_total": len(queue_rows),
            "stale_count": len(stale_alerts),
            "stale_total": len(stale_rows),
            "recent_change_count": len(recent_rating_changes),
            "generated_at": now_dt.isoformat(),
        },
    }


def build_today_workspace_items(
    calendar_items: list[dict[str, Any]],
    scheduled_lunch_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    today_s = date.today().isoformat()
    items: list[dict[str, Any]] = []
    for row in calendar_items:
        if row.get("event_date") != today_s:
            continue
        items.append(
            {
                "item_type": row.get("item_type") or "event",
                "title": row.get("title") or "Untitled",
                "event_date": row.get("event_date") or today_s,
                "start_time": row.get("start_time") or "",
                "location": row.get("location") or "",
                "meta": row.get("pnm_name") or row.get("created_by_username") or "",
                "google_calendar_url": row.get("google_calendar_url"),
            }
        )
    if items:
        return items[:12]
    return [
        {
            "item_type": "lunch",
            "title": f"Lunch with {row.get('pnm_name', 'PNM')}",
            "event_date": row.get("lunch_date") or "",
            "start_time": row.get("start_time") or "",
            "location": row.get("location") or "",
            "meta": row.get("assigned_officer_username") or row.get("scheduled_by_username") or "",
            "google_calendar_url": row.get("google_calendar_url"),
        }
        for row in scheduled_lunch_rows[:12]
    ]


def build_command_attention_items(
    pnms: list[dict[str, Any]],
    command_payload: dict[str, Any],
    assignment_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()

    for row in command_payload.get("stale_alerts", []):
        pnm_id = int(row.get("pnm_id") or 0)
        key = (pnm_id, "stale")
        if pnm_id <= 0 or key in seen:
            continue
        seen.add(key)
        stale_reason = str(row.get("stale_reason") or "").strip().lower()
        if stale_reason == "never_rated":
            stale_label = "Never Rated"
        elif stale_reason == "rating_older_than_recent_touchpoint":
            stale_label = "Behind Touchpoint"
        elif stale_reason == "no_recent_rating":
            stale_label = "No Recent Rating"
        else:
            stale_label = "Needs Update"
        items.append(
            {
                "pnm_id": pnm_id,
                "pnm_code": row.get("pnm_code") or "",
                "name": row.get("name") or "",
                "label": stale_label,
                "detail": f"Last touchpoint: {row.get('last_touchpoint_at') or 'None'}",
                "priority": 4,
            }
        )

    for row in assignment_payload.get("escalations", []):
        pnm_id = int(row.get("pnm_id") or 0)
        key = (pnm_id, "assignment")
        if pnm_id <= 0 or key in seen:
            continue
        seen.add(key)
        due_state = str(row.get("assignment_due_state") or "").strip().replace("_", " ").title()
        status_label = str(row.get("assignment_status") or "").strip().replace("_", " ").title()
        items.append(
            {
                "pnm_id": pnm_id,
                "pnm_code": row.get("pnm_code") or "",
                "name": row.get("name") or "",
                "label": status_label or "Assignment Alert",
                "detail": due_state or "Needs follow-up",
                "priority": 3,
            }
        )

    for pnm in pnms:
        pnm_id = int(pnm.get("pnm_id") or 0)
        if pnm_id <= 0:
            continue
        if not pnm.get("assigned_officers") and not pnm.get("assigned_officer_id"):
            key = (pnm_id, "owner")
            if key not in seen:
                seen.add(key)
                items.append(
                    {
                        "pnm_id": pnm_id,
                        "pnm_code": pnm.get("pnm_code") or "",
                        "name": f"{pnm.get('first_name', '')} {pnm.get('last_name', '')}".strip(),
                        "label": "No Owner",
                        "detail": "Assignment needed",
                        "priority": 2,
                    }
                )
        if not pnm.get("photo_url"):
            key = (pnm_id, "photo")
            if key not in seen:
                seen.add(key)
                items.append(
                    {
                        "pnm_id": pnm_id,
                        "pnm_code": pnm.get("pnm_code") or "",
                        "name": f"{pnm.get('first_name', '')} {pnm.get('last_name', '')}".strip(),
                        "label": "Missing Photo",
                        "detail": "Add photo or fetch from Instagram",
                        "priority": 1,
                    }
                )
        if not str(pnm.get("notes") or "").strip() or int(pnm.get("rating_count") or 0) <= 0:
            key = (pnm_id, "meeting")
            if key not in seen:
                seen.add(key)
                items.append(
                    {
                        "pnm_id": pnm_id,
                        "pnm_code": pnm.get("pnm_code") or "",
                        "name": f"{pnm.get('first_name', '')} {pnm.get('last_name', '')}".strip(),
                        "label": "Meeting Context Thin",
                        "detail": "Notes or rating depth still missing",
                        "priority": 1,
                    }
                )

    items.sort(key=lambda item: (-int(item["priority"]), item["name"].lower(), int(item["pnm_id"])))
    return items[:24]


@app.get("/api/workspace/command")
def workspace_command(
    request: Request,
    window_hours: int = Query(default=72, ge=24, le=168),
    limit: int = Query(default=30, ge=1, le=100),
    user: sqlite3.Row = Depends(require_officer),
) -> dict[str, Any]:
    command_payload = dashboard_command_center(window_hours=window_hours, limit=limit, user=user)
    leaderboard_payload = pnm_leaderboard(limit=8, _=user)
    analytics_payload = analytics_overview(user=user)
    assignments_payload = assignments_overview(include_completed=False, user=user)
    mine_payload = assignments_mine(include_completed=False, user=user)
    notifications_payload = notification_digest(period="daily", include_read=False, max_items=30, user=user)
    scheduled_payload = scheduled_lunches(request=request, limit=40, _=user)
    calendar_payload = rush_calendar(request=request, include_past=False, limit=80, _=user)
    pnms_payload = list_pnms(user=user)
    pending_payload = pending_users(_=user)

    team_pulse = {
        "pending_approvals": len(pending_payload.get("pending", [])),
        "unassigned_pnms": sum(1 for row in assignments_payload.get("assignments", []) if row.get("assignment_status") == "unassigned"),
        "needs_help": sum(1 for row in assignments_payload.get("assignments", []) if row.get("assignment_status") == "needs_help"),
        "over_capacity_officers": sum(1 for row in assignments_payload.get("officer_loads", []) if row.get("is_over_capacity")),
    }

    return {
        "command_center": command_payload,
        "leaderboard": leaderboard_payload.get("leaderboard", []),
        "analytics": analytics_payload,
        "assignments": mine_payload.get("assignments", []),
        "today": build_today_workspace_items(calendar_payload.get("items", []), scheduled_payload.get("lunches", [])),
        "attention": build_command_attention_items(pnms_payload.get("pnms", []), command_payload, assignments_payload),
        "team_pulse": team_pulse,
        "watch_candidates": leaderboard_payload.get("leaderboard", [])[:6],
        "notifications": notifications_payload,
    }


@app.get("/api/workspace/rushees")
def workspace_rushees(
    request: Request,
    interest: str | None = None,
    stereotype: str | None = None,
    state: str | None = None,
    user: sqlite3.Row = Depends(require_officer),
) -> dict[str, Any]:
    return {
        "pnms": list_pnms(interest=interest, stereotype=stereotype, state=state, user=user).get("pnms", []),
        "analytics": analytics_overview(user=user),
        "scheduled_lunches": scheduled_lunches(request=request, limit=60, _=user).get("lunches", []),
        "calendar_share": calendar_share_payload(request, current_tenant()),
        "assignments": assignments_overview(include_completed=False, user=user),
        "interest_hints": list_interests(_=user),
    }


@app.get("/api/workspace/team")
def workspace_team(
    role: str | None = "all",
    state: str | None = None,
    city: str | None = None,
    sort: str | None = "location",
    user: sqlite3.Row = Depends(require_officer),
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "users": list_users(role=role, state=state, city=city, sort=sort, user=user).get("users", []),
        "pending": pending_users(_=user).get("pending", []),
        "assignments": assignments_mine(include_completed=False, user=user),
        "assignment_overview": assignments_overview(include_completed=False, user=user),
    }
    if user["role"] == ROLE_HEAD:
        payload["leadership"] = head_admin_officer_metrics(_=user)
    return payload


@app.get("/api/workspace/operations")
def workspace_operations(
    request: Request,
    user: sqlite3.Row = Depends(require_officer),
) -> dict[str, Any]:
    return {
        "calendar": rush_calendar(request=request, include_past=False, limit=300, _=user),
        "scheduled_lunches": scheduled_lunches(request=request, limit=80, _=user),
        "goals": list_weekly_goals(include_archived=False, _=user),
        "notifications": notification_digest(period="daily", include_read=True, max_items=60, user=user),
        "chat": list_officer_chat_messages(limit=180, user=user),
        "chat_stats": officer_chat_stats(_=user),
        "calendar_share": calendar_share_payload(request, current_tenant()),
    }


@app.get("/api/workspace/meetings")
def workspace_meetings(
    user: sqlite3.Row = Depends(require_officer),
) -> dict[str, Any]:
    pnms = list_pnms(user=user).get("pnms", [])
    assignments_payload = assignments_overview(include_completed=False, user=user)
    leaderboard_rows = pnm_leaderboard(limit=18, _=user).get("leaderboard", [])

    candidates: list[dict[str, Any]] = []
    for pnm in pnms:
        flags: list[str] = []
        if int(pnm.get("rating_count") or 0) <= 0:
            flags.append("No Ratings")
        if not str(pnm.get("notes") or "").strip():
            flags.append("No Notes")
        if not pnm.get("photo_url"):
            flags.append("No Photo")
        if not pnm.get("assigned_officers") and not pnm.get("assigned_officer_id"):
            flags.append("No Owner")
        if int(pnm.get("total_lunches") or 0) <= 0:
            flags.append("No Lunch Context")
        meeting_ready_score = max(0, 100 - len(flags) * 18 + min(int(pnm.get("rating_count") or 0), 5) * 4)
        candidates.append(
            {
                "pnm_id": int(pnm.get("pnm_id") or 0),
                "pnm_code": pnm.get("pnm_code") or "",
                "name": f"{pnm.get('first_name', '')} {pnm.get('last_name', '')}".strip(),
                "weighted_total": round(float(pnm.get("weighted_total") or 0.0), 2),
                "rating_count": int(pnm.get("rating_count") or 0),
                "total_lunches": int(pnm.get("total_lunches") or 0),
                "assigned_officer_username": pnm.get("assigned_officer", {}).get("username") if isinstance(pnm.get("assigned_officer"), dict) else "",
                "package_group_label": pnm.get("package_group_label") or "",
                "linked_count": len(list(pnm.get("linked_pnms") or [])),
                "flags": flags,
                "meeting_ready_score": meeting_ready_score,
            }
        )

    candidates.sort(key=lambda item: (-item["meeting_ready_score"], -item["weighted_total"], item["name"].lower()))
    compare_defaults = [item["pnm_id"] for item in candidates[:2] if int(item["pnm_id"]) > 0]

    return {
        "candidates": candidates,
        "shortlist": candidates[:12],
        "attention": build_command_attention_items(pnms, {"stale_alerts": []}, assignments_payload),
        "watch_candidates": leaderboard_rows[:8],
        "compare_defaults": compare_defaults,
    }


@app.get("/api/admin/overview")
def workspace_admin_overview(
    user: sqlite3.Row = Depends(require_head),
) -> dict[str, Any]:
    return {
        "leadership": head_admin_officer_metrics(_=user),
        "assignments": assignments_overview(include_completed=True, user=user),
        "storage": storage_diagnostics(_=user),
        "pending": pending_users(_=user),
        "goals": list_weekly_goals(include_archived=False, _=user),
    }


@app.get("/api/search/global")
def global_search(
    q: str = Query(default="", min_length=1, max_length=120),
    _: sqlite3.Row = Depends(current_user),
) -> dict[str, Any]:
    token = q.strip()
    if not token:
        return {"query": "", "pnms": [], "members": [], "commands": []}
    like_token = f"%{token.lower()}%"
    tenant = current_tenant()
    with db_session() as conn:
        pnm_rows = conn.execute(
            """
            SELECT
                p.id,
                p.pnm_code,
                p.first_name,
                p.last_name,
                p.weighted_total
            FROM pnms p
            WHERE
                lower(p.pnm_code) LIKE ?
                OR lower(p.first_name) LIKE ?
                OR lower(p.last_name) LIKE ?
                OR lower(COALESCE(p.instagram_handle, '')) LIKE ?
            ORDER BY p.weighted_total DESC, p.last_name ASC, p.first_name ASC
            LIMIT 8
            """,
            (like_token, like_token, like_token, like_token),
        ).fetchall()
        user_rows = conn.execute(
            """
            SELECT id, username, role, emoji
            FROM users
            WHERE is_approved = 1
              AND (lower(username) LIKE ? OR lower(role) LIKE ?)
            ORDER BY username ASC
            LIMIT 8
            """,
            (like_token, like_token),
        ).fetchall()
    return {
        "query": token,
        "pnms": [
            {
                "pnm_id": int(row["id"]),
                "pnm_code": row["pnm_code"],
                "name": f"{row['first_name']} {row['last_name']}",
                "weighted_total": round(float(row["weighted_total"]), 2),
                "meeting_path": f"/{tenant.slug}/meeting?pnm_id={int(row['id'])}",
            }
            for row in pnm_rows
        ],
        "members": [
            {
                "user_id": int(row["id"]),
                "username": row["username"],
                "role": row["role"],
                "emoji": row["emoji"],
            }
            for row in user_rows
        ],
        "commands": [
            {"command_id": "create_lunch", "label": "Create Lunch", "action": "create_lunch"},
            {"command_id": "create_event", "label": "Create Event", "action": "create_event"},
            {"command_id": "backup_csv", "label": "Backup CSV", "action": "backup_csv"},
            {"command_id": "open_meetings", "label": "Open Meetings Workspace", "action": "open_meetings"},
        ],
    }


@app.get("/api/matching")
def matching(
    interest: str | None = None,
    stereotype: str | None = None,
    state: str | None = None,
    user: sqlite3.Row = Depends(current_user),
) -> dict[str, Any]:
    try:
        interest_filter = parse_interest_filter(interest)
        state_filter = parse_state_filter(state)
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
        links_by_pnm = fetch_assignment_links_for_pnms(
            conn,
            pnm_ids=[int(row["id"]) for row in pnm_rows],
        )
        user_rows = conn.execute(
            "SELECT * FROM users WHERE is_approved = 1 ORDER BY username ASC"
        ).fetchall()

    pnms = []
    for row in pnm_rows:
        if normalized_stereotype and row["stereotype"].lower() != normalized_stereotype:
            continue
        if not has_interest_match(row["interests_norm"], interest_filter):
            continue
        if state_filter:
            hometown_state_code = pnm_state_code_for_row(row)
            if hometown_state_code != state_filter:
                continue
        pnms.append(
            pnm_payload(
                row,
                own_rating_by_pnm.get(row["id"]),
                assigned_officer=assigned_officer_payload_from_row(row),
                assigned_officers=links_by_pnm.get(int(row["id"]), []),
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
            "state": state_filter or "",
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


@app.get("/api/leaderboard/pnms")
def pnm_leaderboard(limit: int = 100, _: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    safe_limit = max(1, min(int(limit), 500))
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT
                p.id,
                p.pnm_code,
                p.first_name,
                p.last_name,
                p.weighted_total,
                p.rating_count,
                p.total_lunches,
                p.first_event_date,
                ao.username AS assigned_officer_username
            FROM pnms p
            LEFT JOIN users ao ON ao.id = p.assigned_officer_id
            ORDER BY p.weighted_total DESC, p.rating_count DESC, p.total_lunches DESC, p.last_name ASC, p.first_name ASC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    leaderboard: list[dict[str, Any]] = []
    leader_score = round(float(rows[0]["weighted_total"]), 2) if rows else 0.0
    for index, row in enumerate(rows, start=1):
        weighted_total = round(float(row["weighted_total"]), 2)
        days_since = (date.today() - date.fromisoformat(row["first_event_date"])).days
        leaderboard.append(
            {
                "rank": index,
                "pnm_id": row["id"],
                "pnm_code": row["pnm_code"],
                "name": f"{row['first_name']} {row['last_name']}",
                "weighted_total": weighted_total,
                "rating_count": int(row["rating_count"]),
                "total_lunches": int(row["total_lunches"]),
                "days_since_first_event": days_since,
                "assigned_officer_username": row["assigned_officer_username"] or "",
                "points_from_leader": round(leader_score - weighted_total, 2),
            }
        )

    return {
        "leaderboard": leaderboard,
        "leader_score": leader_score,
        "count": len(leaderboard),
    }


@app.get("/api/interests")
def list_interests(_: sqlite3.Row = Depends(current_user)) -> dict[str, list[str]]:
    tenant = CURRENT_TENANT.get()
    values = list(tenant.default_interest_tags) if tenant else list(DEFAULT_INTEREST_TAG_SUGGESTIONS)
    return {"interests": values}
