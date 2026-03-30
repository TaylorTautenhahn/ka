#!/usr/bin/env python3
from __future__ import annotations

import base64
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

        if main_module.normalize_state_code("Texas") != "TX":
            raise AssertionError("State normalization should map full state names.")
        if main_module.normalize_state_code("tx") != "TX":
            raise AssertionError("State normalization should map 2-letter abbreviations.")
        parsed_city, parsed_state = main_module.parse_hometown_city_state("Austin, TX")
        if parsed_city != "Austin" or parsed_state != "TX":
            raise AssertionError("Hometown parser should handle City, ST format.")
        parsed_city, parsed_state = main_module.parse_hometown_city_state("Dallas TX")
        if parsed_city != "Dallas" or parsed_state != "TX":
            raise AssertionError("Hometown parser should handle City ST format.")
        parsed_city, parsed_state = main_module.parse_hometown_city_state("Unknown Place")
        if parsed_city != "Unknown Place" or parsed_state != "":
            raise AssertionError("Hometown parser should preserve unknown format city with empty state.")
        checks.append("State normalization + hometown parsing helpers work")

        try:
            main_module.require_bootstrap_secret_configured(
                "",
                env_name="HEAD_SEED_ACCESS_CODE",
                principal_label="Head rush officer",
                production_mode=True,
            )
        except RuntimeError as exc:
            if "HEAD_SEED_ACCESS_CODE" not in str(exc):
                raise
        else:
            raise AssertionError("Fresh production bootstrap should require an explicit head seed secret.")
        main_module.require_bootstrap_secret_configured(
            "configured",
            env_name="HEAD_SEED_ACCESS_CODE",
            principal_label="Head rush officer",
            production_mode=True,
        )
        checks.append("Production bootstrap secret guard works")

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

            response = client.get("/kappaalphaorder", follow_redirects=False)
            expect_status(response, 307, "Tenant root redirect")
            if response.headers.get("location") != "/kappaalphaorder/dashboard":
                raise AssertionError("Tenant root should redirect to /{tenant}/dashboard.")
            checks.append("Tenant root redirects to dashboard route")

            response = client.get("/kappaalphaorder?view=overview", follow_redirects=False)
            expect_status(response, 307, "Legacy overview redirect")
            if response.headers.get("location") != "/kappaalphaorder/dashboard":
                raise AssertionError("Legacy ?view=overview should redirect to dashboard.")
            checks.append("Legacy overview query redirect works")

            response = client.get("/kappaalphaorder?view=operations", follow_redirects=False)
            expect_status(response, 307, "Legacy operations redirect")
            if response.headers.get("location") != "/kappaalphaorder/dashboard#operations":
                raise AssertionError("Legacy ?view=operations should redirect to dashboard#operations.")
            checks.append("Legacy operations query redirect works")

            response = client.get("/kappaalphaorder?view=members", follow_redirects=False)
            expect_status(response, 307, "Legacy members redirect")
            if response.headers.get("location") != "/kappaalphaorder/team":
                raise AssertionError("Legacy ?view=members should redirect to /team.")
            checks.append("Legacy members query redirect works")

            response = client.get("/kappaalphaorder/dashboard")
            expect_status(response, 200, "Dashboard route")
            response = client.get("/kappaalphaorder/rushees")
            expect_status(response, 200, "Rushees route")
            response = client.get("/kappaalphaorder/meetings")
            expect_status(response, 200, "Meetings route")
            response = client.get("/kappaalphaorder/team")
            expect_status(response, 200, "Team route")
            response = client.get("/kappaalphaorder/calendar")
            expect_status(response, 200, "Calendar route")
            response = client.get("/kappaalphaorder/admin")
            expect_status(response, 200, "Admin route (anonymous login shell)")
            checks.append("Desktop route pages respond")

            response = client.get("/kappaalphaorder/manifest.webmanifest")
            expect_status(response, 200, "Tenant manifest")
            tenant_manifest = response.json()
            if tenant_manifest.get("start_url") != "/kappaalphaorder/dashboard":
                raise AssertionError("Tenant manifest start_url is incorrect.")
            checks.append("Tenant web manifest responds")

            response = client.get("/kappaalphaorder/mobile")
            expect_status(response, 200, "Tenant mobile page")
            response = client.get("/kappaalphaorder/mobile/pnms")
            expect_status(response, 200, "Tenant mobile rushees page")
            response = client.get("/kappaalphaorder/mobile/members")
            expect_status(response, 200, "Tenant mobile team page")
            response = client.get("/kappaalphaorder/mobile/calendar")
            expect_status(response, 200, "Tenant mobile calendar page")
            response = client.get("/kappaalphaorder/mobile/admin")
            expect_status(response, 200, "Tenant mobile admin page")
            checks.append("Mobile routes respond")

            response = client.get("/platform")
            expect_status(response, 200, "Platform admin page")
            checks.append("Platform route responds")

            response = client.get("/kappaalphaorder/api/auth/me")
            expect_status(response, 200, "Anonymous tenant auth check")
            auth_payload = response.json()
            if auth_payload.get("authenticated") is not False or auth_payload.get("user") is not None:
                raise AssertionError("Anonymous tenant auth probe should return authenticated=false with no user.")
            checks.append("Anonymous tenant auth probe stays clean")

            response = client.get("/platform/api/auth/me")
            expect_status(response, 200, "Anonymous platform auth check")
            platform_auth_payload = response.json()
            if platform_auth_payload.get("authenticated") is not False or platform_auth_payload.get("admin") is not None:
                raise AssertionError("Anonymous platform auth probe should return authenticated=false with no admin.")
            checks.append("Anonymous platform auth probe stays clean")

            response = client.get("/kappaalphaorder/api/pnms")
            expect_status(response, 401, "Anonymous protected API check")
            checks.append("Anonymous protected API access blocked")

            officer_username = "officerqa"
            officer_password = "OfficerPass123!"
            response = client.post(
                "/kappaalphaorder/api/auth/register",
                json={
                    "username": officer_username,
                    "access_code": officer_password,
                    "emoji": "🔥",
                    "city": "Austin",
                    "state": "Texas",
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
            head_user_id = int(response.json().get("user", {}).get("user_id") or 0)
            if not head_user_id:
                raise AssertionError("Head login payload should include the user id.")
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

            response = client.get("/kappaalphaorder/admin")
            expect_status(response, 200, "Head can open admin route")
            checks.append("Head can access admin route")

            response = client.get("/kappaalphaorder/api/auth/capabilities")
            expect_status(response, 200, "Head capabilities API")
            capabilities = response.json().get("capabilities", {})
            if not capabilities.get("can_manage_admin") or not capabilities.get("can_export_backups"):
                raise AssertionError("Head capabilities should expose admin and backup access.")
            checks.append("Head capabilities API works")

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

            officer_two_username = "officerqa2"
            officer_two_password = "OfficerTwoPass123!"
            response = client.post(
                "/kappaalphaorder/api/auth/register",
                json={
                    "username": officer_two_username,
                    "access_code": officer_two_password,
                    "emoji": "⚡",
                    "city": "Dallas",
                    "state": "TX",
                },
            )
            expect_status(response, 200, "Second officer registration")

            response = client.get("/kappaalphaorder/api/users/pending")
            expect_status(response, 200, "Pending users list after second registration")
            pending = response.json().get("pending", [])
            pending_user_two = next((item for item in pending if item.get("username") == officer_two_username), None)
            if pending_user_two is None:
                raise AssertionError("Pending list missing second registered officer.")
            officer_two_user_id = int(pending_user_two["user_id"])

            response = client.post(f"/kappaalphaorder/api/users/pending/{officer_two_user_id}/approve")
            expect_status(response, 200, "Approve second officer")
            checks.append("Second officer approval flow works")

            member_username = "memberqa"
            member_password = "MemberPass123!"
            response = client.post(
                "/kappaalphaorder/api/auth/register-member",
                json={
                    "username": member_username,
                    "access_code": member_password,
                    "city": "College Station",
                    "state": "TX",
                },
            )
            expect_status(response, 200, "Member registration")

            response = client.get("/kappaalphaorder/api/users/pending")
            expect_status(response, 200, "Pending users list after member registration")
            pending = response.json().get("pending", [])
            pending_member = next((item for item in pending if item.get("username") == member_username), None)
            if pending_member is None:
                raise AssertionError("Pending list missing member registration.")
            member_user_id = int(pending_member["user_id"])
            response = client.post(f"/kappaalphaorder/api/users/pending/{member_user_id}/approve")
            expect_status(response, 200, "Approve member")
            checks.append("Member registration + approval flow works")

            response = client.get("/kappaalphaorder/api/users?role=Rush%20Officer&state=TX&sort=location")
            expect_status(response, 200, "Users filter by role/state/location sort")
            filtered_officers = response.json().get("users", [])
            if not filtered_officers:
                raise AssertionError("Expected at least one filtered Rush Officer in TX.")
            if not all(item.get("role") == "Rush Officer" for item in filtered_officers):
                raise AssertionError("Role filter should only return Rush Officer users.")
            if not all(item.get("state_code") == "TX" for item in filtered_officers):
                raise AssertionError("State filter should only return TX users.")
            checks.append("Users API role/state/sort filters work")

            response = client.get("/kappaalphaorder/api/users?city=aus")
            expect_status(response, 200, "Users filter by city contains")
            city_filtered = response.json().get("users", [])
            if not any(item.get("username") == officer_username for item in city_filtered):
                raise AssertionError("City filter should match Austin-based officer.")
            checks.append("Users API city contains filter works")

            response = client.patch(
                "/kappaalphaorder/api/users/me",
                json={"city": "Tuscaloosa", "state": "Alabama"},
            )
            expect_status(response, 200, "Self location update")
            me_user = (response.json() or {}).get("user", {})
            if me_user.get("city") != "Tuscaloosa" or me_user.get("state_code") != "AL":
                raise AssertionError("Self location update did not normalize city/state.")
            checks.append("Self location update works")

            response = client.patch(
                f"/kappaalphaorder/api/users/{officer_user_id}/location",
                json={"city": "San Antonio", "state": "TX"},
            )
            expect_status(response, 200, "Officer location update by head")
            updated_user = (response.json() or {}).get("user", {})
            if updated_user.get("city") != "San Antonio" or updated_user.get("state_code") != "TX":
                raise AssertionError("Officer location patch did not persist expected values.")
            checks.append("Head/officer location edit endpoint works")

            today = date.today().isoformat()
            response = client.post(
                "/kappaalphaorder/api/pnms",
                json={
                    "first_name": "Alex",
                    "last_name": "Carter",
                    "class_year": "F",
                    "hometown": "Austin",
                    "state": "TX",
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
            if int(pnm.get("assigned_officer_id") or 0) != int(head_user_id):
                raise AssertionError("Head-created PNM should auto-assign to the creator.")
            assigned_officers = pnm.get("assigned_officers") or []
            if not assigned_officers or int(assigned_officers[0].get("user_id") or 0) != int(head_user_id):
                raise AssertionError("Head-created PNM should create a primary assignment link for the creator.")
            checks.append("PNM create works")

            tiny_png = base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5nXioAAAAASUVORK5CYII="
            )
            response = client.post(
                f"/kappaalphaorder/api/pnms/{pnm_id}/photo",
                files={"photo": ("tiny.png", tiny_png, "image/png")},
            )
            expect_status(response, 200, "Upload PNM photo")
            photo_payload = response.json().get("pnm", {})
            if not str(photo_payload.get("photo_url") or "").startswith("/uploads/"):
                raise AssertionError("Uploaded PNM photo should return a local uploads URL.")
            checks.append("PNM photo upload works")

            response = client.post(
                "/kappaalphaorder/api/pnms",
                json={
                    "first_name": "Blake",
                    "last_name": "Donovan",
                    "class_year": "F",
                    "hometown": "Dallas, TX",
                    "state": "TX",
                    "phone_number": "+1 555 000 1111",
                    "instagram_handle": "@blaked",
                    "first_event_date": today,
                    "interests": ["Leadership", "Finance"],
                    "stereotype": "Connector",
                    "notes": "Potential package deal candidate with Alex.",
                    "auto_photo_from_instagram": False,
                },
            )
            expect_status(response, 200, "Create second PNM")
            pnm_two = response.json().get("pnm", {})
            pnm_two_id = int(pnm_two.get("pnm_id"))
            checks.append("Second PNM create works")

            response = client.post(
                "/kappaalphaorder/api/pnms",
                json={
                    "first_name": "Casey",
                    "last_name": "Ellis",
                    "class_year": "S",
                    "hometown": "Boulder",
                    "state": "CO",
                    "phone_number": "+1 555 222 3333",
                    "instagram_handle": "@caseye",
                    "first_event_date": today,
                    "interests": ["Finance", "Sports"],
                    "stereotype": "Builder",
                    "notes": "Bridge candidate to verify package merge behavior.",
                    "auto_photo_from_instagram": False,
                },
            )
            expect_status(response, 200, "Create third PNM")
            pnm_three = response.json().get("pnm", {})
            pnm_three_id = int(pnm_three.get("pnm_id"))
            checks.append("Third PNM create works")

            response = client.get("/kappaalphaorder/api/pnms?state=TX")
            expect_status(response, 200, "PNM state filter")
            tx_pnms = response.json().get("pnms", [])
            tx_ids = {int(item.get("pnm_id")) for item in tx_pnms if item.get("pnm_id")}
            if pnm_id not in tx_ids or pnm_two_id not in tx_ids or pnm_three_id in tx_ids:
                raise AssertionError("PNM state filter should include TX PNMs and exclude non-TX PNMs.")
            if not all(item.get("hometown_state_code") == "TX" for item in tx_pnms):
                raise AssertionError("PNM payload should expose normalized hometown_state_code.")
            checks.append("PNM state filter + hometown state payload fields work")

            response = client.get("/kappaalphaorder/api/matching?state=TX")
            expect_status(response, 200, "Matching state filter")
            matching_pnms = response.json().get("pnms", [])
            matching_ids = {int(item.get("pnm_id")) for item in matching_pnms if item.get("pnm_id")}
            if pnm_id not in matching_ids or pnm_two_id not in matching_ids or pnm_three_id in matching_ids:
                raise AssertionError("Matching state filter should apply to PNM results.")
            checks.append("Matching API state filter works")

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

            response = client.get("/kappaalphaorder/admin", follow_redirects=False)
            expect_status(response, 307, "Officer blocked from admin route")
            if response.headers.get("location") != "/kappaalphaorder/dashboard?notice=admin-access-denied":
                raise AssertionError("Non-head admin route access should redirect to dashboard with notice.")
            checks.append("Admin route guard redirects non-head users")

            response = client.get("/kappaalphaorder/mobile/admin", follow_redirects=False)
            expect_status(response, 307, "Officer blocked from mobile admin route")
            if response.headers.get("location") != "/kappaalphaorder/mobile?notice=admin-access-denied":
                raise AssertionError("Non-head mobile admin route access should redirect to mobile dashboard with notice.")
            checks.append("Mobile admin route guard redirects non-head users")

            response = client.patch(
                f"/kappaalphaorder/api/pnms/{pnm_id}",
                json={"notes": "Officer should not be able to edit head-created rushee."},
            )
            expect_status(response, 403, "Officer blocked from editing head-created PNM")
            checks.append("Officers cannot edit rushees created by other users")

            response = client.post(
                "/kappaalphaorder/api/pnms",
                json={
                    "first_name": "Bob",
                    "last_name": "Harper",
                    "class_year": "F",
                    "hometown": "Plano",
                    "state": "TX",
                    "phone_number": "+1 555 999 2222",
                    "instagram_handle": "@bobharper",
                    "first_event_date": today,
                    "interests": ["Leadership", "Business"],
                    "stereotype": "Connector",
                    "notes": "Officer-owned rushee for ownership tests.",
                    "auto_photo_from_instagram": False,
                },
            )
            expect_status(response, 200, "Officer-owned PNM create")
            officer_owned_pnm = response.json().get("pnm", {})
            officer_owned_pnm_id = int(officer_owned_pnm.get("pnm_id") or 0)
            if not officer_owned_pnm.get("can_manage_profile"):
                raise AssertionError("Creator should be able to manage the rushee they created.")
            if officer_owned_pnm.get("created_by_username") != officer_username:
                raise AssertionError("Officer-created PNM should expose the creator username.")
            if int(officer_owned_pnm.get("assigned_officer_id") or 0) != int(officer_user_id):
                raise AssertionError("Officer-created PNM should auto-assign to the creator.")
            assigned_officers = officer_owned_pnm.get("assigned_officers") or []
            if not assigned_officers or int(assigned_officers[0].get("user_id") or 0) != int(officer_user_id):
                raise AssertionError("Officer-created PNM should create a primary assignment link for the creator.")
            checks.append("Officer-created PNM exposes ownership metadata")

            response = client.patch(
                f"/kappaalphaorder/api/pnms/{officer_owned_pnm_id}",
                json={"hometown": "Plano, TX", "state": "TX", "notes": "Officer updated this rushee profile."},
            )
            expect_status(response, 200, "Officer edits owned PNM")
            if (response.json().get("pnm") or {}).get("hometown") != "Plano, TX":
                raise AssertionError("Officer-owned PNM update did not persist.")
            checks.append("Officers can edit rushees they created")

            response = client.get("/kappaalphaorder/api/pnms")
            expect_status(response, 200, "PNM ownership metadata list API")
            pnm_rows = {int(item.get("pnm_id") or 0): item for item in response.json().get("pnms", []) if item.get("pnm_id")}
            if pnm_rows.get(pnm_id, {}).get("can_manage_profile"):
                raise AssertionError("Officer should not see head-created PNM as editable.")
            if not pnm_rows.get(officer_owned_pnm_id, {}).get("can_manage_profile"):
                raise AssertionError("Officer should see their own created PNM as editable.")
            checks.append("PNM list exposes owner-aware edit permissions")

            response = client.post("/kappaalphaorder/api/auth/logout")
            expect_status(response, 200, "Officer logout for head ownership check")
            sync_csrf_header()

            response = client.post(
                "/kappaalphaorder/api/auth/login",
                json={"username": "headseed", "access_code": "HeadSeed123!"},
            )
            expect_status(response, 200, "Head relogin for owner override test")
            sync_csrf_header()

            response = client.patch(
                f"/kappaalphaorder/api/pnms/{officer_owned_pnm_id}",
                json={"notes": "Head can edit any rushee profile.", "state": "TX"},
            )
            expect_status(response, 200, "Head edits officer-owned PNM")
            checks.append("Head can edit rushees created by other users")

            reset_officer_password = "OfficerReset456!"
            response = client.post(
                f"/kappaalphaorder/api/users/{officer_user_id}/reset-access-code",
                json={"access_code": reset_officer_password},
            )
            expect_status(response, 200, "Head resets officer password")
            checks.append("Head can reset rush team passwords")

            response = client.post("/kappaalphaorder/api/auth/logout")
            expect_status(response, 200, "Head logout after owner override test")
            sync_csrf_header()

            response = client.post(
                "/kappaalphaorder/api/auth/login",
                json={"username": officer_username, "access_code": officer_password},
            )
            expect_status(response, 401, "Old officer password rejected after reset")
            checks.append("Old rush team password stops working after reset")

            officer_password = reset_officer_password
            response = client.post(
                "/kappaalphaorder/api/auth/login",
                json={"username": officer_username, "access_code": officer_password},
            )
            expect_status(response, 200, "Officer relogin after head ownership check")
            sync_csrf_header()
            checks.append("Officer relogin after ownership checks works")

            response = client.get("/kappaalphaorder/api/dashboard/command-center?window_hours=72&limit=25")
            expect_status(response, 200, "Officer command center API")
            command_payload = response.json()
            if not isinstance(command_payload.get("queue"), list):
                raise AssertionError("Command center queue payload should be a list.")
            if not isinstance(command_payload.get("stale_alerts"), list):
                raise AssertionError("Command center stale_alerts payload should be a list.")
            if not isinstance(command_payload.get("recent_rating_changes"), list):
                raise AssertionError("Command center recent_rating_changes payload should be a list.")
            summary = command_payload.get("summary", {})
            if int(summary.get("window_hours", 0)) != 72:
                raise AssertionError("Command center summary should reflect requested 72-hour window.")
            checks.append("Officer command center API works")

            response = client.get("/kappaalphaorder/api/auth/capabilities")
            expect_status(response, 200, "Officer capabilities API")
            capabilities_payload = response.json().get("capabilities", {})
            if not capabilities_payload.get("can_use_command") or not capabilities_payload.get("can_pin_for_meetings"):
                raise AssertionError("Officer capabilities should include command and Meetings pin permissions.")
            if capabilities_payload.get("can_manage_admin"):
                raise AssertionError("Officer capabilities should not expose head-only admin permission.")
            checks.append("Officer capabilities API works")

            response = client.get("/kappaalphaorder/api/workspace/command")
            expect_status(response, 200, "Command workspace API")
            command_workspace = response.json()
            if "command_center" not in command_workspace or "team_pulse" not in command_workspace:
                raise AssertionError("Command workspace payload should include command_center and team_pulse.")
            if "weekly_roi" not in command_workspace or "season_setup" not in command_workspace or "meeting_pins" not in command_workspace:
                raise AssertionError("Command workspace payload should include weekly_roi, season_setup, and meeting_pins.")
            if not isinstance((command_workspace.get("weekly_roi") or {}).get("cards"), list):
                raise AssertionError("Command workspace weekly ROI payload should include cards.")
            if not isinstance((command_workspace.get("season_setup") or {}).get("steps"), list):
                raise AssertionError("Command workspace season setup payload should include steps.")
            checks.append("Command workspace API works")

            response = client.get("/kappaalphaorder/api/workspace/rushees?state=TX")
            expect_status(response, 200, "Rushees workspace API")
            rushee_workspace = response.json()
            if not isinstance(rushee_workspace.get("pnms"), list):
                raise AssertionError("Rushees workspace should include a pnm list.")
            checks.append("Rushees workspace API works")

            response = client.get("/kappaalphaorder/api/workspace/team?role=Rush%20Officer&state=TX")
            expect_status(response, 200, "Team workspace API")
            team_workspace = response.json()
            if "users" not in team_workspace or "assignment_overview" not in team_workspace:
                raise AssertionError("Team workspace payload should include users and assignment_overview.")
            checks.append("Team workspace API works")

            response = client.get("/kappaalphaorder/api/workspace/operations")
            expect_status(response, 200, "Operations workspace API")
            operations_workspace = response.json()
            if "calendar" not in operations_workspace or "chat" not in operations_workspace:
                raise AssertionError("Operations workspace payload should include calendar and chat data.")
            checks.append("Operations workspace API works")

            response = client.get("/kappaalphaorder/api/workspace/meetings")
            expect_status(response, 200, "Meetings workspace API")
            meetings_workspace = response.json()
            if "shortlist" not in meetings_workspace or "candidates" not in meetings_workspace or "pins" not in meetings_workspace:
                raise AssertionError("Meetings workspace payload should include shortlist, candidates, and pins.")
            checks.append("Meetings workspace API works")

            response = client.get("/kappaalphaorder/api/meetings/pins")
            expect_status(response, 200, "Meetings pins list API")
            if response.json().get("pins") != []:
                raise AssertionError("Meetings pins should start empty in smoke tests.")
            response = client.post("/kappaalphaorder/api/meetings/pins", json={"pnm_id": pnm_id})
            expect_status(response, 200, "Create meeting pin")
            pins_payload = response.json().get("pins", [])
            if not any(int(item.get("pnm_id") or 0) == pnm_id for item in pins_payload):
                raise AssertionError("Meeting pin creation should return the pinned rushee.")
            response = client.get(f"/kappaalphaorder/api/pnms/{pnm_id}/meeting")
            expect_status(response, 200, "Meeting packet includes pin state")
            if not (response.json().get("meeting_pin") or {}).get("is_pinned"):
                raise AssertionError("Meeting packet payload should expose current meeting pin state.")
            response = client.delete(f"/kappaalphaorder/api/meetings/pins/{pnm_id}")
            expect_status(response, 200, "Delete meeting pin")
            if any(int(item.get("pnm_id") or 0) == pnm_id for item in response.json().get("pins", [])):
                raise AssertionError("Meeting pin delete should remove the selected rushee.")
            checks.append("Meetings pin APIs work")

            response = client.get("/kappaalphaorder/api/mobile/home")
            expect_status(response, 200, "Officer mobile home API")
            mobile_home_payload = response.json()
            if "pnms" not in mobile_home_payload or "recent_lunches" not in mobile_home_payload:
                raise AssertionError("Mobile home payload should include pnms and recent_lunches.")
            checks.append("Officer mobile home API works")

            response = client.get("/kappaalphaorder/api/mobile/pnms")
            expect_status(response, 200, "Officer mobile pnms API")
            if not isinstance(response.json().get("pnms"), list):
                raise AssertionError("Mobile pnms payload should include a pnm list.")
            checks.append("Officer mobile pnms API works")

            response = client.get("/kappaalphaorder/api/mobile/members")
            expect_status(response, 200, "Officer mobile members API")
            if not isinstance(response.json().get("users"), list):
                raise AssertionError("Mobile members payload should include a user list.")
            checks.append("Officer mobile members API works")

            response = client.get("/kappaalphaorder/api/calendar/share")
            expect_status(response, 200, "Officer calendar share API")
            calendar_share = response.json()
            if not calendar_share.get("feed_url") or not calendar_share.get("google_subscribe_url"):
                raise AssertionError("Calendar share payload should include feed and subscribe URLs.")
            checks.append("Officer calendar share API works")

            response = client.get("/kappaalphaorder/api/search/global?q=alex")
            expect_status(response, 200, "Global search API")
            search_payload = response.json()
            if "pnms" not in search_payload or "members" not in search_payload or "commands" not in search_payload:
                raise AssertionError("Global search payload should include pnms, members, and commands.")
            officer_commands = {
                str(item.get("action"))
                for item in search_payload.get("commands", [])
                if isinstance(item, dict) and item.get("action")
            }
            if "backup_csv" in officer_commands or "create_event" in officer_commands:
                raise AssertionError("Officer search should not expose head-only commands.")
            checks.append("Global search API works")

            response = client.get("/kappaalphaorder/api/search/global?q=alex%20carter")
            expect_status(response, 200, "Global search full-name API")
            full_name_results = response.json().get("pnms", [])
            if not any(str(item.get("name") or "").lower() == "alex carter" for item in full_name_results):
                raise AssertionError("Global search should match full-name PNM queries.")
            checks.append("Global search full-name matching works")

            response = client.get("/kappaalphaorder/api/search/global?q=head%20officer")
            expect_status(response, 200, "Global search member full-name API")
            member_full_name_results = response.json().get("members", [])
            if not any(item.get("username") == "headseed" for item in member_full_name_results):
                raise AssertionError("Global search should match member full-name queries.")
            checks.append("Global search member full-name matching works")

            response = client.get("/kappaalphaorder/api/search/global?q=touchpoint")
            expect_status(response, 200, "Global search command filtering API")
            touchpoint_search_payload = response.json()
            touchpoint_commands = {
                str(item.get("action"))
                for item in touchpoint_search_payload.get("commands", [])
                if isinstance(item, dict) and item.get("action")
            }
            if "schedule_touchpoint" not in touchpoint_commands and "create_lunch" not in touchpoint_commands:
                raise AssertionError("Command-like searches should expose touchpoint scheduling.")
            checks.append("Global search command filtering works")

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
                "/kappaalphaorder/api/pnms/package/link",
                json={
                    "pnm_ids": [pnm_id, pnm_two_id],
                    "sync_assignment": True,
                },
            )
            expect_status(response, 200, "Officer package link endpoint")
            checks.append("Rush team users can link package deals")

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

            response = client.get(f"/kappaalphaorder/api/pnms/{pnm_id}/lunches")
            expect_status(response, 200, "Officer lunch history view")
            lunch_payload = response.json()
            if not isinstance(lunch_payload.get("lunches"), list) or not lunch_payload.get("lunches"):
                raise AssertionError("Officer lunch history should include at least one lunch entry.")
            checks.append("Officer lunch history remains available")

            response = client.post(
                f"/kappaalphaorder/api/pnms/{pnm_id}/comments",
                json={"comment": "Quick note from chapter dinner: strong table presence and better follow-up energy."},
            )
            expect_status(response, 200, "Create standalone rushee comment")
            if "comment" not in response.json():
                raise AssertionError("Standalone rushee comment API should return the saved comment payload.")
            checks.append("Standalone rushee comments can be created without rating changes")

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

            response = client.get("/kappaalphaorder/api/meetings/pins")
            expect_status(response, 200, "Officer list meeting pins")
            if response.json().get("pins") != []:
                raise AssertionError("Meeting pins should start empty in the smoke flow.")

            response = client.post("/kappaalphaorder/api/meetings/pins", json={"pnm_id": pnm_id})
            expect_status(response, 200, "Officer create meeting pin")
            meeting_pins = response.json().get("pins", [])
            if not any(int(item.get("pnm_id") or 0) == pnm_id for item in meeting_pins):
                raise AssertionError("Created meeting pin should appear in the shared pin list.")

            response = client.get("/kappaalphaorder/api/workspace/command")
            expect_status(response, 200, "Command workspace with meeting pin")
            if not any(int(item.get("pnm_id") or 0) == pnm_id for item in response.json().get("meeting_pins", [])):
                raise AssertionError("Command workspace should mirror persisted meeting pins.")

            response = client.get("/kappaalphaorder/api/workspace/meetings")
            expect_status(response, 200, "Meetings workspace with meeting pin")
            meetings_payload = response.json()
            if not any(int(item.get("pnm_id") or 0) == pnm_id for item in meetings_payload.get("pins", [])):
                raise AssertionError("Meetings workspace should mirror persisted meeting pins.")
            shortlist = meetings_payload.get("shortlist", [])
            if not shortlist or int(shortlist[0].get("pnm_id") or 0) != pnm_id:
                raise AssertionError("Persisted meeting pins should be prioritized at the front of the shortlist.")
            checks.append("Meeting pins persist across Command and Meetings workspaces")

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
            meeting_payload = response.json()
            linked_pnms = meeting_payload.get("linked_pnms", [])
            if not isinstance(linked_pnms, list):
                raise AssertionError("Meeting view linked_pnms should be a list.")
            if not any(int(item.get("pnm_id") or 0) == pnm_two_id for item in linked_pnms):
                raise AssertionError("Meeting view should include linked package rushee references.")
            category_rankings = meeting_payload.get("category_rankings", [])
            if not isinstance(category_rankings, list) or not category_rankings:
                raise AssertionError("Meeting view should include category ranking analytics.")
            rating_update_comments = meeting_payload.get("rating_update_comments", [])
            if not isinstance(rating_update_comments, list):
                raise AssertionError("Meeting view rating_update_comments should be a list.")
            lunch_comment_history = meeting_payload.get("lunch_comment_history", [])
            if not isinstance(lunch_comment_history, list):
                raise AssertionError("Meeting view lunch_comment_history should be a list.")
            standalone_comment_history = meeting_payload.get("standalone_comment_history", [])
            if not isinstance(standalone_comment_history, list):
                raise AssertionError("Meeting view standalone_comment_history should be a list.")
            rush_comment_timeline = meeting_payload.get("rush_comment_timeline", [])
            if not isinstance(rush_comment_timeline, list):
                raise AssertionError("Meeting view rush_comment_timeline should be a list.")
            if not any(item.get("source") == "quick_note" for item in rush_comment_timeline):
                raise AssertionError("Meeting view should include standalone rushee comments in the rush comment timeline.")
            meeting_pin = meeting_payload.get("meeting_pin", {})
            if not meeting_pin.get("is_pinned"):
                raise AssertionError("Meeting packet payload should expose persisted meeting pin state.")
            checks.append("Meeting view API includes standalone rushee comments")

            response = client.delete(f"/kappaalphaorder/api/meetings/pins/{pnm_id}")
            expect_status(response, 200, "Officer remove meeting pin")
            if any(int(item.get("pnm_id") or 0) == pnm_id for item in response.json().get("pins", [])):
                raise AssertionError("Meeting pin removal should clear the pinned rushee from shared state.")
            checks.append("Meeting pins can be removed")

            response = client.post("/kappaalphaorder/api/auth/logout")
            expect_status(response, 200, "Officer logout")
            sync_csrf_header()

            response = client.post(
                "/kappaalphaorder/api/auth/login",
                json={"username": member_username, "access_code": member_password},
            )
            expect_status(response, 200, "Approved member login")
            sync_csrf_header()

            response = client.get("/kappaalphaorder/api/dashboard/command-center")
            expect_status(response, 403, "Rusher blocked from command center API")
            checks.append("Command center endpoint enforces officer-only access")

            response = client.get("/kappaalphaorder/mobile", follow_redirects=False)
            expect_status(response, 307, "Rusher mobile home route redirect")
            if response.headers.get("location") != "/kappaalphaorder/member":
                raise AssertionError("Rusher mobile home route should redirect to member portal.")
            checks.append("Rusher mobile home route redirects to member portal")

            response = client.get("/kappaalphaorder/mobile/pnms", follow_redirects=False)
            expect_status(response, 307, "Rusher mobile rushees route redirect")
            if response.headers.get("location") != "/kappaalphaorder/member":
                raise AssertionError("Rusher mobile rushees route should redirect to member portal.")
            checks.append("Rusher mobile rushees route redirects to member portal")

            response = client.get("/kappaalphaorder/meeting", follow_redirects=False)
            expect_status(response, 307, "Rusher meeting route redirect")
            if response.headers.get("location") != "/kappaalphaorder/member":
                raise AssertionError("Rusher meeting route should redirect to member portal.")
            checks.append("Rusher meeting route redirects to member portal")

            response = client.get(f"/kappaalphaorder/api/pnms/{pnm_id}/meeting")
            expect_status(response, 403, "Rusher blocked from meeting detail API")
            checks.append("Meeting detail enforces officer-only access")

            response = client.get(f"/kappaalphaorder/api/pnms/{pnm_id}/lunches")
            expect_status(response, 403, "Rusher blocked from lunch history API")
            checks.append("Lunch history enforces officer-only access")

            response = client.get("/kappaalphaorder/api/events?include_past=1")
            expect_status(response, 403, "Rusher blocked from events API")
            checks.append("Unified events API enforces officer-only access")

            response = client.get("/kappaalphaorder/api/rush-events")
            expect_status(response, 403, "Rusher blocked from rush events API")
            checks.append("Rush events API enforces officer-only access")

            response = client.get("/kappaalphaorder/api/rush-calendar?limit=50")
            expect_status(response, 403, "Rusher blocked from rush calendar API")
            checks.append("Rush calendar API enforces officer-only access")

            response = client.get("/kappaalphaorder/api/tasks/weekly")
            expect_status(response, 403, "Rusher blocked from weekly goals API")
            checks.append("Weekly goals API enforces officer-only access")

            response = client.get("/kappaalphaorder/api/users")
            expect_status(response, 403, "Rusher blocked from users API")
            checks.append("Users API enforces officer-only access")

            response = client.get("/kappaalphaorder/api/matching")
            expect_status(response, 403, "Rusher blocked from matching API")
            checks.append("Matching API enforces officer-only access")

            response = client.get("/kappaalphaorder/api/analytics/overview")
            expect_status(response, 403, "Rusher blocked from analytics API")
            checks.append("Analytics API enforces officer-only access")

            response = client.get("/kappaalphaorder/api/leaderboard/pnms?limit=25")
            expect_status(response, 403, "Rusher blocked from leaderboard API")
            checks.append("Leaderboard API enforces officer-only access")

            response = client.get("/kappaalphaorder/api/interests")
            expect_status(response, 403, "Rusher blocked from interests API")
            checks.append("Interests API enforces officer-only access")

            response = client.get("/kappaalphaorder/api/mobile/home")
            expect_status(response, 403, "Rusher blocked from mobile home API")
            checks.append("Mobile home API enforces officer-only access")

            response = client.get("/kappaalphaorder/api/mobile/pnms")
            expect_status(response, 403, "Rusher blocked from mobile pnms API")
            checks.append("Mobile pnms API enforces officer-only access")

            response = client.get("/kappaalphaorder/api/mobile/members")
            expect_status(response, 403, "Rusher blocked from mobile members API")
            checks.append("Mobile members API enforces officer-only access")

            response = client.get("/kappaalphaorder/api/calendar/share")
            expect_status(response, 403, "Rusher blocked from calendar share API")
            checks.append("Calendar share API enforces officer-only access")

            response = client.get("/kappaalphaorder/api/search/global?q=alex")
            expect_status(response, 200, "Rusher global search API")
            rusher_search_payload = response.json()
            rusher_commands = {
                str(item.get("action"))
                for item in rusher_search_payload.get("commands", [])
                if isinstance(item, dict) and item.get("action")
            }
            blocked_rusher_commands = {"add_rushee", "create_event", "backup_csv", "open_meetings"}
            if rusher_commands & blocked_rusher_commands:
                raise AssertionError("Rusher search should not expose officer or head-only commands.")
            if "create_lunch" in rusher_commands:
                raise AssertionError("Rusher search should not expose touchpoint scheduling.")
            if rusher_search_payload.get("members"):
                raise AssertionError("Rusher search should not expose member roster results.")
            checks.append("Global search hides restricted commands for rushers")

            response = client.get("/kappaalphaorder/api/search/global?q=tutorial")
            expect_status(response, 200, "Rusher tutorial search API")
            tutorial_search_payload = response.json()
            tutorial_commands = {
                str(item.get("action"))
                for item in tutorial_search_payload.get("commands", [])
                if isinstance(item, dict) and item.get("action")
            }
            if "open_tutorial" not in tutorial_commands:
                raise AssertionError("Tutorial queries should still expose tutorial access.")
            checks.append("Tutorial search exposes tutorial access")

            response = client.patch(
                f"/kappaalphaorder/api/users/{officer_user_id}/location",
                json={"city": "Blocked", "state": "TX"},
            )
            expect_status(response, 403, "Rusher blocked from editing other user location")
            checks.append("Location edit permissions enforce officer-only updates")

            response = client.post("/kappaalphaorder/api/auth/logout")
            expect_status(response, 200, "Member logout")
            sync_csrf_header()

            response = client.post(
                "/kappaalphaorder/api/auth/login",
                json={"username": "headseed", "access_code": "HeadSeed123!"},
            )
            expect_status(response, 200, "Head re-login")
            sync_csrf_header()

            response = client.get("/kappaalphaorder/api/auth/capabilities")
            expect_status(response, 200, "Head capabilities API")
            head_capabilities = response.json().get("capabilities", {})
            if not head_capabilities.get("can_manage_admin") or not head_capabilities.get("can_export_backups"):
                raise AssertionError("Head capabilities should expose admin and backup permissions.")
            checks.append("Head capabilities API works")

            response = client.get("/kappaalphaorder/api/admin/season/kickoff")
            expect_status(response, 200, "Head season kickoff API")
            kickoff_payload = response.json()
            if "steps" not in kickoff_payload or "progress" not in kickoff_payload:
                raise AssertionError("Season kickoff payload should include steps and progress.")

            response = client.patch(
                "/kappaalphaorder/api/admin/season/kickoff",
                json={
                    "season_label": "Fall 2026 Rush",
                    "rating_criteria_confirmed": True,
                    "member_invites_shared": True,
                    "kickoff_completed": True,
                },
            )
            expect_status(response, 200, "Head updates season kickoff")
            kickoff_payload = response.json()
            if kickoff_payload.get("season_label") != "Fall 2026 Rush":
                raise AssertionError("Season kickoff update should persist the season label.")
            if not kickoff_payload.get("kickoff_completed_at"):
                raise AssertionError("Season kickoff update should allow marking kickoff complete.")
            checks.append("Season kickoff API works")

            response = client.get("/kappaalphaorder/api/admin/overview")
            expect_status(response, 200, "Admin overview API")
            admin_overview = response.json()
            if "kickoff" not in admin_overview or "trust_center" not in admin_overview:
                raise AssertionError("Admin overview should include kickoff and trust_center payloads.")
            trust_center = admin_overview.get("trust_center", {})
            if "recent_jobs" not in trust_center or "capabilities" not in trust_center:
                raise AssertionError("Trust center payload should include capabilities and recent job history.")
            checks.append("Admin overview trust center payload works")

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

            response = client.patch(
                f"/kappaalphaorder/api/pnms/{pnm_id}/assignment",
                json={
                    "officer_user_id": officer_user_id,
                    "assignment_status": "in_progress",
                    "assignment_priority": 4,
                    "assignment_due_date": today,
                    "assignment_notes": "Priority outreach before chapter discussion.",
                },
            )
            expect_status(response, 200, "Assignment detail update")
            checks.append("Assignment orchestration endpoint works")

            response = client.post(
                "/kappaalphaorder/api/pnms/package/link",
                json={
                    "pnm_ids": [pnm_two_id, pnm_three_id],
                    "sync_assignment": True,
                },
            )
            expect_status(response, 200, "Package link endpoint")
            package_payload = response.json()
            package_group_id = package_payload.get("package_group_id")
            if not package_group_id:
                raise AssertionError("Package link response missing package_group_id.")

            response = client.get("/kappaalphaorder/api/pnms")
            expect_status(response, 200, "List PNMs after package link")
            pnms = {int(item.get("pnm_id")): item for item in response.json().get("pnms", []) if item.get("pnm_id")}
            first = pnms.get(pnm_id)
            second = pnms.get(pnm_two_id)
            third = pnms.get(pnm_three_id)
            if not first or not second or not third:
                raise AssertionError("Expected PNMs missing after package link.")
            if (
                first.get("package_group_id") != package_group_id
                or second.get("package_group_id") != package_group_id
                or third.get("package_group_id") != package_group_id
            ):
                raise AssertionError("Package link merge did not persist same package_group_id across linked PNMs.")
            if (
                int(first.get("assigned_officer_id") or 0) != officer_user_id
                or int(second.get("assigned_officer_id") or 0) != officer_user_id
                or int(third.get("assigned_officer_id") or 0) != officer_user_id
            ):
                raise AssertionError("Package link sync should align assigned officer across linked PNMs.")
            checks.append("Package deal merge link and assignment sync works")

            response = client.post(
                f"/kappaalphaorder/api/pnms/{pnm_id}/assignees",
                json={
                    "officer_user_id": officer_two_user_id,
                    "include_package": True,
                },
            )
            expect_status(response, 200, "Add secondary assignee")
            add_assignee_payload = response.json()
            assignment_team = (add_assignee_payload.get("pnm", {}) or {}).get("assigned_officers", [])
            assignment_ids = {
                int(item.get("user_id"))
                for item in assignment_team
                if isinstance(item, dict) and item.get("user_id")
            }
            if officer_user_id not in assignment_ids or officer_two_user_id not in assignment_ids:
                raise AssertionError("Assignment team should include both primary and secondary officers.")
            checks.append("Secondary assignee add flow works")

            response = client.get("/kappaalphaorder/api/mobile/pnms")
            expect_status(response, 200, "Mobile PNM payload")
            mobile_pnms = {
                int(item.get("pnm_id")): item for item in response.json().get("pnms", []) if item.get("pnm_id")
            }
            mobile_first = mobile_pnms.get(pnm_id)
            mobile_second = mobile_pnms.get(pnm_two_id)
            if not mobile_first or not mobile_second:
                raise AssertionError("Mobile payload missing linked PNMs.")
            if not mobile_first.get("package_group_id") or not mobile_second.get("package_group_id"):
                raise AssertionError("Mobile payload should include package_group_id for linked PNMs.")
            checks.append("Mobile PNM payload includes package metadata")

            response = client.patch(
                f"/kappaalphaorder/api/pnms/{pnm_id}/stage",
                json={"stage": "evaluated", "reason": "Completed initial officer review."},
            )
            expect_status(response, 200, "Funnel stage update")
            checks.append("Funnel stage update API works")

            response = client.get(f"/kappaalphaorder/api/pnms/{pnm_id}/stage-history")
            expect_status(response, 200, "Funnel stage history API")
            stage_history = response.json().get("history", [])
            if not stage_history:
                raise AssertionError("Funnel stage history should include at least one transition.")
            checks.append("Funnel stage history API works")

            response = client.get("/kappaalphaorder/api/assignments/overview")
            expect_status(response, 200, "Assignments overview API")
            checks.append("Assignments overview API works")

            response = client.get("/kappaalphaorder/api/events?include_past=1")
            expect_status(response, 200, "Unified events API")
            events_payload = response.json()
            if int(events_payload.get("count", 0)) < 2:
                raise AssertionError("Unified events feed should include both lunch and rush events.")
            checks.append("Unified event/workflow API works")

            response = client.get("/kappaalphaorder/api/funnel/summary")
            expect_status(response, 200, "Funnel summary API")
            if int(response.json().get("total_pnms", 0)) < 1:
                raise AssertionError("Funnel summary should include at least one PNM.")
            checks.append("Funnel summary API works")

            response = client.get("/kappaalphaorder/api/notifications/digest?period=daily")
            expect_status(response, 200, "Notification digest API")
            checks.append("Notification digest API works")

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

            response = client.post("/kappaalphaorder/api/auth/logout")
            expect_status(response, 200, "Head logout before second officer checks")
            sync_csrf_header()

            response = client.post(
                "/kappaalphaorder/api/auth/login",
                json={"username": officer_two_username, "access_code": officer_two_password},
            )
            expect_status(response, 200, "Second officer login")
            sync_csrf_header()

            response = client.get("/kappaalphaorder/api/assignments/mine")
            expect_status(response, 200, "Assignments mine API for secondary officer")
            mine_rows = response.json().get("assignments", [])
            mine_ids = {int(item.get("pnm_id")) for item in mine_rows if item.get("pnm_id")}
            if pnm_id not in mine_ids:
                raise AssertionError("Secondary officer assignment list should include linked assigned PNM.")
            checks.append("Assignments mine API works for secondary assignees")

            response = client.get("/kappaalphaorder/api/export/contacts-assigned.vcf")
            expect_status(response, 200, "Assigned contacts export for secondary officer")
            assigned_contacts_text = response.content.decode("utf-8", errors="ignore")
            if "BEGIN:VCARD" not in assigned_contacts_text or "Alex Carter" not in assigned_contacts_text:
                raise AssertionError("Assigned contacts export missing expected linked PNM vCard.")
            checks.append("Assigned contacts export works for officers")

            response = client.post("/kappaalphaorder/api/auth/logout")
            expect_status(response, 200, "Second officer logout")
            sync_csrf_header()

            response = client.post(
                "/kappaalphaorder/api/auth/login",
                json={"username": "headseed", "access_code": "HeadSeed123!"},
            )
            expect_status(response, 200, "Head re-login before backup checks")
            sync_csrf_header()

            response = client.get("/kappaalphaorder/api/export/csv")
            expect_status(response, 200, "CSV export API")
            content_type = response.headers.get("content-type", "")
            if "application/zip" not in content_type:
                raise AssertionError(f"CSV export returned unexpected content-type: {content_type}")
            checks.append("CSV backup export works")

            response = client.get("/kappaalphaorder/api/admin/storage")
            expect_status(response, 200, "Storage diagnostics API")
            checks.append("Storage diagnostics endpoint works")

            temp_delete_officer_username = "cleanupofficer"
            temp_delete_officer_password = "CleanupOfficer123!"
            response = client.post(
                "/kappaalphaorder/api/auth/register",
                json={
                    "username": temp_delete_officer_username,
                    "access_code": temp_delete_officer_password,
                    "emoji": "🧹",
                    "city": "Waco",
                    "state": "TX",
                },
            )
            expect_status(response, 200, "Temporary officer registration for delete flow")

            response = client.get("/kappaalphaorder/api/users/pending")
            expect_status(response, 200, "Pending users list before manual delete")
            temp_pending = next(
                (item for item in response.json().get("pending", []) if item.get("username") == temp_delete_officer_username),
                None,
            )
            if temp_pending is None:
                raise AssertionError("Temporary officer should appear in the pending queue before approval.")
            temp_delete_officer_id = int(temp_pending["user_id"])

            response = client.post(f"/kappaalphaorder/api/users/pending/{temp_delete_officer_id}/approve")
            expect_status(response, 200, "Approve temporary officer for delete flow")

            response = client.delete(f"/kappaalphaorder/api/users/{head_user_id}")
            expect_status(response, 400, "Head self-delete blocked")
            checks.append("Head self-delete guard works")

            response = client.delete(f"/kappaalphaorder/api/users/{temp_delete_officer_id}")
            expect_status(response, 200, "Head deletes rush team member")
            deleted_payload = response.json().get("deleted_user", {})
            if deleted_payload.get("username") != temp_delete_officer_username:
                raise AssertionError("Delete user API should return the removed username.")
            checks.append("Head can delete rush team members")

            response = client.post(
                "/kappaalphaorder/api/auth/login",
                json={"username": temp_delete_officer_username, "access_code": temp_delete_officer_password},
            )
            expect_status(response, 401, "Deleted officer login blocked")
            checks.append("Deleted rush team members cannot sign in")

            response = client.get("/kappaalphaorder/api/admin/rush-officers")
            expect_status(response, 200, "Rush officer metrics after delete")
            officer_usernames = {item.get("username") for item in response.json().get("rush_officers", [])}
            if temp_delete_officer_username in officer_usernames:
                raise AssertionError("Deleted officer should be removed from admin leadership metrics.")
            checks.append("Deleted rush team members disappear from leadership metrics")

            response = client.post(
                "/kappaalphaorder/api/admin/season/reset",
                json={
                    "confirm_phrase": "RESET RUSH SEASON",
                    "archive_label": "Smoke Reset",
                    "head_chair_confirmation": True,
                },
            )
            expect_status(response, 200, "Season reset deletes non-head team accounts")
            archive_payload = response.json().get("archive", {})
            if int(archive_payload.get("deleted_member_count", 0)) < 1:
                raise AssertionError("Season reset should report that non-head team accounts were deleted.")
            checks.append("Season reset removes non-head team accounts")

            response = client.get("/kappaalphaorder/api/users")
            expect_status(response, 200, "Users list after season reset")
            remaining_roles = {item.get("role") for item in response.json().get("users", [])}
            if remaining_roles != {"Head Rush Officer"}:
                raise AssertionError("Season reset should leave only Head Rush Officer accounts.")
            checks.append("Season reset leaves only head accounts")

            response = client.post(
                "/kappaalphaorder/api/auth/login",
                json={"username": officer_username, "access_code": officer_password},
            )
            expect_status(response, 401, "Reset-deleted officer login blocked")
            response = client.post(
                "/kappaalphaorder/api/auth/login",
                json={"username": member_username, "access_code": member_password},
            )
            expect_status(response, 401, "Reset-deleted member login blocked")
            checks.append("Season reset deleted accounts cannot sign in")

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
