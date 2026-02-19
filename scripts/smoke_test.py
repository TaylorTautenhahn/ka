#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def configure_env(root: Path) -> None:
    data_root = root / "data"
    os.environ["DATA_ROOT"] = str(data_root)
    os.environ["DB_PATH"] = str(data_root / "recruitment.db")
    os.environ["PLATFORM_DB_PATH"] = str(data_root / "platform.db")
    os.environ["TENANTS_DB_DIR"] = str(data_root / "tenants")
    os.environ["UPLOADS_DIR"] = str(data_root / "uploads")
    os.environ["BACKUP_DIR"] = str(data_root / "backups")
    os.environ["DEFAULT_TENANT_SLUG"] = "kappaalphaorder"
    os.environ["DEFAULT_TENANT_NAME"] = "Kappa Alpha Order"
    os.environ["HEAD_SEED_USERNAME"] = "headseed"
    os.environ["HEAD_SEED_ACCESS_CODE"] = "HeadSeed123!"
    os.environ["PLATFORM_ADMIN_USERNAME"] = "platformadmin"
    os.environ["PLATFORM_ADMIN_ACCESS_CODE"] = "Platform123!"
    os.environ["SESSION_COOKIE_SECURE"] = "0"
    os.environ["SESSION_COOKIE_SAMESITE"] = "strict"
    os.environ["REQUIRE_PERSISTENT_DATA"] = "0"
    os.environ["ALLOWED_HOSTS"] = "*"


