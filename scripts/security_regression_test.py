#!/usr/bin/env python3
"""Offline security regressions; all application state lives in a temporary directory."""
from __future__ import annotations

import base64
import csv
import io
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from contextlib import ExitStack
from email.message import Message
from unittest.mock import patch
from urllib.request import HTTPHandler, HTTPSHandler
from urllib.response import addinfourl

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from smoke_test import configure_env


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5nXioAAAAASUVORK5CYII="
)


class SecurityRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if "app.main" in sys.modules:
            raise RuntimeError("Run security regressions in a fresh process to isolate application data.")
        cls.resources = ExitStack()
        cls.addClassCleanup(cls.resources.close)
        cls.tmp = cls.resources.enter_context(tempfile.TemporaryDirectory(prefix="bidboard-security-"))
        cls.resources.enter_context(patch.dict(os.environ))
        configure_env(Path(cls.tmp))
        os.environ.pop("RENDER", None)
        os.environ.update(DEMO_ENABLED="0", ENFORCE_CSRF="1", AUTO_CREATE_HEAD_SEED="1")
        cls.resources.enter_context(patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden in security tests")))
        cls.resources.enter_context(patch.object(socket, "getaddrinfo", side_effect=AssertionError("DNS forbidden in security tests")))
        from app import main
        from fastapi.testclient import TestClient

        cls.m = main
        cls.client = cls.resources.enter_context(TestClient(main.app))
        cls.tenant = main.tenant_context_from_row(main.require_tenant_exists("kappaalphaorder"))
        main.platform_create_tenant(main.TenantCreateRequest(
            slug="security-other", display_name="Security Other", chapter_name="Test",
            head_seed_username="otherhead", head_seed_first_name="Other", head_seed_last_name="Head",
            head_seed_pledge_class="Test", head_seed_access_code="OtherHead123!",
        ), {})
        cls.other = main.tenant_context_from_row(main.require_tenant_exists("security-other"))
        for username, role in (("securityofficer", main.ROLE_RUSH_OFFICER), ("securitymember", main.ROLE_RUSHER)):
            with main.db_session(cls.tenant.db_path) as conn:
                main.ensure_seed_data(conn, seed_username=username, seed_access_code="Security123!")
                conn.execute("UPDATE users SET role = ?, emoji = ? WHERE username = ?",
                             (role, "S" if role == main.ROLE_RUSH_OFFICER else None, username))

    def setUp(self):
        self.client.cookies.clear()
        self.client.headers.pop("X-CSRF-Token", None)
        self.client.headers["Origin"] = "http://testserver"
        self.m._RATE_LIMIT_EVENTS.clear()
        self.m._LOGIN_ATTEMPTS.clear()
        self.m._LOGIN_BLOCKED_UNTIL.clear()

    def login(self, username="headseed", password="HeadSeed123!", tenant="kappaalphaorder"):
        response = self.client.post(f"/{tenant}/api/auth/login", json={"username": username, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        self.client.headers["X-CSRF-Token"] = self.client.cookies.get(self.m.CSRF_COOKIE)
        return response.json()["user"]

    def create_pnm(self, **overrides):
        payload = dict(first_name="Alex", last_name="Security", class_year="F", hometown="Austin", state="TX",
                       instagram_handle="@security_test", first_event_date="2026-09-16",
                       interests=["Leadership"], stereotype="Leader", notes="Private officer note")
        payload.update(overrides)
        response = self.client.post("/kappaalphaorder/api/pnms", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["pnm"]

    def test_contact_exports_escape_all_newline_encodings(self):
        self.login("securityofficer", "Security123!")
        pnm = self.create_pnm(first_name="Alex\rTEL:9999999\rZ")
        self.login()
        for route in (f"contacts/{pnm['pnm_id']}.vcf", "contacts.vcf", "contacts-assigned.vcf"):
            with self.subTest(route=route):
                response = self.client.get(f"/kappaalphaorder/api/export/{route}")
                self.assertEqual(response.status_code, 200, response.text)
                self.assertNotIn("TEL:9999999", response.text.splitlines())
                self.assertNotIn("\r", response.text.replace("\r\n", ""))
                self.assertIn("Alex\\nTEL:9999999\\nZ", response.text)
        for value in ("A\rB", "A\nB", "A\r\nB"):
            self.assertEqual(self.m.vcard_escape(value), "A\\nB")
        self.assertEqual(self.m.vcard_escape("A;B,C\\D"), "A\\;B\\,C\\\\D")

    def mock_fetch(self, fetch, responses):
        seen = []

        def fake_open(_handler, request):
            seen.append(request.full_url)
            code, headers, body = responses[request.full_url]
            message = Message()
            for key, value in headers.items():
                message[key] = value
            response = addinfourl(io.BytesIO(body), message, request.full_url, code=code)
            response.msg = "Found" if code == 302 else "OK"
            return response

        with patch.object(HTTPSHandler, "https_open", fake_open), patch.object(HTTPHandler, "http_open", fake_open):
            result = fetch()
        return result, seen

    def test_remote_image_redirect_cannot_escape_allowlist(self):
        initial = "https://unavatar.io/instagram/security?fallback=false"
        for target in ("http://127.0.0.1/private", "https://127.0.0.1/private", "https://attacker.invalid/a.png",
                       "http://www.instagram.com/a.png", "https://www.instagram.com:8443/a.png"):
            with self.subTest(target=target):
                result, seen = self.mock_fetch(lambda: self.m.fetch_image_from_url(initial), {
                    initial: (302, {"Location": target}, b""),
                    target: (200, {"Content-Type": "image/png"}, PNG),
                })
                self.assertIsNone(result)
                self.assertEqual(seen, [initial])

    def test_remote_profile_and_api_redirects_cannot_escape_allowlist(self):
        target = "https://attacker.invalid/private"
        for initial, fetch in (
            ("https://www.instagram.com/security/", lambda: self.m.fetch_instagram_og_image_url("security")),
            ("https://www.instagram.com/api/v1/users/web_profile_info/?username=security",
             lambda: self.m.fetch_instagram_api_image_url("security")),
        ):
            with self.subTest(initial=initial):
                result, seen = self.mock_fetch(fetch, {
                    initial: (302, {"Location": target}, b""),
                    target: (200, {"Content-Type": "text/plain"}, b"{}"),
                })
                self.assertIsNone(result)
                self.assertEqual(seen, [initial])

    def test_every_redirect_hop_and_status_is_checked(self):
        initial = "https://unavatar.io/instagram/security"
        cdn = "https://images.cdninstagram.com/photo.png"
        target = "http://169.254.169.254/private"
        for status in (301, 302, 303, 307, 308):
            with self.subTest(status=status):
                result, seen = self.mock_fetch(lambda: self.m.fetch_image_from_url(initial), {
                    initial: (status, {"Location": cdn}, b""),
                    cdn: (status, {"Location": target}, b""),
                    target: (200, {"Content-Type": "image/png"}, PNG),
                })
                self.assertIsNone(result)
                self.assertEqual(seen, [initial, cdn])

    def test_relative_redirect_and_profile_metadata_still_work(self):
        initial = "https://www.instagram.com/security/"
        redirected = "https://www.instagram.com/security/avatar"
        cdn = "https://images.cdninstagram.com/photo.png?signature=abc%2B123"
        result, seen = self.mock_fetch(lambda: self.m.fetch_instagram_og_image_url("security"), {
            initial: (302, {"Location": "avatar"}, b""),
            redirected: (200, {"Content-Type": "text/html"}, f'<meta property="og:image" content="{cdn}">'.encode()),
        })
        self.assertEqual(result, cdn)
        self.assertEqual(seen, [initial, redirected])
        api = "https://www.instagram.com/api/v1/users/web_profile_info/?username=security"
        result, _ = self.mock_fetch(lambda: self.m.fetch_instagram_api_image_url("security"), {
            api: (200, {"Content-Type": "application/json"}, ('{"data":{"user":{"profile_pic_url_hd":"' + cdn + '"}}}').encode()),
        })
        self.assertEqual(result, cdn)

    def test_allowed_redirects_and_image_limits_still_work(self):
        initial = "https://unavatar.io/instagram/security?fallback=false"
        cdn = "https://images.cdninstagram.com/photo.png?signature=abc%2B123"
        result, seen = self.mock_fetch(lambda: self.m.fetch_image_from_url(initial), {
            initial: (302, {"Location": cdn}, b""), cdn: (200, {"Content-Type": "image/png"}, PNG),
        })
        self.assertEqual(result, (PNG, ".png"))
        self.assertEqual(seen, [initial, cdn])
        with patch.object(self.m, "MAX_PNM_PHOTO_BYTES", 8):
            result, _ = self.mock_fetch(lambda: self.m.fetch_image_from_url(cdn), {
                cdn: (200, {"Content-Type": "image/png"}, PNG),
            })
            self.assertIsNone(result)
        result, _ = self.mock_fetch(lambda: self.m.fetch_image_from_url(cdn), {
            cdn: (200, {"Content-Type": "image/png"}, b"<script>not an image</script>"),
        })
        self.assertIsNone(result)

    def test_remote_url_policy_rejects_ambiguous_authorities(self):
        for url in ("https://www.instagram.com:8443/image", "https://user:pass@www.instagram.com/image",
                    "https://www.instagram.com/image\n", "https://www.instagram.com:invalid/image",
                    "https://www.instagram.com.attacker.invalid/image", "https://127.0.0.1/image"):
            with self.subTest(url=url):
                self.assertFalse(self.m.is_allowed_remote_fetch_url(url))
        self.assertTrue(self.m.is_allowed_remote_fetch_url("https://www.instagram.com:443/image"))

    def test_tenant_sessions_and_photos_cannot_cross_organizations(self):
        self.login()
        pnm = self.create_pnm()
        response = self.client.post(f"/kappaalphaorder/api/pnms/{pnm['pnm_id']}/photo",
                                    files={"photo": ("../../unsafe.png", PNG, "image/png")})
        self.assertEqual(response.status_code, 200, response.text)
        photo = response.json()["pnm"]["photo_url"]
        self.assertNotIn("unsafe", photo)
        self.assertEqual(self.client.get(photo).status_code, 200)
        self.assertEqual(self.client.get("/security-other/api/pnms").status_code, 401)
        self.assertEqual(self.client.get("/platform/api/tenants").status_code, 401)
        self.client.cookies.clear()
        self.client.headers.pop("X-CSRF-Token", None)
        self.login("otherhead", "OtherHead123!", tenant="security-other")
        self.assertEqual(self.client.get(photo).status_code, 401)
        self.assertEqual(self.client.get("/kappaalphaorder/api/pnms").status_code, 401)
        self.client.cookies.clear()
        self.assertEqual(self.client.get(photo).status_code, 401)

    def test_member_cannot_access_officer_or_head_data(self):
        self.login()
        pnm = self.create_pnm()
        self.login("securitymember", "Security123!")
        for route in ("export/csv", "export/sqlite", "export/contacts.vcf", "admin/storage", "users/pending",
                      f"pnms/{pnm['pnm_id']}/meeting", "chat/officer", "workspace/command", "calendar/share"):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(f"/kappaalphaorder/api/{route}").status_code, 403)
        response = self.client.get(f"/kappaalphaorder/api/pnms/{pnm['pnm_id']}")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("notes", response.json()["pnm"])
        self.assertNotIn("assignment_notes", response.json()["pnm"])
        self.assertIn("no-store", response.headers["cache-control"])

    def test_csrf_blocks_missing_token_and_foreign_origin(self):
        self.login()
        token = self.client.headers.pop("X-CSRF-Token")
        route = "/kappaalphaorder/api/users/me"
        self.assertEqual(self.client.patch(route, json={"city": "Austin"}).status_code, 403)
        self.client.headers["X-CSRF-Token"] = token
        self.assertEqual(self.client.patch(route, headers={"Origin": "https://attacker.invalid"},
                                           json={"city": "Austin"}).status_code, 403)
        self.assertEqual(self.client.patch(route, json={"city": "Austin"}).status_code, 200)

    def test_officer_cannot_modify_another_creators_profile(self):
        self.login()
        pnm = self.create_pnm()
        self.login("securityofficer", "Security123!")
        route = f"/kappaalphaorder/api/pnms/{pnm['pnm_id']}"
        self.assertEqual(self.client.patch(route, json={"first_name": "Changed"}).status_code, 403)
        before = set(self.tenant.pnm_uploads_dir.glob("*"))
        self.assertEqual(self.client.post(route + "/photo", files={"photo": ("test.png", PNG, "image/png")}).status_code, 403)
        self.assertEqual(set(self.tenant.pnm_uploads_dir.glob("*")), before)

    def test_upload_containment_and_type(self):
        from fastapi import HTTPException
        outside = Path(self.tmp) / "outside.png"
        outside.write_bytes(PNG)
        root = Path(self.tmp) / "containment"
        root.mkdir(exist_ok=True)
        (root / "link.png").symlink_to(outside)
        for name in ("../outside.png", "link.png"):
            with self.assertRaises(HTTPException):
                self.m.safe_upload_file(root, name, pattern=r"[A-Za-z0-9._-]+\.png")
        self.login()
        pnm = self.create_pnm()
        response = self.client.post(f"/kappaalphaorder/api/pnms/{pnm['pnm_id']}/photo",
                                    files={"photo": ("fake.png", b"<svg onload=bad()>", "image/png")})
        self.assertEqual(response.status_code, 400)

    def test_csv_export_quotes_direct_formula_prefixes(self):
        for value in ("=1+1", "+1+1", "-1+1", "@SUM(A1)", "\t=1+1"):
            output = self.m.csv_bytes_from_rows(["name"], [{"name": value}]).decode()
            self.assertEqual(list(csv.DictReader(io.StringIO(output)))[0]["name"], "'" + value)
        self.assertEqual(self.m.csv_safe_cell(42), 42)
        self.assertEqual(self.m.csv_safe_cell("Alice"), "Alice")

    def test_import_stops_reading_at_row_limit(self):
        self.login()
        real_reader = csv.DictReader
        consumed = []

        class CountingReader(real_reader):
            def __next__(self):
                row = super().__next__()
                consumed.append(row)
                return row

        body = "First Name,Last Name,Instagram Handle\n" + "Alex,Security,@import_test\n" * 10
        with patch.object(self.m, "MAX_GOOGLE_FORM_IMPORT_ROWS", 2), patch.object(csv, "DictReader", CountingReader):
            response = self.client.post("/kappaalphaorder/api/admin/import/google-form",
                                        files={"file": ("test.csv", body, "text/csv")})
        self.assertEqual(response.status_code, 413, response.text)
        self.assertEqual(len(consumed), 3)
        with self.m.db_session(self.tenant.db_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM pnms WHERE instagram_handle = '@import_test'").fetchone()[0], 0)

    def test_malformed_import_returns_client_error(self):
        self.login()
        body = "First Name,Last Name,Instagram Handle\n" + ("A" * (csv.field_size_limit() + 1)) + ",Security,@import_test\n"
        response = self.client.post("/kappaalphaorder/api/admin/import/google-form",
                                    files={"file": ("test.csv", body, "text/csv")})
        self.assertEqual(response.status_code, 400, response.text)

    def test_normal_csv_import_still_works(self):
        self.login()
        body = "First Name,Last Name,Instagram Handle\nAlex,Normal,@normal_import\n"
        response = self.client.post("/kappaalphaorder/api/admin/import/google-form",
                                    files={"file": ("test.csv", body, "text/csv")})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["created_count"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
