"""Job state: no confirm before preview."""
from __future__ import annotations
import tempfile
import unittest
from tfv2.product.job_plan import FileSpec, build_plan
from tfv2.product.job_state import JobStage, JobStore


class Tests(unittest.TestCase):
    def test_preview_gate(self):
        with tempfile.TemporaryDirectory() as td:
            store = JobStore(td); rec = store.create(build_plan([FileSpec(name="A", pages=10)]))
            with self.assertRaises(ValueError):
                store.confirm(rec.job_id)
            store.preview(rec.job_id)
            rec = store.confirm(rec.job_id)
            self.assertEqual(rec.stage, JobStage.QUEUED)
            self.assertTrue(rec.confirmed)
            rec = store.start(rec.job_id)
            self.assertEqual(rec.stage, JobStage.RUNNING)

    def test_cancel(self):
        with tempfile.TemporaryDirectory() as td:
            store = JobStore(td); rec = store.create(build_plan([FileSpec(name="A", pages=10)]))
            store.preview(rec.job_id); self.assertEqual(store.cancel(rec.job_id).stage, JobStage.PAUSED)


if __name__ == "__main__":
    unittest.main()
