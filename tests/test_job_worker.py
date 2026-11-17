"""Worker requires queued and can skip files without artifact."""
from __future__ import annotations
import tempfile
import unittest
from tfv2.product.job_plan import FileSpec, build_plan
from tfv2.product.job_state import JobStage, JobStore
from tfv2.product.job_worker import run_job


class Tests(unittest.TestCase):
    def test_requires_queued(self):
        with tempfile.TemporaryDirectory() as td:
            s = JobStore(td); rec = s.create(build_plan([FileSpec(name="A", pages=10)]))
            with self.assertRaises(ValueError):
                run_job(rec.job_id, s)

    def test_skip_no_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            s = JobStore(td); rec = s.create(build_plan([FileSpec(name="A", pages=10)]))
            s.preview(rec.job_id); s.confirm(rec.job_id)
            out = run_job(rec.job_id, s)
            self.assertEqual(out["stage"], "done")
            self.assertEqual(out["events"][-1]["stage"], "done")


if __name__ == "__main__":
    unittest.main()
