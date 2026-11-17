"""复习排程：FSRS 风格的状态转移与每日负载。"""
from __future__ import annotations

import unittest
from datetime import date

from tfv2.product import fsrs


class FsrsTests(unittest.TestCase):
    def test_new_card_intervals_follow_grade(self) -> None:
        today = date(2026, 1, 1)
        again, _ = fsrs.review(fsrs.CardState(), fsrs.GRADE_AGAIN, today=today)
        good, i_good = fsrs.review(fsrs.CardState(), fsrs.GRADE_GOOD, today=today)
        easy, i_easy = fsrs.review(fsrs.CardState(), fsrs.GRADE_EASY, today=today)
        self.assertLess(again.stability, good.stability)
        self.assertLess(good.stability, easy.stability)
        self.assertLess(i_good, i_easy)

    def test_again_resets_stability_and_counts_lapse(self) -> None:
        today = date(2026, 1, 1)
        state = fsrs.CardState(stability=30, difficulty=4, reps=5, last_review=date(2025, 12, 20))
        new, interval = fsrs.review(state, fsrs.GRADE_AGAIN, today=today)
        self.assertLess(new.stability, 10)
        self.assertEqual(new.lapses, 1)
        self.assertGreaterEqual(interval, 1)

    def test_easy_beats_good_over_time(self) -> None:
        today = date(2026, 1, 1)
        base = fsrs.CardState(stability=5, difficulty=5, reps=2, last_review=date(2025, 12, 28))
        good, i_good = fsrs.review(base, fsrs.GRADE_GOOD, today=today)
        easy, i_easy = fsrs.review(base, fsrs.GRADE_EASY, today=today)
        self.assertGreater(i_easy, i_good)

    def test_hard_increases_difficulty(self) -> None:
        base = fsrs.CardState(stability=5, difficulty=5, reps=1, last_review=date(2026, 1, 1))
        new, _ = fsrs.review(base, fsrs.GRADE_HARD, today=date(2026, 1, 2))
        self.assertGreater(new.difficulty, base.difficulty)

    def test_interval_bounds(self) -> None:
        self.assertEqual(fsrs.interval_days(0), 1)
        self.assertLessEqual(fsrs.interval_days(10_000), 365)

    def test_retrievability_decays(self) -> None:
        state = fsrs.CardState(stability=10, last_review=date(2026, 1, 1))
        r0 = fsrs.retrievability(state, today=date(2026, 1, 1))
        r10 = fsrs.retrievability(state, today=date(2026, 1, 11))
        self.assertGreater(r0, r10)
        self.assertGreater(r0, 0.8)


class DueAndForecastTests(unittest.TestCase):
    CARDS = [
        {"id": 1, "next_review": "2026-01-01", "stability": 5},
        {"id": 2, "next_review": "2026-01-01", "stability": 2},
        {"id": 3, "next_review": "2026-01-03", "stability": 9},
        {"id": 4, "next_review": "2025-12-20", "stability": 40},
    ]

    def test_due_order_overdue_then_low_stability(self) -> None:
        got = fsrs.due_cards(self.CARDS, today=date(2026, 1, 2))
        self.assertEqual([c["id"] for c in got], [4, 2, 1])

    def test_due_limit(self) -> None:
        self.assertEqual(len(fsrs.due_cards(self.CARDS, today=date(2026, 1, 2), limit=1)), 1)

    def test_forecast_counts(self) -> None:
        rows = fsrs.forecast(self.CARDS, today=date(2026, 1, 1), days=3)
        self.assertEqual([r["due"] for r in rows], [2, 0, 1])
        self.assertEqual(rows[0]["overdue"], 1)
