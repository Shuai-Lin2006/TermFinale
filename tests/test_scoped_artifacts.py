"""Scoped modules: range must replace material id before handler runs."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from tfv2.product import scoped_artifacts


class ScopedArtifactTests(unittest.TestCase):
    def test_wrap_replaces_material_with_scoped(self):
        seen = {}

        def handler(material):
            seen["id"] = material["id"]
            return {"status": "done", "artifact_id": material["id"]}

        with patch.object(scoped_artifacts, "create_scoped_artifact",
                          return_value={"id": "scoped1", "page_count": 3, "scope": {}}):
            out = scoped_artifacts.wrap(handler, "2-4")({"id": "orig", "title": "t"})
        self.assertEqual(seen["id"], "scoped1")
        self.assertEqual(out["scope"]["page_count"], 3)
        self.assertEqual(out["scope"]["requested"], "2-4")

    def test_all_returns_original(self):
        def handler(material):
            return {"status": "done"}

        self.assertIs(scoped_artifacts.wrap(handler, "all"), handler)


if __name__ == "__main__":
    unittest.main()
