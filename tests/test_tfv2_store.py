"""聊天持久化测试。"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import tfv2.store as store


class StoreTests(unittest.TestCase):
    def test_chat_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            old = store.DB_PATH
            store.DB_PATH = Path(d) / "v2.sqlite3"
            try:
                store.append_chat("a", "s", "user", "问")
                store.append_chat("a", "s", "assistant", "答")
                msgs = store.list_chat("a", "s")
                self.assertEqual([m["role"] for m in msgs], ["user", "assistant"])
                store.clear_chat("a", "s")
                self.assertEqual(store.list_chat("a", "s"), [])
            finally:
                store.DB_PATH = old


if __name__ == "__main__":
    unittest.main()
