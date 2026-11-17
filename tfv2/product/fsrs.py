"""复习排程：FSRS 风格（stability / difficulty），不依赖外部库。

说明（不夸大）：这是按 FSRS 公开的“记忆稳定性”思路实现的简化版，目标是
比固定间隔 [1,2,4,7,15,30] 更贴合遗忘曲线，**不声称与 fsrs 官方库逐位一致**。
公式公开、可复现：
- 可提取度 R(t,S) = (1 + t/(9S))^(-1)
- 目标召回率 0.9 时，下次间隔 ≈ S
- 评分：1=Again，2=Hard，3=Good，4=Easy
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import date, timedelta

TARGET_RETENTION = 0.9
DECAY = -1.0
FACTOR = 9.0

GRADE_AGAIN = 1
GRADE_HARD = 2
GRADE_GOOD = 3
GRADE_EASY = 4


@dataclass(frozen=True)
class CardState:
    stability: float = 0.0     # 记忆稳定性（天）
    difficulty: float = 5.0    # 难度 1（易）–10（难）
    reps: int = 0
    lapses: int = 0
    last_review: date | None = None


def retrievability(state: CardState, *, today: date) -> float:
    """今天还记得的概率；新卡按 0 处理。"""
    if not state.last_review or state.stability <= 0:
        return 0.0
    elapsed = max(0, (today - state.last_review).days)
    return round((1 + elapsed / (FACTOR * state.stability)) ** DECAY, 4)


def init_stability(grade: int) -> float:
    return {GRADE_AGAIN: 0.6, GRADE_HARD: 1.4, GRADE_GOOD: 2.2, GRADE_EASY: 3.6}.get(grade, 2.2)


def next_stability(state: CardState, grade: int, *, today: date) -> float:
    if state.reps == 0 or state.stability <= 0:
        return init_stability(grade)
    s = state.stability
    if grade == GRADE_AGAIN:
        return round(max(0.5, s * 0.2), 3)
    if grade == GRADE_HARD:
        return round(s * 1.25, 3)
    if grade == GRADE_GOOD:
        # 回忆难度越高（retrievability 低），涨得越多
        r = max(0.05, retrievability(state, today=today))
        return round(s * (1.6 + (1 - r) * 0.9), 3)
    return round(s * 2.6, 3)


def next_difficulty(state: CardState, grade: int) -> float:
    d = state.difficulty
    if grade == GRADE_AGAIN:
        d += 0.9
    elif grade == GRADE_HARD:
        d += 0.25
    elif grade == GRADE_GOOD:
        d -= 0.15
    else:
        d -= 0.45
    return round(min(10.0, max(1.0, d)), 3)


def interval_days(stability: float) -> int:
    """目标召回率 0.9 下，稳定性 S 对应约 S 天；做上下限保护。"""
    if stability <= 0:
        return 1
    # R=0.9 时 t ≈ S（见模块说明），直接取稳定性天数并做上下限保护
    return int(max(1, min(365, round(stability))))


def review(state: CardState, grade: int, *, today: date) -> tuple[CardState, int]:
    """复习一次，返回新状态与下次间隔天数。"""
    if grade not in (GRADE_AGAIN, GRADE_HARD, GRADE_GOOD, GRADE_EASY):
        raise ValueError(f"未知评分：{grade}")
    stability = next_stability(state, grade, today=today)
    difficulty = next_difficulty(state, grade)
    lapses = state.lapses + (1 if grade == GRADE_AGAIN else 0)
    new_state = CardState(stability=stability, difficulty=difficulty,
                          reps=state.reps + 1, lapses=lapses, last_review=today)
    return new_state, interval_days(stability)


def due_cards(cards: list[dict], *, today: date, limit: int = 100) -> list[dict]:
    """到期复习：先逾期、再按稳定性低（更容易忘）优先。cards 需含 next_review/稳定性字段。"""
    def key(card: dict):
        due = str(card.get("next_review") or "")
        overdue = due[:10] <= today.isoformat()
        stability = float(card.get("stability") or 0.0)
        return (0 if overdue else 1, due, stability)

    pending = [c for c in cards if str(c.get("next_review") or "")[:10] <= today.isoformat()]
    pending.sort(key=key)
    return pending[:max(0, limit)]


def forecast(cards: list[dict], *, today: date, days: int = 7) -> list[dict]:
    """未来 N 天的到期数量（含今天），用于页面上的“每天要复习多少”。"""
    out = []
    for offset in range(max(0, days)):
        day = (today + timedelta(days=offset)).isoformat()
        count = sum(1 for c in cards if str(c.get("next_review") or "")[:10] == day)
        overdue = sum(1 for c in cards if str(c.get("next_review") or "")[:10] < today.isoformat())
        out.append({"date": day, "due": count, "overdue": overdue if offset == 0 else 0})
    return out


def retention_curve(stability: float, *, days: int = 30) -> list[dict]:
    """稳定性 S 的记忆保持曲线，给用户看“什么时候该复习”。"""
    if stability <= 0:
        return []
    return [{"day": d, "retention": round((1 + d / (FACTOR * stability)) ** DECAY, 3)}
            for d in range(0, max(1, days) + 1)]
