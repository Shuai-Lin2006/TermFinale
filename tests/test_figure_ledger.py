import tempfile, unittest
from pathlib import Path
from PIL import Image
from core.quality.figure_ledger import audit_figures

class LedgerTest(unittest.TestCase):
    def test_missing_and_used(self):
        with tempfile.TemporaryDirectory() as d:
            Image.new('RGB',(200,200),'white').save(Path(d)/'a.png')
            src=['【《x》第 1 页】\n[[[IMAGE: a.png | 图注: A图（第 1 页）]]]\n[[[IMAGE: b.png | 图注: B图（第 1 页）]]]']
            md='[[[IMAGE: a.png | 图注: A图（第 1 页）]]]'
            r=audit_figures(src,md,d)
            self.assertEqual(r.source,2); self.assertEqual(r.used,1); self.assertTrue(r.missing)
