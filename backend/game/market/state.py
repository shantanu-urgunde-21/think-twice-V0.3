"""Hidden Market V1 — state shapes.

MarketState is the server's ground truth. PlayerView is the per-player
projection sent to clients: it must never leak another player's private
fields. See rules.project() for the only place that boundary is crossed.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

ActionType = Literal["BUY", "SELL", "HOLD"]


@dataclass
class PlayerState:
    player_id: int
    cash: float
    inventory: int
    # Private signal for the *current* round: a noisy hint of next round's
    # price delta. Regenerated each round in rules.start_round().
    private_signal: float = 0.0


@dataclass
class Action:
    player_id: int
    type: ActionType
    qty: int = 0  # ignored for HOLD


@dataclass
class RoundEvent:
    """One entry in the resolved-round log. Kept structurally simple now;
    this shape is what Phase 5 (event log) will persist and replay."""
    round_number: int
    price_before: float
    price_after: float
    trades: List[dict]  # [{player_id, type, qty, fill_price}]


@dataclass
class MarketState:
    game_id: int
    round_number: int
    max_rounds: int
    price: float
    price_history: List[float]
    players: Dict[int, PlayerState]
    pending_actions: Dict[int, Action] = field(default_factory=dict)
    events: List[RoundEvent] = field(default_factory=list)
    finished: bool = False


@dataclass
class PlayerView:
    """What one player (or the AI) is allowed to see."""
    game_id: int
    round_number: int
    max_rounds: int
    price: float
    price_history: List[float]
    cash: float
    inventory: int
    private_signal: float
    has_submitted: bool
    submissions_count: int
    total_players: int
    finished: bool
