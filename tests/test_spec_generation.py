import unittest
from core.quality.constraints import TaskConstraints, validate_output

SOURCE = "\n\n".join(f"【《资料》第 {i} 页】\n第{i}页知识点内容" for i in range(1, 11))

class SpecGenerationTest(unittest.TestCase):
    def test_guide_key_requires_mode_declaration(self):
        c = TaskConstraints(task="guide", guide_mode="key")
        r = validate_output("## 第一章\n\n内容", c)
        self.assertFalse(r.ok)
        self.assertTrue(any("精简模式" in x for x in r.issues))

    def test_guide_coverage_hard_for_real_docs(self):
        c = TaskConstraints(task="guide")
        text = "## 第一章\n\n第 1 页知识点（P.1）"
        r = validate_output(text, c, source_text=SOURCE)
        self.assertFalse(r.ok)
        self.assertTrue(any("页码覆盖不足" in x for x in r.issues))

    def test_analysis_requires_structure_and_pages(self):
        c = TaskConstraints(task="analysis")
        r = validate_output("## 分析\n\n随便写点。", c)
        self.assertFalse(r.ok)

    def test_exam_original_requires_provenance(self):
        c = TaskConstraints(task="exam", exam_mode="original", answer_mode="forbidden")
        r = validate_output("## 一、选择题\n\n1. 题干（2分）\nA. 甲 B. 乙", c)
        self.assertFalse(r.ok)
        self.assertTrue(any("改编自" in x for x in r.issues))

    def test_nouns_require_definition_and_page(self):
        c = TaskConstraints(task="extract", extract_type="nouns")
        r = validate_output("- 环烃\n- 脂环烃\n- 芳香烃", c, source_text=SOURCE)
        self.assertFalse(r.ok)
        self.assertTrue(any("定义" in x or "出处" in x for x in r.issues))

if __name__ == "__main__": unittest.main()
