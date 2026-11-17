"""把 v3 每个页面/主要按钮/中英文/深浅色/移动端扫一遍，输出 JSON。

用法：
  PYTHONPATH=. .venv/bin/python tools/ui_sweep.py --url http://127.0.0.1:8907/
"""
from __future__ import annotations

import argparse
import json
import sys

from playwright.sync_api import sync_playwright


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8907/")
    ap.add_argument("--out", default="docs/evidence/ui_sweep.json")
    args = ap.parse_args()
    out: dict = {"routes": {}, "buttons": {}, "lang": {}, "theme": {}, "mobile": {}, "errors": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="msedge")
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda e: out["errors"].append(str(e)))
        page.goto(args.url, wait_until="networkidle")
        page.evaluate("localStorage.setItem('tf-ui-lang','zh')")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(400)

        for name, route in [
            ("home", "#/"), ("courses", "#/library"), ("workbench", "#/workbench"),
            ("practice", "#/practice"), ("review", "#/review"), ("notes", "#/notes"),
            ("settings", "#/settings"), ("new", "#/new"), ("exam", "#/exam"),
        ]:
            page.goto(args.url + route, wait_until="networkidle")
            page.wait_for_timeout(250)
            out["routes"][name] = {
                "title": page.locator("#view h1, #view h2").first.inner_text() if page.locator("#view h1, #view h2").count() else "",
                "text": page.inner_text("#view")[:120],
            }

        # settings: profile save, theme, language
        page.goto(args.url + "#/settings", wait_until="networkidle")
        page.wait_for_timeout(300)
        page.fill("#profileName", "测试同学")
        page.click("text=保存称呼")
        page.wait_for_timeout(400)
        out["buttons"]["profile_save"] = "测试同学" in page.inner_text("#sidebarUser")
        page.fill("#profileName", "学习者")
        page.click("text=保存称呼")
        page.wait_for_timeout(300)
        out["buttons"]["theme_toggle"] = page.locator("#themeBtn").count() == 1
        before = page.evaluate("document.documentElement.dataset.theme")
        page.click("#themeBtn")
        page.wait_for_timeout(300)
        after = page.evaluate("document.documentElement.dataset.theme")
        out["theme"] = {"before": before, "after": after, "changed": before != after}
        page.click('[data-set-lang="hant"]')
        page.wait_for_timeout(400)
        out["lang"]["hant_nav"] = page.locator(".nav").inner_text().replace("\n", "|")
        page.click('[data-set-lang="en"]')
        page.wait_for_timeout(400)
        out["lang"]["en_nav"] = page.locator(".nav").inner_text().replace("\n", "|")
        out["lang"]["en_settings"] = page.inner_text("#view")[:200]
        page.click('[data-set-lang="zh"]')
        page.wait_for_timeout(400)
        out["lang"]["zh_nav"] = page.locator(".nav").inner_text().replace("\n", "|")

        # course -> artifact -> reader tools
        page.goto(args.url + "#/library", wait_until="networkidle")
        page.wait_for_timeout(300)
        page.locator(".course-card").first.click()
        page.wait_for_timeout(300)
        page.locator('a[href^="#/artifact/"]').first.click()
        page.wait_for_timeout(400)
        out["buttons"]["artifact_word"] = page.locator('a[href$="lecture.docx"]').count() == 1
        page.locator('a[href^="#/read/"]').first.click()
        page.wait_for_timeout(1200)
        frame = page.frame_locator("iframe")
        out["buttons"]["reader_search"] = frame.locator("#tfSearchBtn").count() == 1
        if out["buttons"]["reader_search"]:
            frame.locator("#tfSearchBtn").click()
            page.wait_for_timeout(200)
            frame.locator("#tfSearchInput").fill("换路")
            frame.locator("#tfSearchInput").press("Enter")
            page.wait_for_timeout(300)
            out["buttons"]["reader_search_count"] = frame.locator("#tfSearchCount").inner_text()
            frame.locator("#tfSearchClose").click()
        out["buttons"]["reader_ai"] = frame.locator("#tfAiBtn").count() == 1
        if out["buttons"]["reader_ai"]:
            frame.locator("#tfAiBtn").click()
            page.wait_for_timeout(200)
            out["buttons"]["reader_ai_open"] = frame.locator("#tfAiPanel").is_visible()
            frame.locator("#tfAiClose").click()
        out["buttons"]["reader_export"] = frame.locator("#tfExportBtn").count() == 1
        if out["buttons"]["reader_export"]:
            frame.locator("#tfExportBtn").click()
            page.wait_for_timeout(200)
            out["buttons"]["reader_export_open"] = frame.locator("#tfExportMenu").is_visible()
            frame.locator("#tfExportBtn").click()

        # global AI
        page.goto(args.url, wait_until="networkidle")
        page.wait_for_timeout(300)
        page.click("#aiFab")
        page.wait_for_timeout(300)
        out["buttons"]["global_ai"] = page.locator("#aiDrawer").is_visible()
        page.click("#aiClose")

        # workbench tabs
        page.goto(args.url + "#/workbench", wait_until="networkidle")
        page.wait_for_timeout(400)
        tabs = page.locator(".tab")
        out["buttons"]["workbench_tabs"] = tabs.count()
        for i in range(min(5, tabs.count())):
            tabs.nth(i).click()
            page.wait_for_timeout(150)
        out["buttons"]["workbench_run"] = page.locator("#wbRun").count() == 1
        page.goto(args.url + "#/exam", wait_until="networkidle")
        page.wait_for_timeout(300)
        out["buttons"]["exam_form"] = page.locator("#examForm").count() == 1 and page.locator('#examForm select[name="mode"] option').count() == 4
        page.goto(args.url + "#/new", wait_until="networkidle")
        page.wait_for_timeout(300)
        out["buttons"]["new_custom_prompt"] = page.locator('#newForm textarea[name="custom_prompt"]').count() == 1
        out["buttons"]["new_weight_hint"] = "权重" in (page.locator('#newForm textarea[name="key_points"]').get_attribute("placeholder") or "")
        upload = page.locator('#newForm input[name="file"]')
        out["buttons"]["multi_form"] = upload.count() == 1 and upload.get_attribute("multiple") is not None and page.locator('#newForm input[name="weights"]').count() == 1

        # mobile
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(args.url, wait_until="networkidle")
        page.wait_for_timeout(300)
        page.click("#menuBtn")
        page.wait_for_timeout(250)
        out["mobile"]["sidebar_open"] = page.evaluate("document.querySelector('.sidebar').classList.contains('open')")
        page.evaluate("document.getElementById('menuBtn').click()")
        page.wait_for_timeout(200)

        browser.close()

    ok = not out["errors"] and all(out["routes"].values()) and out["buttons"].get("artifact_word") and ("Control" in out["lang"].get("en_nav", "") or "Today" in out["lang"].get("en_nav", ""))
    out["ok"] = bool(ok)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2)[:4000])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