def expect_status(response: Any, expected: int, label: str) -> None:
    if response.status_code != expected:
        body = response.text.strip().replace("\n", " ")
        if len(body) > 320:
            body = f"{body[:320]}..."
        raise AssertionError(f"{label}: expected HTTP {expected}, got {response.status_code}. Body: {body}")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="bidboard-smoke-") as tmpdir:
        configure_env(Path(tmpdir))

        from fastapi.testclient import TestClient
        from app import main as main_module
        from app.main import app

        checks: list[str] = []
        with TestClient(app) as client:
            client.headers.update({"Origin": "http://testserver"})

            def sync_csrf_header() -> None:
                token = client.cookies.get(main_module.CSRF_COOKIE, "")
                if token:
                    client.headers["X-CSRF-Token"] = token
                else:
                    client.headers.pop("X-CSRF-Token", None)

            response = client.get("/")
            expect_status(response, 200, "Landing page")
            checks.append("Landing route responds")

            response = client.get("/features")
            expect_status(response, 200, "Features page")
            checks.append("Features route responds")

            response = client.get("/faq")
            expect_status(response, 200, "FAQ page")
            checks.append("FAQ route responds")

            response = client.get("/demo")
            expect_status(response, 200, "Demo page")
            checks.append("Demo route responds")

            response = client.head("/")
            expect_status(response, 200, "HEAD root")
            checks.append("HEAD / health probe path responds")

            response = client.get("/manifest.webmanifest")
            expect_status(response, 200, "Root manifest")
            manifest = response.json()
            if manifest.get("short_name") != "BidBoard":
                raise AssertionError("Root manifest short_name should be BidBoard.")
            checks.append("Root web manifest responds")

            response = client.get("/kappaalphaorder")
            expect_status(response, 200, "Tenant web app page")
            checks.append("Tenant route responds")

            response = client.get("/kappaalphaorder/manifest.webmanifest")
            expect_status(response, 200, "Tenant manifest")
            tenant_manifest = response.json()
            if tenant_manifest.get("start_url") != "/kappaalphaorder/":
                raise AssertionError("Tenant manifest start_url is incorrect.")
            checks.append("Tenant web manifest responds")

            response = client.get("/kappaalphaorder/mobile")
            expect_status(response, 200, "Tenant mobile page")
            checks.append("Mobile route responds")

            response = client.get("/platform")
            expect_status(response, 200, "Platform admin page")
            checks.append("Platform route responds")

            response = client.get("/kappaalphaorder/api/auth/me")
            expect_status(response, 401, "Anonymous auth check")
            checks.append("Anonymous API access blocked")

            officer_username = "officerqa"
            officer_password = "OfficerPass123!"
            response = client.post(
                "/kappaalphaorder/api/auth/register",
                json={
                    "username": officer_username,
                    "access_code": officer_password,
                    "emoji": "🔥",
                },
            )
            expect_status(response, 200, "Officer registration")
            checks.append("Officer registration works")

            response = client.post(
                "/kappaalphaorder/api/auth/login",
                json={"username": officer_username, "access_code": officer_password},
            )
            expect_status(response, 403, "Pending officer login blocked")
            checks.append("Pending users cannot login before approval")

            response = client.post(
                "/kappaalphaorder/api/auth/login",
                json={"username": "headseed", "access_code": "HeadSeed123!", "remember_me": True},
            )
            expect_status(response, 200, "Head login")
            sync_csrf_header()
            session_cookie = client.cookies.get(main_module.SESSION_COOKIE)
            if not session_cookie:
                raise AssertionError("Head login did not set rush session cookie.")
            tenant_row = main_module.fetch_tenant_row("kappaalphaorder")
            if tenant_row is None:
                raise AssertionError("Missing tenant row for kappaalphaorder.")
            tenant_ctx = main_module.tenant_context_from_row(tenant_row)
            with main_module.db_session(tenant_ctx.db_path) as conn:
                session_row = conn.execute(
                    "SELECT max_idle_seconds FROM sessions WHERE token = ?",
                    (session_cookie,),
                ).fetchone()
            if session_row is None:
                raise AssertionError("Could not find persisted session record for head login.")
            if int(session_row["max_idle_seconds"]) != int(main_module.SESSION_REMEMBER_TTL_SECONDS):
                raise AssertionError("Remember-me login did not store remember session TTL.")
            checks.append("Head login works")
            checks.append("Remember-me session TTL stored for tenant user")

            response = client.get("/kappaalphaorder/api/users/pending")
            expect_status(response, 200, "Pending users list")
            pending = response.json().get("pending", [])
            pending_user = next((item for item in pending if item.get("username") == officer_username), None)
            if pending_user is None:
                raise AssertionError("Pending list missing newly registered officer.")
            officer_user_id = int(pending_user["user_id"])
            checks.append("Pending approval queue includes new officer")

            response = client.post(f"/kappaalphaorder/api/users/pending/{officer_user_id}/approve")
            expect_status(response, 200, "Approve officer")
            checks.append("Officer approval flow works")

            today = date.today().isoformat()
            response = client.post(
                "/kappaalphaorder/api/pnms",
                json={
                    "first_name": "Alex",
                    "last_name": "Carter",
                    "class_year": "F",
                    "hometown": "Austin",
                    "phone_number": "+1 555 123 4567",
                    "instagram_handle": "@alexc",
                    "first_event_date": today,
                    "interests": ["Leadership", "Sports"],
                    "stereotype": "Leader",
                    "notes": "High-energy candidate with strong social presence.",
                    "auto_photo_from_instagram": False,
                },
            )
            expect_status(response, 200, "Create PNM")
            pnm = response.json().get("pnm", {})
            pnm_id = int(pnm.get("pnm_id"))
            checks.append("PNM create works")

            response = client.post("/kappaalphaorder/api/auth/logout")
            expect_status(response, 200, "Head logout")
            sync_csrf_header()

            response = client.post(
                "/kappaalphaorder/api/auth/login",
                json={"username": officer_username, "access_code": officer_password},
            )
            expect_status(response, 200, "Approved officer login")
            sync_csrf_header()
            checks.append("Approved officer login works")

            response = client.post(
                "/kappaalphaorder/api/ratings",
                json={
                    "pnm_id": pnm_id,
                    "good_with_girls": 7,
                    "will_make_it": 8,
                    "personable": 8,
                    "alcohol_control": 7,
                    "instagram_marketability": 4,
                    "comment": "Initial rating entry",
                },
            )
            expect_status(response, 200, "Create rating")
            checks.append("Rating create works")

            response = client.post(
                "/kappaalphaorder/api/ratings",
                json={
                    "pnm_id": pnm_id,
                    "good_with_girls": 8,
                    "will_make_it": 8,
                    "personable": 8,
                    "alcohol_control": 7,
                    "instagram_marketability": 4,
                    "comment": "Too short update",
                },
            )
            expect_status(response, 400, "Rating update short comment blocked")
            checks.append("Rating update comment-length rule enforced")

            response = client.post(
                "/kappaalphaorder/api/ratings",
                json={
                    "pnm_id": pnm_id,
                    "good_with_girls": 8,
                    "will_make_it": 9,
                    "personable": 8,
                    "alcohol_control": 7,
                    "instagram_marketability": 5,
                    "comment": "Improved this week after multiple strong interactions and better consistency.",
                },
            )
            expect_status(response, 200, "Rating update with valid comment")
            checks.append("Rating update with delta tracking works")

            response = client.post(
                "/kappaalphaorder/api/lunches",
                json={
                    "pnm_id": pnm_id,
                    "lunch_date": today,
                    "start_time": "12:00",
                    "end_time": "13:00",
                    "location": "Campus Cafe",
                    "notes": "Reviewed interests and class schedule.",
                },
            )
            expect_status(response, 200, "Create lunch")
            checks.append("Lunch scheduling works")

            response = client.post(
                "/kappaalphaorder/api/lunches",
                json={
                    "pnm_id": pnm_id,
                    "lunch_date": today,
                    "start_time": "14:00",
                    "end_time": "15:00",
                    "location": "Second Cafe",
                    "notes": "Duplicate date check",
                },
            )
            expect_status(response, 409, "Duplicate lunch blocked")
            checks.append("Lunch dedupe rule enforced")

            response = client.post(
                "/kappaalphaorder/api/rush-events",
                json={
                    "title": "Officer Should Not Create",
                    "event_type": "official",
                    "event_date": today,
                },
            )
            expect_status(response, 403, "Officer blocked from creating rush event")
            checks.append("Head-only rush event permission enforced")

            response = client.post(
                "/kappaalphaorder/api/chat/officer",
                json={"message": "Reminder @headseed to review Alex before chapter tonight.", "tags": "priority,events"},
            )
            expect_status(response, 200, "Officer chat message create")
            checks.append("Officer chat write works")

            response = client.get("/kappaalphaorder/api/chat/officer?limit=50")
            expect_status(response, 200, "Officer chat list")
            messages = response.json().get("messages", [])
            if not messages:
                raise AssertionError("Chat list should contain at least one message.")
            checks.append("Officer chat read works")

            response = client.get(f"/kappaalphaorder/api/pnms/{pnm_id}/meeting")
            expect_status(response, 200, "Meeting view payload")
            checks.append("Meeting view API works")

            response = client.post("/kappaalphaorder/api/auth/logout")
            expect_status(response, 200, "Officer logout")
            sync_csrf_header()

            response = client.post(
                "/kappaalphaorder/api/auth/login",
                json={"username": "headseed", "access_code": "HeadSeed123!"},
            )
            expect_status(response, 200, "Head re-login")
            sync_csrf_header()

            response = client.post(
                "/kappaalphaorder/api/rush-events",
                json={
                    "title": "Official Rush Kickoff",
                    "event_type": "official",
                    "event_date": today,
                    "start_time": "19:00",
                    "end_time": "20:30",
                    "location": "Chapter House",
                    "details": "Kickoff briefing and assignment review.",
                    "is_official": True,
                },
            )
            expect_status(response, 200, "Head creates rush event")
            checks.append("Head rush event create works")

            response = client.get("/kappaalphaorder/api/rush-calendar?limit=50")
            expect_status(response, 200, "Rush calendar API")
            calendar_payload = response.json()
            stats = calendar_payload.get("stats", {})
            if int(stats.get("official_event_count", 0)) < 1 or int(stats.get("lunch_count", 0)) < 1:
                raise AssertionError("Rush calendar stats should include at least one event and one lunch.")
            checks.append("Combined rush calendar aggregation works")

            response = client.get("/kappaalphaorder/api/analytics/overview")
            expect_status(response, 200, "Analytics overview API")
            checks.append("Analytics API works")

            response = client.get("/kappaalphaorder/api/export/contacts/status")
            expect_status(response, 200, "Contacts status API before export")
            status_payload = response.json()
            if int(status_payload.get("downloaded_count", -1)) != 0:
                raise AssertionError("Contacts status should be empty before any export.")
            checks.append("Per-user contact download status starts empty")

            response = client.get(f"/kappaalphaorder/api/export/contacts/{pnm_id}.vcf")
            expect_status(response, 200, "Single contact VCF export API")
            single_contact_text = response.content.decode("utf-8", errors="ignore")
            if "BEGIN:VCARD" not in single_contact_text or "FN:Alex Carter" not in single_contact_text:
                raise AssertionError("Single contact export missing required vCard data.")
            checks.append("Single PNM contact export works")

            response = client.get("/kappaalphaorder/api/export/contacts/status")
            expect_status(response, 200, "Contacts status API after single export")
            status_payload = response.json()
            downloads = status_payload.get("downloads", [])
            downloaded_ids = {int(item.get("pnm_id")) for item in downloads if isinstance(item, dict) and item.get("pnm_id")}
            if pnm_id not in downloaded_ids:
                raise AssertionError("Single contact export did not persist per-user download checkmark state.")
            checks.append("Per-user contact download status persists after single export")

            response = client.get("/kappaalphaorder/api/export/contacts.vcf")
            expect_status(response, 200, "Contacts VCF export API")
            contacts_content_type = (response.headers.get("content-type", "") or "").lower()
            if "vcard" not in contacts_content_type:
                raise AssertionError(f"Contacts export returned unexpected content-type: {contacts_content_type}")
            contacts_text = response.content.decode("utf-8", errors="ignore")
            if "BEGIN:VCARD" not in contacts_text or "ORG:PNM (Kappa Alpha Order)" not in contacts_text:
                raise AssertionError("Contacts export missing required vCard fields.")
            checks.append("Contacts VCF export works")

            response = client.get("/kappaalphaorder/api/export/contacts/status")
            expect_status(response, 200, "Contacts status API after bulk export")
            status_payload = response.json()
            if int(status_payload.get("downloaded_count", 0)) < 1:
                raise AssertionError("Bulk contact export should leave at least one per-user download status record.")
            checks.append("Bulk contact export updates per-user contact status")

            response = client.get("/kappaalphaorder/api/export/csv")
            expect_status(response, 200, "CSV export API")
            content_type = response.headers.get("content-type", "")
            if "application/zip" not in content_type:
                raise AssertionError(f"CSV export returned unexpected content-type: {content_type}")
            checks.append("CSV backup export works")

            response = client.get("/kappaalphaorder/api/admin/storage")
            expect_status(response, 200, "Storage diagnostics API")
            checks.append("Storage diagnostics endpoint works")

            response = client.post(
                "/platform/api/auth/login",
                json={"username": "platformadmin", "access_code": "Platform123!", "remember_me": True},
            )
            expect_status(response, 200, "Platform admin login")
            sync_csrf_header()
            platform_cookie = client.cookies.get(main_module.PLATFORM_SESSION_COOKIE)
            if not platform_cookie:
                raise AssertionError("Platform login did not set platform session cookie.")
            with main_module.platform_db_session() as conn:
                platform_session = conn.execute(
                    "SELECT max_idle_seconds FROM platform_sessions WHERE token = ?",
                    (platform_cookie,),
                ).fetchone()
            if platform_session is None:
                raise AssertionError("Could not find persisted platform session record.")
            if int(platform_session["max_idle_seconds"]) != int(main_module.PLATFORM_SESSION_REMEMBER_TTL_SECONDS):
                raise AssertionError("Platform remember-me login did not store remember session TTL.")
            checks.append("Platform admin login works")
            checks.append("Remember-me session TTL stored for platform admin")

            response = client.get("/platform/api/tenants")
            expect_status(response, 200, "Platform tenant list")
            tenant_slugs = {item.get("slug") for item in response.json().get("tenants", [])}
            if "kappaalphaorder" not in tenant_slugs:
                raise AssertionError("Default tenant missing from platform tenant list.")
            checks.append("Platform tenant registry API works")

            response = client.get("/health")
            expect_status(response, 200, "Health endpoint")
            checks.append("Health endpoint responds")

        print(f"Smoke tests passed: {len(checks)} checks")
        for item in checks:
            print(f" - {item}")


if __name__ == "__main__":
    main()
