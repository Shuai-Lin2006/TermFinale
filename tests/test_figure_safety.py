"""Round 17 safety: unverified figures are rejected, not attached."""
from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from tfv2.product import generate


class FigureSafetyTests(unittest.TestCase):
    def test_vision_deadline_rejects_figure(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "x.png"
            Image.new("RGB", (320, 200), "white").save(path)
            section = SimpleNamespace(title="神经传导", summary="动作电位沿轴突传播", blocks=[])
            old = generate._VISION_DEADLINE
            generate._VISION_DEADLINE = time.monotonic() - 1
            try:
                self.assertFalse(generate._figure_supports(str(path), section, "神经传导"))
            finally:
                generate._VISION_DEADLINE = old


if __name__ == "__main__":
    unittest.main()
