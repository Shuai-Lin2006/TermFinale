import unittest
from tfv2.domain.lecture import LectureSpec, LectureHeader, LectureSummary, LectureSection, LectureBlock, BlockKind, SourceRef, LectureClosing, LectureFooter
from tfv2.quality.review import review_and_revise

def spec_with_blocks(blocks):
    ref=SourceRef(material="m.pdf",page_start=1,page_end=1)
    return LectureSpec(header=LectureHeader(title="t",course="c"), summary=LectureSummary(overview="o"), sections=[LectureSection(id="s",title="s",blocks=blocks,source_refs=[ref])], closing=LectureClosing(persona="p",text="end"), footer=LectureFooter(coverage_percent=100,material_label="m.pdf"), page_count=1, coverage_percent=100)

class ReviewTests(unittest.TestCase):
    def test_removes_same_section_duplicate_long_paragraph(self):
        ref=SourceRef(material="m.pdf",page_start=1,page_end=1)
        text="这是重复的长段落" * 10
        s=spec_with_blocks([LectureBlock(id="a",kind=BlockKind.PARAGRAPH,text=text,source_refs=[ref]),LectureBlock(id="b",kind=BlockKind.PARAGRAPH,text=text,source_refs=[ref])])
        report, applied=review_and_revise(s)
        self.assertEqual(len(s.sections[0].blocks),1)
        self.assertEqual(len(applied),1)
        self.assertTrue(report["passed"])

    def test_short_section_warns(self):
        ref=SourceRef(material="m.pdf",page_start=1,page_end=1)
        s=spec_with_blocks([LectureBlock(id="a",kind=BlockKind.PARAGRAPH,text="短",source_refs=[ref])])
        report,_=review_and_revise(s)
        self.assertTrue(any(x["code"]=="section.short" for x in report["issues"]))
