"""阅读器验收：搜索/编辑/导出/图/目录/AI 面板（Playwright）。

用法：
  PYTHONPATH=. .venv/bin/python tools/reader_acceptance.py \
    --url http://127.0.0.1:8906/docs/evidence/v2_circuit_full/lecture.html

需要本机有 Edge/Chrome/Chromium 之一；默认先试 msedge，再试 chromium。
"""
from __future__ import annotations

import argparse
import json
import sys


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--channel", default="msedge")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    out: dict = {}
    with sync_playwright() as p:
        browser = None
        errors: list[str] = []
        try:
            browser = p.chromium.launch(headless=True, channel=args.channel)
        except Exception:
            browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: d.accept())
        page.goto(args.url, wait_until="networkidle")

        out["title"] = page.title()
        out["sections"] = page.locator("section.chapter").count()
        out["figures"] = page.locator("figure").count()
        out["figcaptions"] = page.locator("figcaption").count()
        imgs = page.eval_on_selector_all(
            "figure img", "els => els.map(e => [e.getAttribute('src'), e.naturalWidth])"
        )
        out["images_ok"] = all(w > 0 for _, w in imgs)
        out["image_count"] = len(imgs)

        toc_links = page.locator('.toc a, a[href^="#sec-"], a[href^="#"]')
        if toc_links.count():
            toc_links.first.click()
            page.wait_for_timeout(200)
        out["toc_hash"] = page.evaluate("location.hash")

        page.click("#tfSearchBtn")
        first_title = page.locator("section.chapter h2").first.inner_text() if page.locator("section.chapter h2").count() else "第"
        query = first_title.strip()[:2] or "第"
        page.fill("#tfSearchInput", query)
        page.press("#tfSearchInput", "Enter")
        page.wait_for_timeout(400)
        out["search_count"] = page.inner_text("#tfSearchCount")
        out["search_marks"] = page.locator("mark.tf-hit").count()

        page.click("#tfEditBtn")
        out["editing_on"] = page.eval_on_selector(".lecture", "el => el.contentEditable")
        page.click("#tfEditBtn")
        out["editing_off"] = page.eval_on_selector(".lecture", "el => el.contentEditable")

        page.click("#tfExportBtn")
        with page.expect_download() as dl:
            page.click("#tfWordBtn")
        word = dl.value
        word_text = open(word.path(), encoding="utf-8", errors="replace").read()
        out["word_file"] = word.suggested_filename
        out["word_bytes"] = len(word_text.encode("utf-8"))
        out["word_data_images"] = word_text.count("data:image/")
        out["word_mathml"] = word_text.count("<math")
        out["word_relative_images"] = word_text.count('src="assets/')

        page.click("#tfExportBtn")
        with page.expect_download() as dl2:
            page.click("#tfHtmlBtn")
        out["html_file"] = dl2.value.suggested_filename

        page.click("#tfAiBtn")
        page.wait_for_timeout(200)
        out["ai_panel_visible"] = page.is_visible("#tfAiPanel")
        out["page_errors"] = errors
        browser.close()

    print(json.dumps(out, ensure_ascii=False, indent=2))
    ok = (
        out.get("sections", 0) >= 1
        and out.get("figures", 0) >= 6
        and out.get("figcaptions", 0) == out.get("figures", -1)
        and out.get("images_ok")
        and out.get("search_marks", 0) > 0
        and out.get("editing_on") == "true"
        and out.get("editing_off") == "false"
        and out.get("word_file", "").endswith(".doc")
        and out.get("word_data_images", 0) > 0
        and out.get("word_relative_images", 1) == 0
        and out.get("html_file", "").endswith(".html")
        and out.get("ai_panel_visible")
        and not out.get("page_errors")
    )
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
