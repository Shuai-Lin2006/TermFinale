
"""Run DocLayout-YOLO in the docling venv and print layout boxes JSON.

Usage: python tools/doclayout_detect.py image1.png image2.png ...
"""
from __future__ import annotations

import glob
import json
import os
import sys

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")


def _weights() -> str:
    explicit = os.getenv("TERMFINALE_DOCLAYOUT_WEIGHTS", "").strip()
    if explicit and os.path.isfile(explicit):
        return explicit
    pattern = os.path.expanduser(
        "~/.cache/huggingface/hub/models--juliozhao--DocLayout-YOLO-DocStructBench/snapshots/*/doclayout_yolo_docstructbench_imgsz1024.pt"
    )
    matches = sorted(glob.glob(pattern))
    if matches:
        return matches[-1]
    raise SystemExit("DocLayout weights not found; set TERMFINALE_DOCLAYOUT_WEIGHTS")


def main() -> None:
    from doclayout_yolo import YOLOv10

    model = YOLOv10(_weights())
    out = []
    for path in sys.argv[1:]:
        result = model.predict(path, imgsz=1024, conf=0.22, device="cpu", verbose=False)
        boxes = []
        for r in result:
            for b in r.boxes:
                boxes.append({
                    "cls": r.names[int(b.cls)],
                    "conf": round(float(b.conf), 3),
                    "xyxy": [round(float(x), 1) for x in b.xyxy[0]],
                })
        out.append({"path": path, "boxes": boxes})
    print(json.dumps({"images": out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
