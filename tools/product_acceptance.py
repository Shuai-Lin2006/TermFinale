"""v3 学习台验收：首页/讲义库/质量报告/阅读器/笔记/新建/主题/移动端。

用法：
  PYTHONPATH=. .venv/bin/python tools/product_acceptance.py \
    --url http://127.0.0.1:8907/
"""
from __future__ import annotations

import argparse
import json
import sys


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8907/")
    ap.add_argument("--channel", default="msedge")
    ap.add_argument("--artifact", default="v2_circuit_full")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    out: dict = {}
    errors: list[str] = []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True, channel=args.channel)
        except Exception:
            browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(args.url, wait_until="networkidle")
        page.wait_for_timeout(400)
        out["home_title"] = page.title()
        out["home_hero"] = page.locator(".cc-title").inner_text() if page.locator(".cc-title").count() else (page.locator("#view h1").first.inner_text() if page.locator("#view h1").count() else "")
        out["nav_items"] = page.locator("[data-nav]").count()
        out["nav_svg"] = page.locator(".nav-ico").count()
        out["course_cards"] = page.locator(".course-card").count()
        out["home_orbit_nodes"] = page.locator(".orbit-node").count()
        out["profile"] = page.locator("#sidebarUser").count() == 1 and page.locator("#userName").inner_text().strip() != ""
        page.locator("#aiFab").click()
        page.wait_for_timeout(200)
        out["ai_drawer"] = page.locator("#aiDrawer").is_visible() and page.locator("#aiMessages").count() == 1
        page.locator("#aiClose").click()

        page.goto(args.url + "#/library", wait_until="networkidle")
        page.wait_for_timeout(300)
        out["library_cards"] = page.locator(".course-card").count()
        page.locator(".course-card").first.click()
        page.wait_for_timeout(400)
        out["course_page"] = page.locator(".course-hero").count() == 1

        page.goto(args.url + f"#/artifact/{args.artifact}", wait_until="networkidle")
        page.wait_for_timeout(300)
        body = page.inner_text("#view")
        out["artifact_quality"] = all(k in body for k in ("结构 Gate", "语义覆盖", "可读"))
        out["artifact_sections"] = page.locator("table tbody tr").count()
        out["rewrite_form"] = page.locator("#rewriteInstruction").count() == 1 and page.locator("#rewriteBtn").count() == 1
        out["word_link"] = page.locator('a[href$="lecture.docx"]').count() >= 1
        if out["word_link"]:
            r = page.request.get(args.url.rstrip("/") + f"/artifact/{args.artifact}/lecture.docx")
            out["word_ok"] = r.ok and r.headers.get("content-type", "").startswith("application/vnd.openxmlformats")
        else:
            out["word_ok"] = False

        page.goto(args.url + f"#/read/{args.artifact}", wait_until="networkidle")
        page.wait_for_timeout(1200)
        frames = page.frames
        out["reader_frames"] = len(frames)
        out["reader_katex"] = 0
        out["reader_math_ready"] = False
        for f in frames:
            if "/artifact/" in f.url:
                out["reader_math_ready"] = f.evaluate("typeof window.renderMathInElement") == "function"
                out["reader_katex"] = f.locator(".katex").count()

        page.goto(args.url + "#/notes", wait_until="networkidle")
        page.wait_for_timeout(300)
        out["notes_page"] = "笔记" in page.inner_text("#view")

        page.goto(args.url + "#/exam", wait_until="networkidle")
        page.wait_for_timeout(300)
        out["exam_form"] = page.locator("#examForm").count() == 1 and page.locator('#examForm select[name="mode"] option').count() == 4 and page.locator('#examForm input[name="references"]').get_attribute("multiple") is not None
        out["exam_gen_lang"] = page.locator('#examForm select[name="gen_lang"]').count() == 1

        page.goto(args.url + "#/workbench", wait_until="networkidle")
        page.wait_for_timeout(400)
        out["workbench"] = page.locator("#wbRun").count() == 1 and page.locator(".tab").count() >= 5

        page.goto(args.url + "#/settings", wait_until="networkidle")
        page.wait_for_timeout(300)
        settings_text = page.inner_text("#view")
        out["settings_status"] = "迁移状态" not in settings_text and "备份" in settings_text and "立即备份" in settings_text

        page.goto(args.url + "#/new", wait_until="networkidle")
        page.wait_for_timeout(300)
        out["new_form"] = page.locator("#newForm").count() == 1 and page.locator("input[name=file]").count() == 1
        out["new_fields"] = page.locator('#newForm textarea[name="key_points"]').count() == 1 and page.locator('#newForm textarea[name="excluded"]').count() == 1
        out["gen_lang"] = page.locator('#newForm select[name="gen_lang"]').count() == 1 and page.locator('#multiForm select[name="gen_lang"]').count() == 1
        out["illustration_toggle"] = page.locator('#newForm input[name="illustrations"]').count() == 1
        upload = page.locator('#newForm input[name="file"]')
        out["multi_form"] = upload.count() == 1 and upload.get_attribute("multiple") is not None and page.locator('#newForm input[name="weights"]').count() == 1

        page.goto(args.url, wait_until="networkidle")
        before = page.evaluate("document.documentElement.dataset.theme")
        page.click("#themeBtn")
        page.wait_for_timeout(300)
        after = page.evaluate("document.documentElement.dataset.theme")
        out["theme_toggle"] = before != after

        page.set_viewport_size({"width": 390, "height": 800})
        page.goto(args.url, wait_until="networkidle")
        page.evaluate("localStorage.setItem('tf-ui-lang','zh')")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(400)
        out["mobile_menu_visible"] = page.is_visible("#menuBtn")
        page.click("#menuBtn")
        out["mobile_sidebar_open"] = page.eval_on_selector(".sidebar", "el => el.classList.contains('open')")
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(args.url + "#/settings", wait_until="networkidle")
        page.wait_for_timeout(300)
        out["settings_mobile_no_overflow"] = page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 2")
        page.set_viewport_size({"width": 1440, "height": 1000})
        out["page_errors"] = errors
        browser.close()

    print(json.dumps(out, ensure_ascii=False, indent=2))
    ok = (
        out.get("home_title")
        and out.get("nav_items", 0) >= 6
        and out.get("nav_svg", 0) >= 7
        and out.get("profile")
        and out.get("ai_drawer")
        and out.get("new_fields")
        and out.get("multi_form")
        and out.get("exam_form")
        and out.get("exam_gen_lang")
        and out.get("gen_lang")
        and out.get("illustration_toggle")
        and out.get("library_cards", 0) >= 1
        and out.get("course_page")
        and out.get("word_link")
        and out.get("word_ok")
        and out.get("rewrite_form")
        and out.get("artifact_quality")
        and out.get("artifact_sections", 0) >= 1
        and out.get("reader_math_ready")
        and out.get("reader_katex", 0) > 0
        and out.get("notes_page")
        and out.get("workbench")
        and out.get("settings_status")
        and out.get("new_form")
        and out.get("theme_toggle")
        and out.get("mobile_menu_visible")
        and out.get("mobile_sidebar_open")
        and out.get("settings_mobile_no_overflow")
        and not errors
    )
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
