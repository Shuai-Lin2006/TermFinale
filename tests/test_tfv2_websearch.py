import unittest
from tfv2.product import websearch


class WebSearchSafetyTest(unittest.TestCase):
    def test_private_urls_rejected(self):
        self.assertFalse(websearch._public_url("http://127.0.0.1:8907/"))
        self.assertFalse(websearch._public_url("http://localhost/"))
        self.assertFalse(websearch._public_url("file:///etc/passwd"))

    def test_web_context_keeps_url_and_content(self):
        ctx = websearch.web_context([
            {"title": "Example", "url": "https://example.com/a", "content": "hello"}
        ])
        self.assertIn("https://example.com/a", ctx)
        self.assertIn("hello", ctx)

    def test_bing_redirect_decode(self):
        # 非 Bing 链接原样返回
        self.assertEqual(websearch._decode_bing("https://example.com/x"), "https://example.com/x")


if __name__ == "__main__":
    unittest.main()
