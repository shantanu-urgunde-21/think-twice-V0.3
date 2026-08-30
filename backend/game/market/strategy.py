"""AI opponent for Hidden Market V1.

Deliberately a cheap heuristic, not an LLM (see internaldocs roadmap v4,
Phase 4 rationale): the point of V1 is to prove out the async plumbing
around a slow, unreliable decision-maker. Simulated latency stands in for
real inference latency so the queueing/timeout/fallback logic added in
Phase 4 has something realistic to work against. Swapping this out for a
real model later should not require touching the engine.
"""

import random
import time
from dataclasses import dataclass

from .state import Action, PlayerView

# Simulated decision latency range, matching the roadmap's target budget
# for a real model call (Phase 4: 500ms-3s).
MIN_LATENCY_SECONDS = 0.5
MAX_LATENCY_SECONDS = 2.0

AI_PLAYER_ID = -1  # reserved id; never assigned to a real Player row


@dataclass
class TrendFollowerStrategy:
    """Buys when its private signal suggests a rising price, sells when
    it suggests a fall, holds near zero. Trade size scales with signal
    confidence and is capped by available cash/inventory.
    """

    signal_threshold: float = 0.5
    max_trade_qty: int = 10

    def act(self, observation: PlayerView) -> Action:
        signal = observation.private_signal

        if signal > self.signal_threshold:
            affordable = int(observation.cash // observation.price) if observation.price > 0 else 0
            qty = min(self.max_trade_qty, max(0, affordable))
            if qty > 0:
                return Action(player_id=AI_PLAYER_ID, type="BUY", qty=qty)
        elif signal < -self.signal_threshold:
            qty = min(self.max_trade_qty, observation.inventory)
            if qty > 0:
                return Action(player_id=AI_PLAYER_ID, type="SELL", qty=qty)

        return Action(player_id=AI_PLAYER_ID, type="HOLD")


def act_with_simulated_latency(observation: PlayerView, strategy: TrendFollowerStrategy) -> Action:
    """Synchronous call used by the V1 engine. This blocking sleep is the
    exact problem Phase 4 (async AI workers) exists to solve — do not
    "fix" it here by removing the delay; the delay is the point."""
    delay = random.uniform(MIN_LATENCY_SECONDS, MAX_LATENCY_SECONDS)
    time.sleep(delay)
    return strategy.act(observation)
