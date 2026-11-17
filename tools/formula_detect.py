
"""Run MinerU MFD (math formula detection) in the docling venv.

Usage: python tools/formula_detect.py image1.png image2.png ...
Output: {"images":[{"path":"...","boxes":[{"cls":"isolated|embedding","conf":0.76,"xyxy":[...]}]}]}
"""
from __future__ import annotations

import glob
import json
import os
import sys

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")


def _weights() -> str:
    explicit = os.getenv("TERMFINALE_MFD_WEIGHTS", "").strip()
    if explicit and os.path.isfile(explicit):
        return explicit
    pattern = os.path.expanduser(
        "~/.cache/huggingface/hub/models--opendatalab--PDF-Extract-Kit/snapshots/*/models/MFD/weights.pt"
    )
    matches = sorted(glob.glob(pattern))
    if matches:
        return matches[-1]
    raise SystemExit("MFD weights not found; set TERMFINALE_MFD_WEIGHTS")


def main() -> None:
    import warnings
    warnings.filterwarnings("ignore")
    from ultralytics import YOLO

    model = YOLO(_weights())
    out = []
    for path in sys.argv[1:]:
        result = model.predict(path, imgsz=1024, conf=0.35, device="cpu", verbose=False)
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
