from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from treys import Card, Deck, Evaluator

from .models import Decision, GameState


@dataclass
class StrategyConfig:
    opponents: int = 5
    monte_carlo_iterations: int = 800


class StrategyEngine:
    def __init__(self, config: StrategyConfig) -> None:
        self.config = config
        self._evaluator = Evaluator()

    def choose_action(self, state: GameState) -> Optional[Decision]:
        available = state.available_actions
        if not available:
            return None

        if any(card == "??" for card in state.hero_cards):
            safe_action = self._safe_action(available)
            return Decision(
                action=safe_action,
                equity=None,
                reason="Hero cards unreadable from stream; selecting safe fallback",
            )

        equity = self._estimate_equity(
            hero_cards=list(state.hero_cards),
            board_cards=list(state.board_cards),
            opponents=self.config.opponents,
            iterations=self.config.monte_carlo_iterations,
        )
        if equity is None:
            safe_action = self._safe_action(available)
            return Decision(action=safe_action, equity=None, reason="Invalid cards detected")

        call_amount = max(0.0, state.call_amount)
        can_call = "call" in available
        can_raise = "raise" in available
        can_fold = "fold" in available

        if can_call and call_amount == 0.0:
            if equity >= 0.68 and can_raise:
                return Decision("raise", equity, "Free action with high equity")
            return Decision("call", equity, "Check/call free action")

        pot_odds = self._pot_odds(call_amount=call_amount, pot_size=state.pot)
        raise_threshold = max(0.67, pot_odds + 0.28)
        call_threshold = max(0.44, pot_odds + 0.06)

        if can_raise and equity >= raise_threshold:
            return Decision("raise", equity, f"Equity {equity:.2f} exceeds raise threshold {raise_threshold:.2f}")

        if can_call and equity >= call_threshold:
            return Decision("call", equity, f"Equity {equity:.2f} exceeds call threshold {call_threshold:.2f}")

        if can_fold:
            return Decision("fold", equity, f"Equity {equity:.2f} below profitable continue threshold")

        if can_call:
            return Decision("call", equity, "Fold unavailable")

        return None

    @staticmethod
    def _safe_action(available: set[str]) -> str:
        if "call" in available:
            return "call"
        if "fold" in available:
            return "fold"
        if "raise" in available:
            return "raise"
        return "fold"

    @staticmethod
    def _pot_odds(call_amount: float, pot_size: Optional[float]) -> float:
        if call_amount <= 0:
            return 0.0
        if pot_size is None or pot_size <= 0:
            return 0.25
        return call_amount / (pot_size + call_amount)

    def _estimate_equity(
        self,
        hero_cards: list[str],
        board_cards: list[str],
        opponents: int,
        iterations: int,
    ) -> Optional[float]:
        try:
            hero = [Card.new(card) for card in hero_cards]
            board = [Card.new(card) for card in board_cards]
        except Exception:
            return None

        used = set(hero + board)
        if len(used) != len(hero) + len(board):
            return None

        missing_board = 5 - len(board)
        if missing_board < 0:
            return None

        draw_count = (2 * opponents) + missing_board
        full_deck = [c for c in Deck.GetFullDeck() if c not in used]
        if draw_count > len(full_deck):
            return None

        wins = 0.0
        for _ in range(iterations):
            draw = random.sample(full_deck, draw_count)
            board_complete = board + draw[:missing_board]

            scores = [self._evaluator.evaluate(board_complete, hero)]
            index = missing_board
            for _ in range(opponents):
                opp = [draw[index], draw[index + 1]]
                index += 2
                scores.append(self._evaluator.evaluate(board_complete, opp))

            best = min(scores)
            winners = scores.count(best)
            hero_score = scores[0]
            if hero_score == best:
                wins += 1.0 / winners

        return wins / float(iterations)
