import unittest

from tfv2.api.product_app import _ask_effort


class AskEffortRoutingTests(unittest.TestCase):
    def test_simple_chat_uses_low_effort(self):
        self.assertEqual(_ask_effort("一句话解释暂态过程", "chat"), "low")

    def test_deep_question_keeps_full_thinking(self):
        self.assertIsNone(_ask_effort("请推导 RC 电路三要素法的求解步骤并说明为什么", "chat"))

    def test_explain_mode_keeps_full_thinking(self):
        self.assertIsNone(_ask_effort("解释一下", "explain"))

    def test_deep_toggle_forces_full_thinking(self):
        self.assertIsNone(_ask_effort("一句话解释暂态过程", "chat", deep=True))


if __name__ == "__main__":
    unittest.main()
