"""Chapter artifacts + resume: no redoing finished chapters."""
from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path

from tfv2.product import chapter_artifact
from tests.test_longdoc import make_pdf


class ChapterArtifactTests(unittest.TestCase):
    def test_build_and_resume_three_chapters(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            pdf = make_pdf(td, toc=True, pages=90)
            out = td / "book"
            idx = chapter_artifact.build_index(pdf, out)
            self.assertEqual(idx["page_count"], 90)
            self.assertGreaterEqual(len(idx["chapters"]), 3)
            index_path = out / "index.json"

            first = chapter_artifact.run(index_path, lambda c: {"artifact_id": "aid_" + c["id"]}, stop_after=1)
            self.assertEqual(sum(1 for c in first["chapters"] if c["status"] == "done"), 1)
            self.assertTrue(chapter_artifact.pending(first))

            second = chapter_artifact.run(index_path, lambda c: {"artifact_id": "aid_" + c["id"]})
            self.assertEqual([c["status"] for c in second["chapters"]], ["done"] * len(second["chapters"]))

    def test_subprocess_worker_timeout_is_killed(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            pdf = make_pdf(td, toc=True, pages=90)
            out = td / "book"
            chapter_artifact.build_index(pdf, out)
            index_path = out / "index.json"
            code = "import time; time.sleep(2)"
            started = time.time()
            one = chapter_artifact.run_subprocess(index_path, timeout_sec=0.3, stop_after=1,
                                                  worker_cmd=[sys.executable, "-c", code])
            self.assertEqual(one["chapters"][0]["status"], "failed")
            self.assertIn("TimeoutError", one["chapters"][0]["error"])
            self.assertLess(time.time() - started, 1.5)

    def test_global_budget_stops_and_leaves_pending(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            pdf = make_pdf(td, toc=True, pages=90)
            out = td / "book"
            chapter_artifact.build_index(pdf, out)
            index_path = out / "index.json"
            code = "import time; time.sleep(2)"
            started = time.time()
            one = chapter_artifact.run_subprocess(
                index_path, timeout_sec=5, worker_cmd=[sys.executable, "-c", code],
                global_budget_sec=0.3,
            )
            self.assertLess(time.time() - started, 1.5)
            statuses = [c["status"] for c in one["chapters"]]
            self.assertIn("failed", statuses)
            self.assertIn("pending", statuses)

    def test_subprocess_worker_success(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            pdf = make_pdf(td, toc=True, pages=90)
            out = td / "book"
            chapter_artifact.build_index(pdf, out)
            index_path = out / "index.json"
            code = ("import sys,json,pathlib;"
                    "pathlib.Path(sys.argv[2]).write_text(json.dumps({'artifact_id':'aid'}))")
            one = chapter_artifact.run_subprocess(index_path, timeout_sec=5, stop_after=1,
                                                  worker_cmd=[sys.executable, "-c", code])
            self.assertEqual(one["chapters"][0]["status"], "done")
            self.assertEqual(one["chapters"][0]["artifact_id"], "aid")

    def test_gate_passed_marks_validated(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            pdf = make_pdf(td, toc=True, pages=90)
            out = td / "book"
            chapter_artifact.build_index(pdf, out)
            index_path = out / "index.json"
            code = ("import sys,json,pathlib;"
                    "pathlib.Path(sys.argv[2]).write_text(json.dumps({'artifact_id':'aid','gate_passed':True}))")
            one = chapter_artifact.run_subprocess(index_path, timeout_sec=5, stop_after=1,
                                                  worker_cmd=[sys.executable, "-c", code])
            self.assertEqual(one["chapters"][0]["status"], "validated")

    def test_hard_timeout_marks_failed_then_resumes(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            pdf = make_pdf(td, toc=True, pages=90)
            out = td / "book"
            idx = chapter_artifact.build_index(pdf, out)
            index_path = out / "index.json"

            def slow(c):
                time.sleep(0.3)
                return {"artifact_id": "late_" + c["id"]}

            one = chapter_artifact.run(index_path, slow, stop_after=1, timeout_sec=0.05)
            self.assertEqual(one["chapters"][0]["status"], "failed")
            self.assertIn("TimeoutError", one["chapters"][0]["error"])
            self.assertIn("seconds", one["chapters"][0])

            two = chapter_artifact.run(index_path, lambda c: {"artifact_id": "ok_" + c["id"]}, timeout_sec=5)
            self.assertEqual([c["status"] for c in two["chapters"]], ["done"] * len(two["chapters"]))

    def test_failed_chapter_retries(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            pdf = make_pdf(td, toc=True, pages=90)
            out = td / "book"
            idx = chapter_artifact.build_index(pdf, out)
            index_path = out / "index.json"
            failed = {idx["chapters"][1]["id"]}

            def builder(c):
                if c["id"] in failed:
                    failed.clear()
                    raise RuntimeError("boom")
                return {"artifact_id": "aid_" + c["id"]}

            one = chapter_artifact.run(index_path, builder)
            self.assertEqual(one["chapters"][1]["status"], "failed")
            two = chapter_artifact.run(index_path, builder)
            self.assertEqual([c["status"] for c in two["chapters"]], ["done"] * len(two["chapters"]))


if __name__ == "__main__":
    unittest.main()
