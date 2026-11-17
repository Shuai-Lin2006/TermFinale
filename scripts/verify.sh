#!/usr/bin/env bash
# 一条命令做完整验证：单元测试 + 评测脚本 + API 文档导出
# 用法：bash scripts/verify.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-.venv/bin/python}"
echo "== 单元测试 =="
"$PY" -m unittest discover -s tests -t . 2>&1 | tail -3
echo "== 评测脚本（不跑 OCR，快速） =="
"$PY" scripts/eval_harness.py --no-ocr 2>&1 | tail -20
echo "== API 文档 =="
"$PY" scripts/export_openapi.py 2>&1 | tail -1
