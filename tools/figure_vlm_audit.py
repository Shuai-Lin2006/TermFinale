"""机器读图抽检：完整性/裁切/乱码/标签；不是人工签字。"""
from __future__ import annotations
import base64, io, json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
from openai import OpenAI
from core.config import get_key, load_env, vision_model

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "evidence" / "figure_vlm_audit.json"
load_env()
client = OpenAI(api_key=get_key("DASHSCOPE_API_KEY", "sk-not-configured"),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

CASES = []
for p in sorted(ROOT.glob("docs/evidence/**/assets/figures/*.png")):
    CASES.append((p.stem, p))
for p in sorted(ROOT.glob("data/figure_bench/*.png")):
    CASES.append((p.stem, p))
for p in [Path("/tmp/3d.png"), Path("/tmp/mujoco.png"), Path("/tmp/spice.png")]:
    if p.is_file(): CASES.append((p.stem, p))
# 去重，最多 30 张
seen = set(); uniq = []
for name, p in CASES:
    if p in seen: continue
    seen.add(p); uniq.append((name, p))
CASES = uniq[:30]

def audit(path: Path) -> dict:
    img = Image.open(path).convert("RGB")
    if max(img.size) > 1280:
        img.thumbnail((1280, 1280), Image.LANCZOS)
    buf = io.BytesIO(); img.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode()
    prompt = ("检查这张教学图是否完整：1) 是否有内容被裁掉/贴边截断；2) 是否有空白图/乱码/方框；"
              "3) 标签/关键文字是否可读；4) 是否明显与教学图无关。只输出 JSON，不要 Markdown："
              '{"verdict":"ok|warn|fail","issues":["..."],"labels":["..."]}')
    r = client.chat.completions.create(timeout=60, model=vision_model(), messages=[{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        {"type": "text", "text": prompt}]}], temperature=0, max_tokens=500)
    txt = (r.choices[0].message.content or "").strip()
    txt = txt.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(txt)
    except Exception:
        data = {"verdict": "fail", "issues": [f"返回非 JSON：{txt[:200]}"], "labels": []}
    data["case"] = path.name
    return data


def main():
    import sys
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    fresh = "--fresh" in sys.argv
    limit = 30
    for x in sys.argv[1:]:
        if x.startswith("--limit="):
            limit = int(x.split("=", 1)[1])
    wanted = set(args)
    cases = [c for c in CASES if (not wanted or c[0] in wanted)][:limit]

    previous = {}
    if OUT.is_file() and not fresh:
        try:
            previous = {r["case"]: r for r in json.loads(OUT.read_text(encoding="utf-8"))}
        except Exception:
            previous = {}

    rows = []
    def run(item):
        name, p = item
        if not p.is_file():
            return {"case": name, "verdict": "skip", "issues": ["missing"], "labels": []}
        for attempt in range(2):
            try:
                d = audit(p); d["case"] = name; return d
            except Exception as exc:
                if attempt == 1:
                    return {"case": name, "verdict": "timeout", "issues": [str(exc)], "labels": []}
        return {"case": name, "verdict": "fail", "issues": ["unknown"], "labels": []}

    # 已 ok 的跳过；timeout/fail 重试
    todo = [(n, p) for n, p in cases if previous.get(n, {}).get("verdict") not in ("ok",)]
    rows = [previous[n] for n, _ in cases if n in previous and previous[n].get("verdict") == "ok"]
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = {ex.submit(run, item): item[0] for item in todo}
        for f in as_completed(futs):
            r = f.result(); rows.append(r)
            print(r.get("case"), r.get("verdict"), (r.get("issues") or [])[:1], flush=True)
            OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for r in rows if r.get("verdict") == "ok")
    warn = sum(1 for r in rows if r.get("verdict") == "warn")
    bad = [r for r in rows if r.get("verdict") not in ("ok", "warn")]
    print(f"ok={ok} warn={warn} bad={len(bad)} total={len(rows)} -> {OUT}")
    raise SystemExit(0 if len(rows) == len(cases) and not bad else 1)


if __name__ == "__main__":
    main()
