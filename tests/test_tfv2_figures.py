import tempfile
import unittest
from pathlib import Path

from unittest.mock import patch

from tfv2.product import service
from tfv2.render import diagram, figure_compiler, figure_router


class FigureRouterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_series_circuit_is_deterministic(self):
        out = self.root / "series.png"
        res = diagram.render_spec({"kind": "circuit", "elements": [
            {"type": "battery", "label": "U", "value": "12V"},
            {"type": "resistor", "label": "R", "value": "2Ω"},
            {"type": "capacitor", "label": "C", "value": "1μF"},
        ]}, out)
        self.assertEqual(res["layout"], "series")
        self.assertTrue(out.is_file() and out.stat().st_size > 1000)

    def test_chemistry_smiles(self):
        out = self.root / "chem.png"
        res = figure_router.render({"kind": "chem", "smiles": "CCO"}, subject="化学", out_path=out)
        self.assertEqual(res["layout"], "chem")
        self.assertTrue(out.is_file() and out.stat().st_size > 1000)

    def test_flow_nodes_edges(self):
        out = self.root / "flow.png"
        res = figure_router.render({"kind": "flow", "nodes": [
            {"id": "a", "label": "输入"}, {"id": "b", "label": "处理"}, {"id": "c", "label": "输出"},
        ], "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}]}, subject="计算机", out_path=out)
        self.assertEqual(res["layout"], "flow")
        self.assertTrue(out.is_file())

    def test_compiler_chemistry(self):
        out = self.root / "compiler_chem.png"
        res = figure_compiler.compile_figure({"kind": "chem", "smiles": "CCO"}, subject="化学", out_path=out)
        self.assertEqual(res["domain"], "chemistry")
        self.assertTrue(out.is_file())

    def test_compiler_chart(self):
        out = self.root / "chart.png"
        res = figure_compiler.compile_figure({"kind": "bar", "labels": ["A", "B"], "values": [1, 2]},
                                             subject="经济", out_path=out)
        self.assertEqual(res["domain"], "chart")
        self.assertTrue(out.is_file())

    def test_compiler_parallel_and_symbolic(self):
        p = self.root / "parallel.png"
        r = figure_compiler.compile_figure({"kind": "circuit", "topology": "parallel", "source_value": "12V",
                                            "branches": [{"type": "resistor", "label": "R", "value": "2Ω"}]},
                                           subject="电路", out_path=p)
        self.assertEqual(r["domain"], "circuit")
        m = self.root / "sym.png"
        r2 = figure_compiler.compile_figure({"kind": "math", "expression": "x**2"}, subject="高等数学", out_path=m)
        self.assertEqual(r2["engine"], "sympy-matplotlib")
        rx = self.root / "reaction.png"
        r3 = figure_compiler.compile_figure({"kind": "reaction", "reaction": "CCO>>CC=O"}, subject="化学", out_path=rx)
        self.assertEqual(r3["engine"], "rdkit-reaction")

    def test_compiler_table_timeline_map_generic(self):
        t = self.root / "table.png"
        self.assertEqual(figure_compiler.compile_figure({"kind": "table", "headers": ["A"], "rows": [["1"]]},
                                                        subject="医学", out_path=t)["domain"], "table")
        tl = self.root / "timeline.png"
        self.assertEqual(figure_compiler.compile_figure({"kind": "timeline", "events": [{"date": "1900", "label": "X"}]},
                                                        subject="历史", out_path=tl)["domain"], "timeline")
        m = self.root / "map.png"
        self.assertEqual(figure_compiler.compile_figure({"kind": "map", "points": [{"x": 0, "y": 0, "label": "A"}]},
                                                        subject="地理", out_path=m)["domain"], "map")

    def test_compiler_netlist_and_reaction_sequence(self):
        n = self.root / "netlist.png"
        r = figure_compiler.compile_figure({"kind": "circuit", "components": [
            {"type": "battery", "label": "U", "value": "12V"},
            {"type": "resistor", "label": "R1", "value": "2Ω"},
            {"type": "resistor", "label": "R2", "value": "3Ω"},
            {"type": "capacitor", "label": "C", "value": "1μF"},
        ]}, subject="电路", out_path=n)
        self.assertEqual(r["domain"], "circuit")
        rx = self.root / "rxn_seq.png"
        r2 = figure_compiler.compile_figure({"kind": "reaction-sequence", "steps": ["CCO>>CC=O", "CC=O>>CC(=O)O"]},
                                           subject="化学", out_path=rx)
        self.assertEqual(r2["engine"], "rdkit-reaction-sequence")

    def test_compiler_graph_netlist(self):
        out = self.root / "graph.png"
        r = figure_compiler.compile_figure({"kind": "circuit", "nodes": [
            {"id": "u", "type": "battery", "x": 80, "y": 210, "label": "U", "value": "12V"},
            {"id": "r", "type": "resistor", "x": 300, "y": 80, "label": "R", "value": "2Ω"},
            {"id": "c", "type": "capacitor", "x": 500, "y": 210, "label": "C", "value": "1μF"},
        ], "edges": [["u", "r"], ["r", "c"], ["c", "u"]]}, subject="电路", out_path=out)
        self.assertEqual(r["domain"], "circuit")

    def test_compiler_labels_contract(self):
        out = self.root / "labels.png"
        r = figure_compiler.compile_figure({"kind": "timeline", "events": [{"date": "1900", "label": "事件"}]},
                                           subject="历史", out_path=out)
        self.assertIn("1900", r["labels"])
        self.assertIn("事件", r["labels"])

    def test_compiler_3d_scene(self):
        out = self.root / "3d.png"
        r = figure_compiler.compile_figure({"kind": "3d", "objects": [
            {"type": "box", "x": 0, "y": 0, "z": 0, "w": 1, "h": 1, "d": 1, "label": "m"},
            {"type": "arrow", "x": 0, "y": 0, "z": 0, "dx": 1, "dy": 0, "dz": 0, "label": "F"},
        ]}, subject="物理", out_path=out)
        self.assertEqual(r["engine"], "matplotlib-3d")
        self.assertTrue(out.is_file())

    def test_netlist_rejects_duplicate_edge(self):
        out = self.root / "dup.png"
        r = figure_compiler.compile_figure({"kind": "circuit", "nodes": [
            {"id": "u", "type": "battery", "x": 0, "y": 0},
            {"id": "r", "type": "resistor", "x": 100, "y": 0}],
            "edges": [["u", "r"], ["r", "u"], ["u", "r"]]}, subject="电路", out_path=out)
        self.assertIsNone(r)

    def test_netlist_rejects_floating_component(self):
        out = self.root / "floating.png"
        r = figure_compiler.compile_figure({"kind": "circuit", "nodes": [
            {"id": "r", "type": "resistor", "x": 100, "y": 100}], "edges": []}, subject="电路", out_path=out)
        self.assertIsNone(r)

    def test_source_auto_match_artifact_page(self):
        out = self.root / "auto_source.png"
        with patch.object(service, "ARTIFACT_ROOTS", [Path("docs/evidence")]):
            r = figure_compiler.compile_figure({"kind": "source", "artifact_id": "v2_circuit_full", "page": 6},
                                               subject="医学", out_path=out)
        self.assertEqual(r["engine"], "source-only")
        self.assertTrue(out.is_file())

    def test_3d_rotated_cylinder_plane(self):
        out = self.root / "3d2.png"
        r = figure_compiler.compile_figure({"kind": "3d", "objects": [
            {"type": "ground", "w": 5},
            {"type": "box", "x": 0, "y": 0, "z": 0, "rotation": 30, "label": "m"},
            {"type": "cylinder", "x": 1, "y": 0, "z": 0, "r": 0.3, "h": 1.2, "label": "C"},
            {"type": "plane", "x": -1, "y": -1, "z": 0, "w": 1, "d": 1},
        ]}, subject="物理", out_path=out)
        self.assertEqual(r["engine"], "matplotlib-3d")

    def test_source_crop_trims_white_border(self):
        src = self.root / "border.png"
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (300, 200), "white"); d = ImageDraw.Draw(im)
        d.rectangle((100, 60, 200, 140), fill="black"); im.save(src)
        out = self.root / "border_out.png"
        r = figure_compiler.compile_figure({"kind": "source", "path": str(src)}, subject="医学", out_path=out)
        self.assertLess(r["width"], 300)
        self.assertLess(r["height"], 200)
        self.assertGreater(r["width"], 100)
        self.assertGreater(r["height"], 80)

    def test_physics3d_kinematics(self):
        out = self.root / "kinematics.png"
        r = figure_compiler.compile_figure({"kind": "physics3d", "position": [0, 0, 1],
                                            "velocity": [1, 0, 4], "duration": 1.2}, subject="物理", out_path=out)
        self.assertEqual(r["engine"], "physics3d-euler")
        self.assertTrue(out.is_file())

    def test_spice_netlist(self):
        out = self.root / "spice.png"
        r = figure_compiler.compile_figure({"kind": "spice", "netlist": "V1 1 0 12\nR1 1 2 2\nC1 2 0 1e-6"},
                                           subject="电路", out_path=out)
        self.assertEqual(r["engine"], "lcapy-spice")

    def test_mujoco_rigid_body(self):
        out = self.root / "mujoco.png"
        r = figure_compiler.compile_figure({"kind": "mujoco", "position": [0, 0, 1.2], "duration": 0.3},
                                           subject="物理", out_path=out)
        self.assertEqual(r["engine"], "mujoco")

    def test_atlas_and_geojson(self):
        # 独立测试夹具，不依赖用户 data/atlas（用户清空数据后测试仍应可跑）。
        import json
        from PIL import Image
        atlas_root = self.root / "atlas"
        atlas_root.mkdir()
        Image.new("RGB", (1600, 1000), "white").save(atlas_root / "p17.png")
        (atlas_root / "index.json").write_text(json.dumps([
            {"id": "p17", "file": "p17.png", "source_pages": [17], "source": "test fixture"}
        ]), encoding="utf-8")
        a = self.root / "atlas.png"
        r = figure_compiler.compile_figure({"kind": "atlas", "page": 17, "root": str(atlas_root)},
                                            subject="医学", out_path=a)
        self.assertEqual(r["engine"], "atlas-source-only")
        geo = self.root / "x.geojson"
        geo.write_text('{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,0]]]}', encoding="utf-8")
        g = self.root / "geo.png"
        r2 = figure_compiler.compile_figure({"kind": "geojson", "path": str(geo)}, subject="地理", out_path=g)
        self.assertEqual(r2["engine"], "geojson-matplotlib")

    def test_mujoco_multi(self):
        out = self.root / "mujoco_multi.png"
        r = figure_compiler.compile_figure({"kind": "mujoco", "bodies": [
            {"name": "a", "position": [0, 0, 1]}, {"name": "b", "position": [1, 0, 1.5]}],
            "duration": 0.2}, subject="物理", out_path=out)
        self.assertEqual(r["engine"], "mujoco-multi")

    def test_compiler_source_only(self):
        src = self.root / "src.png"
        from PIL import Image
        Image.new("RGB", (200, 100), "white").save(src)
        out = self.root / "source.png"
        r = figure_compiler.compile_figure({"kind": "source", "path": str(src)}, subject="医学", out_path=out)
        self.assertEqual(r["engine"], "source-only")

    def test_compiler_medical_returns_none(self):
        out = self.root / "medical.png"
        res = figure_compiler.compile_figure({"kind": "circuit"}, subject="医学", out_path=out)
        self.assertIsNone(res)

    def test_math_points(self):
        out = self.root / "math.png"
        res = figure_router.render({"kind": "math", "points": [[0, 0], [1, 1], [2, 4]]},
                                   subject="高等数学", out_path=out)
        self.assertEqual(res["layout"], "math")
        self.assertTrue(out.is_file())


if __name__ == "__main__":
    unittest.main()
