import json
import tempfile
import unittest
from pathlib import Path

from tfv2.product import agent, service, store


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "artifacts"; self.root.mkdir()
        self.aid = "agent_art"; d = self.root / self.aid; d.mkdir()
        (d / "manifest.json").write_text(json.dumps({"page_count": 2, "scope_pages": [1, 2]}), encoding="utf-8")
        (d / "sections.json").write_text(json.dumps([{
            "id": "s1", "title": "换路定则", "blocks": [{
                "id": "b1", "kind": "paragraph", "text": "换路定则：电容电压不跃变。",
                "source_refs": [{"material": "m", "page_start": 1, "page_end": 1}], "figure": None,
            }],
        }]), encoding="utf-8")
        (d / "coverage_audit.json").write_text("[]", encoding="utf-8")
        (d / "lecture.html").write_text("<html></html>", encoding="utf-8")
        self._roots = service.ARTIFACT_ROOTS
        self._db = store.DB_PATH
        service.ARTIFACT_ROOTS = [self.root]
        store.DB_PATH = Path(self.tmp.name) / "test.sqlite3"

    def tearDown(self):
        service.ARTIFACT_ROOTS = self._roots
        store.DB_PATH = self._db
        self.tmp.cleanup()

    def test_plan_routes(self):
        self.assertEqual(agent.plan("复习计划")[0]["tool"], "make_review_plan")
        self.assertEqual(agent.plan("出卷")[0]["tool"], "generate_exam")
        self.assertEqual(agent.plan("解释这一页", page=1)[0]["tool"], "read_page")

    def test_search_and_read(self):
        r = agent.search_material(self.aid, "换路")
        self.assertTrue(r["ok"])
        self.assertEqual(r["citations"][0], 1)
        p = agent.read_page(self.aid, 1)
        self.assertTrue(p["ok"])

    def test_run_agent_citations(self):
        r = agent.run_agent("换路定则", artifact_id=self.aid)
        self.assertIn(1, r["citations"])
        self.assertTrue(r["trace"][0]["ok"])

    def test_plan_requires_confirmation_for_exam(self):
        meta = agent.plan_with_meta("出 12 题试卷", artifact_id=self.aid)
        self.assertTrue(meta["needs_confirmation"])
        self.assertTrue(any(s["tool"] == "generate_exam" for s in meta["steps"]))

    def test_workflow_does_not_run_without_confirm(self):
        r = agent.run_workflow("出 12 题试卷", artifact_id=self.aid, confirm=False)
        self.assertTrue(r["needs_confirmation"])

    def test_llm_planner_validates_tools(self):
        class Fake:
            def json(self, *a, **k):
                return {"goal": "x", "steps": [{"tool": "shell", "args": {}},
                                               {"tool": "get_artifact", "args": {"artifact_id": "agent_art"}}]}
        r = agent.plan_with_llm("看质量", artifact_id=self.aid, client=Fake())
        self.assertEqual(r["planner"], "llm")
        self.assertEqual([x["tool"] for x in r["steps"]], ["get_artifact"])

    def test_llm_planner_falls_back(self):
        class Bad:
            def json(self, *a, **k):
                raise RuntimeError("no")
        r = agent.plan_with_llm("复习", artifact_id=self.aid, client=Bad())
        self.assertEqual(r["planner"], "fallback")

    def test_agent_memory_saved(self):
        store.save_memory("复习电路", "成功：get_artifact:OK", "v2_circuit_full")
        rows = store.list_memories(5, "v2_circuit_full")
        self.assertTrue(any("get_artifact" in (r.get("content") or "") for r in rows))
        self.assertTrue(store.recall_memory("复习电路", "v2_circuit_full"))

    def test_interrupted_jobs_marked(self):
        store.create_job("stale_job", "lecture")
        self.assertGreaterEqual(store.mark_interrupted_jobs(), 1)
        self.assertEqual(store.get_job("stale_job")["status"], "failed")

    def test_job_history(self):
        store.create_job("agent_test_job", "agent")
        rows = store.list_jobs("agent", 5)
        self.assertEqual(rows[0]["id"], "agent_test_job")

    def test_workflow_uses_confirmed_steps(self):
        r = agent.run_workflow("x", artifact_id=self.aid, confirm=True,
                               steps=[{"tool": "get_artifact", "args": {"artifact_id": self.aid}}])
        self.assertEqual([x["tool"] for x in r["trace"]], ["get_artifact"])
        self.assertTrue(r["trace"][0]["ok"])

    def test_workflow_and_goal_store(self):
        w = store.save_workflow("复习流", [{"tool": "get_artifact", "args": {"artifact_id": self.aid}}])
        self.assertTrue(w["id"])
        self.assertEqual(store.list_workflows()[0]["name"], "复习流")
        g = store.save_goal("通过电路期末")
        self.assertEqual(store.list_goals()[0]["goal"], "通过电路期末")

    def test_goal_due_and_advance(self):
        g = store.save_goal("每日复习")
        self.assertEqual(store.due_goals()[0]["id"], g["id"])
        nxt = store.advance_goal(g["id"], 3)
        self.assertNotEqual(nxt["next_run"], g["next_run"])

    def test_auto_goal_due(self):
        g = store.save_goal("自动复习", auto=True, artifact_id=self.aid)
        self.assertEqual(store.due_auto_goals()[0]["id"], g["id"])
        store.save_goal("手动复习", auto=False)
        self.assertEqual(len(store.due_auto_goals()), 1)

    def test_workflow_versions_and_diff(self):
        a = store.save_workflow("版本流", [{"tool": "get_artifact"}])
        b = store.save_workflow("版本流", [{"tool": "read_page"}])
        self.assertEqual((a["version"], b["version"]), (1, 2))
        d = store.workflow_diff(b["id"], a["id"])
        self.assertIn("-    \"tool\": \"get_artifact\"", d["diff"])

    def test_parallel_read_steps(self):
        r = agent.run_workflow("并行", artifact_id=self.aid, confirm=True, steps=[
            {"tool": "get_artifact", "args": {"artifact_id": self.aid}},
            {"tool": "get_learning_state", "args": {}},
        ])
        self.assertTrue(all(x.get("parallel") for x in r["trace"]))
        self.assertTrue(all(x["ok"] for x in r["trace"]))

    def test_dag_dependency_order(self):
        r = agent.run_workflow("依赖", artifact_id=self.aid, confirm=True, steps=[
            {"id": "b", "tool": "search_material", "args": {"query": "换路"}, "depends_on": ["a"]},
            {"id": "a", "tool": "get_artifact", "args": {"artifact_id": self.aid}},
        ])
        self.assertEqual([x["tool"] for x in r["trace"]], ["get_artifact", "search_material"])

    def test_dag_levels_parallel_reads(self):
        r = agent.run_workflow("分层", artifact_id=self.aid, confirm=True, steps=[
            {"id": "a", "tool": "get_artifact", "args": {"artifact_id": self.aid}},
            {"id": "b", "tool": "search_material", "args": {"query": "换路"}, "depends_on": ["a"]},
            {"id": "c", "tool": "get_learning_state", "args": {}},
        ])
        parallel = [x for x in r["trace"] if x.get("parallel")]
        self.assertGreaterEqual(len(parallel), 2)
        self.assertEqual(r["trace"][-1]["tool"], "search_material")

    def test_read_page_repairs_to_search(self):
        r = agent.run_workflow("换路", artifact_id=self.aid, confirm=True, steps=[
            {"tool": "read_page", "args": {"artifact_id": self.aid, "page": 99}},
        ])
        self.assertTrue(r["trace"][0]["ok"])

    def test_auto_repair_executes_fallback(self):
        from unittest.mock import patch
        with patch.object(agent, "replan_remaining", return_value={
            "steps": [{"tool": "search_material", "args": {"artifact_id": self.aid, "query": "换路"}}],
            "diff": "diff",
        }):
            r = agent.run_workflow("换路", artifact_id=self.aid, confirm=True,
                                   auto_repair=True, steps=[{"tool": "get_artifact", "args": {"artifact_id": "missing"}}])
        self.assertTrue(r["ok"])
        self.assertTrue(r["repaired_ok"])
        self.assertIn("search_material", [t["tool"] for t in r["trace"]])

    def test_resume_skips_completed_steps(self):
        steps = [{"tool": "get_artifact", "args": {"artifact_id": self.aid},
                  "ok": True, "result": {"ok": True, "data": {}, "citations": []}},
                 {"tool": "make_review_plan", "args": {}}]
        r = agent.run_workflow("继续", artifact_id=self.aid, confirm=True, steps=steps, resume=True)
        self.assertTrue(r["trace"][0].get("skipped"))
        self.assertEqual(r["trace"][1]["tool"], "make_review_plan")

    def test_replan_falls_back_to_search(self):
        class Bad:
            def json(self, *a, **k):
                raise RuntimeError("no")
        r = agent.replan_remaining("换路", artifact_id=self.aid, steps=[
            {"tool": "read_page", "args": {"artifact_id": self.aid, "page": 99}, "ok": False,
             "result": {"ok": False, "error": "bad page"}},
        ], failed_tool="read_page", error="bad page", client=Bad())
        self.assertTrue(r["ok"])
        self.assertEqual(r["steps"][0]["tool"], "search_material")

    def test_tool_schema_has_args(self):
        self.assertIn("query", agent.TOOLS["search_material"]["args"])
        self.assertIn("page", agent.TOOLS["read_page"]["args"])

    def test_review_plan(self):
        r = agent.make_review_plan(3)
        self.assertEqual(len(r["data"]["days"]), 3)


if __name__ == "__main__":
    unittest.main()
