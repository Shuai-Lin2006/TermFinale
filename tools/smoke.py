"""离线冒烟测试：不联网、不调用任何 AI API。

用法：python tools/smoke.py
覆盖：模块导入 → 数据库 → 解析（含图形） → 渲染 → 权重模型 → 单元测试。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TERMFINALE_HOME", str(ROOT / "_backup" / "home_test"))
os.environ.setdefault("TERMFINALE_DISABLE_VISION", "1")

FAILED: list[str] = []


def check(name: str, fn) -> None:
    try:
        detail = fn()
        print(f"✅ {name}" + (f" — {detail}" if detail else ""))
    except Exception as exc:  # noqa: BLE001
        FAILED.append(name)
        print(f"❌ {name}: {type(exc).__name__}: {exc}")


def step_imports() -> str:
    import main  # noqa: F401
    import launcher  # noqa: F401
    from core import config, maintenance, paths  # noqa: F401
    from core.generate import exam_builder, outline  # noqa: F401
    from core.parsing import figures  # noqa: F401
    from core.quality import qa  # noqa: F401
    from services import guide_service, review_service  # noqa: F401

    return "全部模块导入成功"


def step_db() -> str:
    from core.database import Course, get_db_session

    db = get_db_session()
    try:
        count = db.query(Course).count()
    finally:
        db.close()
    return f"{count} 门课程"


def step_parser() -> str:
    pdfs = sorted(Path.home().joinpath("Desktop").glob("*.pdf"))
    if not pdfs:
        return "跳过（桌面没有 PDF 样本）"
    from core.parser import extract_text_from_file

    pages = extract_text_from_file(str(pdfs[0]))
    tags = sum(page.count("[[[IMAGE:") for page in pages)
    assert pages, "解析结果为空"
    return f"{pdfs[0].name}: {len(pages)} 页 / {tags} 张图"


def step_exporter() -> str:
    from core.exporter import export_to_html

    out = ROOT / "_backup" / "smoke.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    export_to_html("## 核心考点：冒烟测试\n\n公式 $x=1$，名词 [[力|相互作用]]。", str(out), lang="中文")
    html = out.read_text(encoding="utf-8")
    assert "第 1 章：冒烟测试" in html
    assert "class=\"keyword\"" in html
    return f"{out.stat().st_size // 1024} KB"


def step_weights() -> str:
    from models.user_profile import CourseInfo

    ev = CourseInfo("冒烟", "普通二本", "环境工程", True, 3.0, 7, 80, 3).evaluate()
    assert 0 <= ev["final_priority_weight"] <= 100
    assert ev["advice"]
    return f"权重 {ev['final_priority_weight']} / {ev['status']}"


def step_units() -> str:
    env = {k: v for k, v in os.environ.items() if k != "TERMFINALE_HOME"}
    done = []
    for module in ("tests.test_weights", "tests.test_maintenance", "tests.test_config"):
        result = subprocess.run([sys.executable, "-m", module], cwd=ROOT, env=env,
                                capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"{module} 失败：{result.stderr[-300:]}")
        done.append(module.rsplit(".", 1)[-1])
    return "、".join(done)


def main() -> int:
    print("=" * 60)
    print("TermFinale 离线冒烟测试")
    print("=" * 60)
    check("模块导入", step_imports)
    check("数据库", step_db)
    check("文档解析", step_parser)
    check("HTML 渲染", step_exporter)
    check("权重模型", step_weights)
    check("单元测试", step_units)
    print("=" * 60)
    if FAILED:
        print(f"❌ 失败 {len(FAILED)} 项：{'、'.join(FAILED)}")
        return 1
    print("✅ 全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
