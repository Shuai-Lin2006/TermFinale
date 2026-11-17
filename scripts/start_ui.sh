#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
PORT="${PORT:-8877}"
exec .venv/bin/python -m uvicorn tfv2.api.product_app:app --host 127.0.0.1 --port "$PORT"
