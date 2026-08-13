from __future__ import annotations

import hashlib
import re
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from fastapi.staticfiles import StaticFiles
from starlette.responses import Response


VERSION_TOKEN_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
VERSIONED_ASSET_CACHE_CONTROL = "public, max-age=31536000, immutable"
UNVERSIONED_ASSET_CACHE_CONTROL = "public, max-age=86400, stale-while-revalidate=604800"


def build_static_asset_version(static_dir: Path, configured_version: str = "") -> str:
    override = configured_version.strip()
    if override:
        if not VERSION_TOKEN_RE.fullmatch(override):
            raise ValueError("STATIC_ASSET_VERSION may only contain letters, numbers, dot, underscore, and hyphen.")
        return override

    digest = hashlib.sha256()
    for asset_path in sorted(path for path in static_dir.rglob("*") if path.is_file()):
        relative_path = asset_path.relative_to(static_dir).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(asset_path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:12]


def versioned_static_url(asset_path: str, version: str) -> str:
    normalized = str(asset_path or "").strip().split("?", 1)[0].lstrip("/")
    if normalized.startswith("static/"):
        normalized = normalized[len("static/") :]
    parts = PurePosixPath(normalized).parts
    if not normalized or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("Static asset path must be a relative path inside the static directory.")
    return f"/static/{quote(normalized, safe='/._-')}?v={version}"


class CacheControlStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: dict) -> Response:
        response = await super().get_response(path, scope)
        if response.status_code in {200, 304}:
            query_string = scope.get("query_string", b"")
            response.headers["Cache-Control"] = (
                VERSIONED_ASSET_CACHE_CONTROL if query_string else UNVERSIONED_ASSET_CACHE_CONTROL
            )
        return response
