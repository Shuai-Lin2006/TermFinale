"""运行期数据目录：源码默认项目 data/，打包版由桌面外壳指向用户目录。"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(os.getenv("TFV2_DATA_ROOT", str(ROOT / "data"))).expanduser()
ARTIFACT_ROOT = DATA_ROOT / "artifacts"
UPLOAD_ROOT = DATA_ROOT / "uploads"
EXPORT_ROOT = DATA_ROOT / "exports"
BACKUP_ROOT = DATA_ROOT / "backups"
ARCHIVE_ROOT = DATA_ROOT / "archive"
