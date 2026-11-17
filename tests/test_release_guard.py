"""Release guards for paths that only break in the packaged app."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tfv2.store as chat_store
from fastapi.testclient import TestClient
from tfv2.api.product_app import _safe_export_name, app as product_app
from tfv2.product import store as product_store


class CourseDeletionTest(unittest.TestCase):
    def test_delete_course_records_uses_chat_database(self):
        """Chat lives in a separate DB; deletion must not query it in product.sqlite3."""
        with tempfile.TemporaryDirectory() as d:
            pdb = Path(d) / "product.sqlite3"
            cdb = Path(d) / "chat.sqlite3"
            with patch.object(product_store, "DB_PATH", pdb), patch.object(chat_store, "DB_PATH", cdb):
                self.assertEqual(product_store.delete_course_records("c-test", ["artifact-test"]), 0)
                self.assertTrue(pdb.is_file())
                self.assertTrue(cdb.is_file())

    def test_delete_artifact_records_uses_chat_database(self):
        with tempfile.TemporaryDirectory() as d:
            pdb = Path(d) / "product.sqlite3"
            cdb = Path(d) / "chat.sqlite3"
            with patch.object(product_store, "DB_PATH", pdb), patch.object(chat_store, "DB_PATH", cdb):
                self.assertEqual(product_store.delete_artifact_records("artifact-test"), 0)
                self.assertTrue(pdb.is_file())
                self.assertTrue(cdb.is_file())




class ProductSurfaceSecurityTest(unittest.TestCase):
    def test_cross_site_origin_is_rejected(self):
        client = TestClient(product_app)
        r = client.get("/api/health", headers={"Origin": "https://evil.example"})
        self.assertEqual(r.status_code, 403)

    def test_loopback_origin_is_allowed(self):
        client = TestClient(product_app, base_url="http://127.0.0.1:8907")
        r = client.get("/api/health", headers={"Origin": "http://127.0.0.1:8907"})
        self.assertEqual(r.status_code, 200)

    def test_other_local_port_is_rejected(self):
        client = TestClient(product_app, base_url="http://127.0.0.1:8907")
        r = client.get("/api/health", headers={"Origin": "http://127.0.0.1:9999"})
        self.assertEqual(r.status_code, 403)

    def test_export_filename_cannot_escape_desktop(self):
        self.assertEqual(_safe_export_name("../../etc/passwd"), "passwd")
        self.assertNotIn("/", _safe_export_name("a/b.pdf"))
        self.assertNotIn("\\", _safe_export_name("a\\b.pdf"))


if __name__ == "__main__":
    unittest.main()
