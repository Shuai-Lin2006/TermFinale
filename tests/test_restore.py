"""备份恢复工具：只恢复 DB、先备份当前库、拒绝坏备份。"""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from tools.restore_backup import inspect_backup, restore


def _make_db(path: Path, courses: int = 1) -> None:
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE courses (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE materials (id INTEGER PRIMARY KEY, filename TEXT);
        CREATE TABLE generated_files (id INTEGER PRIMARY KEY, filename TEXT);
    """)
    for i in range(courses):
        con.execute("INSERT INTO courses(name) VALUES (?)", (f"c{i}",))
    con.commit()
    con.close()


class RestoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="tf_restore_"))
        self.data = self.tmp / "data"
        self.data.mkdir()
        self.backup = self.tmp / "backup.db"
        _make_db(self.backup, courses=3)
        self.target = self.data / "term_finale_pro.db"
        _make_db(self.target, courses=1)

    def test_inspect_counts(self):
        info = inspect_backup(self.backup)
        self.assertEqual(info["integrity"], "ok")
        self.assertEqual(info["counts"]["courses"], 3)

    def test_dry_run_does_not_write(self):
        before = self.target.read_bytes()
        res = restore(self.backup, self.data, yes=False)
        self.assertTrue(res["dry_run"])
        self.assertEqual(self.target.read_bytes(), before)

    def test_restore_backs_up_current_and_replaces(self):
        res = restore(self.backup, self.data, yes=True)
        self.assertFalse(res["dry_run"])
        self.assertTrue(Path(res["pre_restore"]).is_file())
        con = sqlite3.connect(self.target)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM courses").fetchone()[0], 3)
        con.close()

    def test_rejects_non_sqlite(self):
        bad = self.tmp / "bad.db"
        bad.write_text("not a database", encoding="utf-8")
        with self.assertRaises(ValueError):
            inspect_backup(bad)

    def test_rejects_missing_tables(self):
        bad = self.tmp / "bad.db"
        con = sqlite3.connect(bad)
        con.execute("CREATE TABLE courses (id INTEGER PRIMARY KEY)")
        con.commit()
        con.close()
        with self.assertRaises(ValueError):
            inspect_backup(bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
