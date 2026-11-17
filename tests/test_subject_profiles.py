import unittest

from tfv2.quality.subject_profiles import detect_subject, capability_matrix


class SubjectProfileTests(unittest.TestCase):
    def test_detects_required_subjects(self) -> None:
        cases = {
            "电路分析": "circuits", "有机化学": "chemistry", "大学物理": "physics",
            "高等数学": "math", "刑法学": "law", "解剖学": "medical",
            "宏观经济学": "economics", "数据结构": "cs",
        }
        for text, want in cases.items():
            self.assertEqual(detect_subject(course=text).id, want, text)

    def test_unknown_falls_back_general(self) -> None:
        self.assertEqual(detect_subject(course="某不存在的课程").id, "general")

    def test_capability_matrix_has_universal_contract(self) -> None:
        class H: course = "有机化学"; title = "有机"
        class S:
            header = H()
            sections = []
        m = capability_matrix(S())
        self.assertEqual(m["profile"], "chemistry")
        self.assertEqual(m["universal_modules"][:2], ["objectives", "key_terms"])
        self.assertIn("formula", m["universal_gates"])


if __name__ == "__main__":
    unittest.main()


class CapabilityGateTests(unittest.TestCase):
    def test_every_profile_uses_same_contract(self) -> None:
        from tfv2.quality.subject_profiles import PROFILES, capability_gate
        for p in PROFILES:
            matrix = {
                "profile": p.id, "sections": 2,
                "modules": {"objectives": 2, "key_terms": 2, "self_test": 2, "source_index": 2},
                "formula_assets": 0, "formula_fallback": 0,
                "figures": 1, "representations": {
                    "formula": [], "figures": [], "structures": list(p.structures),
                    "code": p.code, "tables": p.tables,
                },
            }
            gate = capability_gate(matrix)
            self.assertTrue(gate["passed"], (p.id, gate))
            # No subject gets a different required-module contract.
            self.assertEqual(set(matrix["modules"]), {"objectives", "key_terms", "self_test", "source_index"})
