"""本地 API 鉴权：无 token 的跨站/裸请求不能读数据，页面首次加载下发 cookie。"""
from __future__ import annotations

import os
import tempfile
import unittest

os.environ["TERMFINALE_HOME"] = tempfile.mkdtemp(prefix="tf_security_")
os.environ["TERMFINALE_SKIP_PROJECT_ENV"] = "1"

from fastapi.testclient import TestClient  # noqa: E402
from server.app import app  # noqa: E402


class LocalAuthTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.client.cookies.clear()

    def test_api_without_cookie_forbidden(self):
        r = self.client.get("/api/courses")
        self.assertEqual(r.status_code, 403)
        self.assertIn("token", r.json().get("detail", ""))

    def test_page_sets_cookie_then_api_ok(self):
        page = self.client.get("/dashboard.html")
        self.assertEqual(page.status_code, 200)
        self.assertIn("tf_token", self.client.cookies)
        r = self.client.get("/api/courses")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)

    def test_evil_origin_rejected(self):
        self.client.get("/dashboard.html")
        r = self.client.post("/api/backup", headers={"Origin": "https://evil.example"})
        self.assertEqual(r.status_code, 403)
        self.assertIn("origin", r.json().get("detail", ""))

    def test_same_origin_allowed(self):
        self.client.get("/dashboard.html")
        r = self.client.post("/api/backup",
                             headers={"Origin": "http://127.0.0.1:8900"})
        self.assertEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TokenPersistenceTest(unittest.TestCase):
    def test_token_file_is_private_and_reused(self):
        from core import paths
        from server.app import _AUTH_TOKEN
        token_file = paths.data_dir() / ".session_token"
        self.assertTrue(token_file.is_file())
        self.assertEqual(token_file.read_text(encoding="utf-8").strip(), _AUTH_TOKEN)
        mode = token_file.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)
