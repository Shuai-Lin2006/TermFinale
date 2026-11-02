"""五维人设的收尾语与显示标签。

从 main.py 抽离，供 services/ 复用；UI 只负责显示。
"""
from __future__ import annotations

OUTROS = {
    "zh": {
        "老师": "## 🎓 结语\n同学们，书山有路勤为径。这份讲义里浓缩了期末最核心的考点，老师能帮你们的就到这里了。剩下的路，需要你们自己去考场上走。不要怕，深呼吸，把这几天背的公式稳稳地写在卷子上。祝你们旗开得胜，老师等你们的好消息！",
        "学术AI": "## 🎓 结语\n数据解析完毕。当前讲义已包含通过最优算法提取的核心知识拓扑。请考生按照既定逻辑执行复习，避免非必要的情绪波动。预祝在即将到来的期末考试中，运算无误，得分最大化。",
        "暴力极客": "## 🎓 结语\n行了，能教的都教了！别再搁这儿磨叽了，赶紧把这些公式给我死死刻在脑子里！考场上遇到不会的，也给我把公式列上去蹭步骤分！少废话，滚去复习，明天干翻那张卷子！听懂没有？！",
        "温柔小姐姐": "## 🎓 结语\n宝宝，看到这里你真的已经很棒啦，辛苦了呢~🥺 复习是一件很枯燥的事情，但你一直坚持到了现在，姐姐真的很为你骄傲。今晚不要再熬夜啦，乖乖早点睡，把讲义里姐姐划的重点再看最后一眼。明天考试别紧张，你那么聪明，一定没问题的。姐姐会一直在你身后陪着你，等你的好消息哦~抱抱~🌸✨",
        "阳光小哥哥": "## 🎓 结语\n兄弟，能坚持看完这份讲义，你已经击败了80%的人。复习确实很累，但你要相信，你熬过的夜、刷过的题，都会变成卷子上的分数。别给自己太大压力，按我给你的步骤和套路来，稳扎稳打就行。去考场上放手一搏吧，别怕，有我在，你一定能行。祝你逢考必过！"
    },
    "en": {
        "老师": "## 🎓 Conclusion\nStudents, there is no royal road to learning. This guide contains the core exam points. I've done what I can. The rest is up to you. Don't be afraid, take a deep breath, and write those formulas steadily. Good luck!",
        "学术AI": "## 🎓 Conclusion\nData analysis complete. Core knowledge topology extracted. Proceed with your review as scheduled. Emotional fluctuations are unnecessary. Maximize your score. End of transmission.",
        "暴力极客": "## 🎓 Conclusion\nAlright, that's all I got! Stop dawdling and memorize these formulas! Even if you don't know the answer, write down the formulas for partial credit! Stop whining and go crush that exam!",
        "温柔小姐姐": "## 🎓 Conclusion\nDarling, you're doing amazing and working so hard~🥺 It's a tough journey, but I'm so proud of you. Get some sleep tonight, review my highlights one last time. Don't be nervous tomorrow, you're smart and you'll do great. I'm always here for you~ Hugs~🌸✨",
        "阳光小哥哥": "## 🎓 Conclusion\nBro, if you made it through this guide, you're already ahead of 80% of people. It's tiring, but your hard work will pay off. Don't stress, just follow my steps. Go out there and give it your all. I believe in you! You got this."
    }
}

# 下拉框显示文案 → PERSONAS 的 key（ai_engine.PERSONAS 必须能接住）
PERSONA_LABELS: dict[str, str] = {
    "温柔小姐姐（适合零基础）": "温柔小姐姐",
    "阳光小哥哥（逻辑清晰）": "阳光小哥哥",
    "学术AI（极简硬核）": "学术AI",
    "老师（严谨推导）": "老师",
    "暴力极客（极限施压）": "暴力极客",
}


def persona_from_label(label: str) -> str:
    """把下拉框文案转成人设 key；未知值安全回落到温柔小姐姐。"""
    return PERSONA_LABELS.get(label, "温柔小姐姐")
