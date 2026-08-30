"""Hidden Market V1 — pure resolution logic.

resolve() must stay a pure function of (state, actions, rng_seed): same
inputs always produce the same outputs. This is what makes replay (event
log reconstruction), deterministic tests, and headless load generation
possible. Do not read the clock, touch the database, or use a global RNG
in here — take a seeded random.Random and thread it through explicitly.
"""

import random
from typing import Dict, List

from .state import Action, MarketState, PlayerState, PlayerView, RoundEvent

STARTING_CASH = 1000.0
STARTING_PRICE = 50.0
PRICE_ELASTICITY = 0.5  # price move per unit of net demand
SIGNAL_NOISE_STDDEV = 1.5
MIN_PRICE = 1.0


def new_game(game_id: int, player_ids: List[int], max_rounds: int, seed: int) -> MarketState:
    rng = random.Random(seed)
    players = {
        pid: PlayerState(player_id=pid, cash=STARTING_CASH, inventory=0)
        for pid in player_ids
    }
    state = MarketState(
        game_id=game_id,
        round_number=1,
        max_rounds=max_rounds,
        price=STARTING_PRICE,
        price_history=[STARTING_PRICE],
        players=players,
    )
    _deal_signals(state, rng)
    return state


def _true_next_delta(rng: random.Random) -> float:
    """The actual price movement that will occur, before noise is added
    to produce each player's private signal. Not stored on state — it is
    implicit in the seeded rng stream so resolve() can reconstruct it
    deterministically without persisting it separately."""
    return rng.uniform(-3.0, 3.0)


def _deal_signals(state: MarketState, rng: random.Random) -> None:
    """Give each player a private, noisy hint of the coming price move.
    Stored per-player so projections can stay isolated."""
    true_delta = _true_next_delta(rng)
    for player in state.players.values():
        noise = rng.gauss(0, SIGNAL_NOISE_STDDEV)
        player.private_signal = round(true_delta + noise, 2)
    # Stash the true delta on the state so resolve() can use the same
    # value that signals were derived from this round.
    state._pending_true_delta = true_delta  # type: ignore[attr-defined]


def project(state: MarketState, player_id: int) -> PlayerView:
    player = state.players[player_id]
    return PlayerView(
        game_id=state.game_id,
        round_number=state.round_number,
        max_rounds=state.max_rounds,
        price=state.price,
        price_history=list(state.price_history),
        cash=player.cash,
        inventory=player.inventory,
        private_signal=player.private_signal,
        has_submitted=player_id in state.pending_actions,
        submissions_count=len(state.pending_actions),
        total_players=len(state.players),
        finished=state.finished,
    )


def submit_action(state: MarketState, action: Action) -> None:
    if state.finished:
        raise ValueError("game finished")
    if action.player_id not in state.players:
        raise ValueError("unknown player")
    if action.player_id in state.pending_actions:
        raise ValueError("already submitted")
    if action.type not in ("BUY", "SELL", "HOLD"):
        raise ValueError("invalid action type")
    if action.type != "HOLD" and action.qty <= 0:
        raise ValueError("qty must be positive for BUY/SELL")
    if action.type == "SELL" and action.qty > state.players[action.player_id].inventory:
        raise ValueError("cannot sell more than current inventory")
    state.pending_actions[action.player_id] = action


def resolve_round(state: MarketState, seed: int) -> RoundEvent:
    """Apply all pending actions (defaulting missing ones to HOLD),
    settle trades at the resolved price, move the price, and advance
    the round. Returns the event describing what happened.
    """
    if state.finished:
        raise ValueError("game finished")

    rng = random.Random(seed * 1_000_003 + state.round_number)

    for pid in state.players:
        state.pending_actions.setdefault(pid, Action(player_id=pid, type="HOLD"))

    price_before = state.price
    trades: List[dict] = []
    net_demand = 0

    for pid, action in state.pending_actions.items():
        player = state.players[pid]
        if action.type == "BUY":
            net_demand += action.qty
        elif action.type == "SELL":
            net_demand -= action.qty

    price_after = max(MIN_PRICE, round(price_before + net_demand * PRICE_ELASTICITY, 2))

    for pid, action in state.pending_actions.items():
        player = state.players[pid]
        if action.type == "BUY":
            cost = action.qty * price_after
            player.cash -= cost
            player.inventory += action.qty
            trades.append({"player_id": pid, "type": "BUY", "qty": action.qty, "fill_price": price_after})
        elif action.type == "SELL":
            proceeds = action.qty * price_after
            player.cash += proceeds
            player.inventory -= action.qty
            trades.append({"player_id": pid, "type": "SELL", "qty": action.qty, "fill_price": price_after})
        else:
            trades.append({"player_id": pid, "type": "HOLD", "qty": 0, "fill_price": price_after})

    event = RoundEvent(
        round_number=state.round_number,
        price_before=price_before,
        price_after=price_after,
        trades=trades,
    )

    state.price = price_after
    state.price_history.append(price_after)
    state.events.append(event)
    state.pending_actions = {}

    if state.round_number >= state.max_rounds:
        state.finished = True
    else:
        state.round_number += 1
        _deal_signals(state, rng)

    return event


def final_scores(state: MarketState) -> Dict[int, float]:
    return {
        pid: round(p.cash + p.inventory * state.price, 2)
        for pid, p in state.players.items()
    }
