"""单实例锁：避免两个 App 同时打开同一个数据库。"""
from __future__ import annotations

import os

from core import paths

_handle = None


def acquire() -> bool:
    global _handle
    if os.getenv("TERMFINALE_ALLOW_MULTI") == "1":
        return True
    try:
        paths.ensure_dirs()
        fh = open(paths.data_dir() / "app.lock", "a+")
    except OSError:
        return True
    try:
        if os.name == "nt":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return False
    _handle = fh
    return True
