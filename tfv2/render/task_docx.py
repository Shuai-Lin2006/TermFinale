"""把提取/试卷/导图/分析结果导出为原生 .docx。"""
from __future__ import annotations

import base64
import io
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt


def _add(doc, text: str, *, bold: bool = False, size: float | None = None) -> None:
    p = doc.add_paragraph()
    r = p.add_run(str(text))
    r.bold = bold
    if size:
        r.font.size = Pt(size)


def write_task_docx(result: dict, out_path: str | Path) -> Path:
    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    _add(doc, result.get("title") or "TermFinale 生成物", bold=True, size=18)
    _add(doc, f"状态：{result.get('status')} ｜ 页码覆盖：{len((result.get('coverage') or {}).get('pages_cited') or [])}/"
              f"{len((result.get('coverage') or {}).get('pages') or [])}", size=9)
    content = result.get("content") or {}
    kind = result.get("kind")
    if kind in ("extract_points", "extract_nouns"):
        for i, item in enumerate(content.get("items") or [], start=1):
            if kind == "extract_points":
                _add(doc, f"{i}. {item.get('point')}（第 {item.get('page')} 页）", bold=True)
                _add(doc, item.get("detail") or "")
            else:
                _add(doc, f"{i}. {item.get('term')}（第 {item.get('page')} 页）", bold=True)
                _add(doc, f"定义：{item.get('definition')}")
                if item.get("confused_with"):
                    _add(doc, f"易混：{item.get('confused_with')}")
    elif kind in ("extract_questions", "paper"):
        for i, q in enumerate(content.get("questions") or content.get("items") or [], start=1):
            _add(doc, f"{i}. {q.get('stem')}（{q.get('qtype')}，第 {q.get('source_page')} 页）", bold=True)
            for j, opt in enumerate(q.get("options") or []):
                _add(doc, f"{chr(65+j)}. {opt}")
            _add(doc, f"答案：{q.get('answer_text') or q.get('answer')}")
            _add(doc, f"解析：{q.get('analysis') or ''}")
    elif kind == "exam":
        _add(doc, f"总分：{content.get('total_score')} 分 ｜ 科目：{content.get('subject')} ｜ 难度：{content.get('difficulty')}/5", bold=True)
        n = 0
        for sec in content.get("sections") or []:
            _add(doc, sec.get("name") or "试题", bold=True, size=14)
            for q in sec.get("questions") or []:
                n += 1
                _add(doc, f"{n}. {q.get('stem')}（{q.get('score')} 分，第 {q.get('source_page')} 页）", bold=True)
                data = q.get("figure_data") or ""
                if isinstance(data, str) and data.startswith("data:image/"):
                    try:
                        raw = base64.b64decode(data.split(",", 1)[1])
                        doc.add_picture(io.BytesIO(raw), width=Inches(4.8))
                    except Exception:
                        pass
                for j, opt in enumerate(q.get("options") or []):
                    _add(doc, f"{chr(65+j)}. {opt}")
                _add(doc, f"参考答案：{q.get('answer_text') or q.get('answer')}")
                _add(doc, f"解析：{q.get('analysis') or ''}")
    elif kind == "mindmap":
        for n in content.get("nodes") or []:
            prefix = "  " * min(4, len(str(n.get("parent") or "")) and 1)
            _add(doc, f"{prefix}{n.get('label')}（第 {n.get('page')}–{n.get('page_end') or n.get('page')} 页）")
    elif kind == "analysis":
        for key, label in [("one_line", "一句话主线"), ("concepts", "概念层级"), ("causal_chain", "因果链"),
                           ("exam_map", "考点映射"), ("confusions", "易混对比"), ("order", "学习顺序")]:
            val = content.get(key)
            if isinstance(val, list):
                _add(doc, f"{label}：", bold=True)
                for x in val:
                    _add(doc, f"· {x}")
            elif val:
                _add(doc, f"{label}：{val}", bold=True)
    _add(doc, "本结果由 TermFinale 智能体生成，仅供复习参考；具体请以实际资料为准，本资料不承担由此产生的法律责任。", size=8)
    doc.save(str(target))
    return target
