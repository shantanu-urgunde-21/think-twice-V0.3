"""Hidden Market V1 — persistence adapter.

Bridges the pure functions in rules.py to SQLAlchemy. This module owns
the translation between MarketState (in-memory, pure) and the DB rows;
rules.py itself never imports SQLAlchemy or touches the database.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from database import MarketAction, MarketGame, MarketPlayerState, MarketRoundResult, Player
from . import rules
from .state import Action, MarketState, PlayerState
from .strategy import AI_PLAYER_ID, TrendFollowerStrategy, act_with_simulated_latency


def load_state(db: Session, market_game: MarketGame) -> MarketState:
    """Reconstruct in-memory MarketState from persisted rows."""
    player_rows = (
        db.query(MarketPlayerState)
        .filter(MarketPlayerState.market_game_id == market_game.id)
        .all()
    )
    players = {
        row.player_id: PlayerState(
            player_id=row.player_id,
            cash=row.cash,
            inventory=row.inventory,
            private_signal=row.private_signal,
        )
        for row in player_rows
    }
    pending = (
        db.query(MarketAction)
        .filter(
            MarketAction.market_game_id == market_game.id,
            MarketAction.round_number == market_game.round_number,
        )
        .all()
    )
    pending_actions = {
        row.player_id: Action(player_id=row.player_id, type=row.action_type, qty=row.qty)
        for row in pending
    }
    return MarketState(
        game_id=market_game.game_id,
        round_number=market_game.round_number,
        max_rounds=market_game.max_rounds,
        price=market_game.price,
        price_history=list(market_game.price_history or [market_game.price]),
        players=players,
        pending_actions=pending_actions,
        finished=market_game.finished,
    )


def save_player_states(db: Session, market_game_id: int, state: MarketState) -> None:
    rows = {
        row.player_id: row
        for row in db.query(MarketPlayerState)
        .filter(MarketPlayerState.market_game_id == market_game_id)
        .all()
    }
    for pid, player in state.players.items():
        row = rows.get(pid)
        if row is None:
            row = MarketPlayerState(market_game_id=market_game_id, player_id=pid)
            db.add(row)
        row.cash = player.cash
        row.inventory = player.inventory
        row.private_signal = player.private_signal


def start_game(db: Session, game_id: int, player_ids: List[int], max_rounds: int, seed: int, include_ai: bool = True) -> MarketGame:
    all_ids = list(player_ids) + ([AI_PLAYER_ID] if include_ai else [])
    state = rules.new_game(game_id=game_id, player_ids=all_ids, max_rounds=max_rounds, seed=seed)

    market_game = MarketGame(
        game_id=game_id,
        status="active",
        round_number=state.round_number,
        max_rounds=max_rounds,
        price=state.price,
        price_history=state.price_history,
        rng_seed=seed,
        include_ai=include_ai,
        finished=False,
    )
    db.add(market_game)
    db.flush()  # need market_game.id before writing player rows

    save_player_states(db, market_game.id, state)
    db.commit()
    db.refresh(market_game)
    return market_game


def get_player_view(db: Session, market_game: MarketGame, player_id: int) -> "PlayerView":
    state = load_state(db, market_game)
    return rules.project(state, player_id)


def submit_action(db: Session, market_game: MarketGame, player_id: int, action_type: str, qty: int) -> None:
    if market_game.finished:
        raise ValueError("game finished")

    existing = (
        db.query(MarketAction)
        .filter(
            MarketAction.market_game_id == market_game.id,
            MarketAction.round_number == market_game.round_number,
            MarketAction.player_id == player_id,
        )
        .first()
    )
    if existing:
        raise ValueError("already submitted")

    state = load_state(db, market_game)
    # Validates qty against current inventory / action rules before persisting.
    rules.submit_action(state, Action(player_id=player_id, type=action_type, qty=qty))

    db.add(
        MarketAction(
            market_game_id=market_game.id,
            round_number=market_game.round_number,
            player_id=player_id,
            action_type=action_type,
            qty=qty,
        )
    )
    db.commit()


def submissions_count(db: Session, market_game: MarketGame) -> int:
    return (
        db.query(MarketAction)
        .filter(
            MarketAction.market_game_id == market_game.id,
            MarketAction.round_number == market_game.round_number,
        )
        .count()
    )


def human_player_count(db: Session, market_game: MarketGame) -> int:
    return (
        db.query(MarketPlayerState)
        .filter(
            MarketPlayerState.market_game_id == market_game.id,
            MarketPlayerState.player_id != AI_PLAYER_ID,
        )
        .count()
    )


def run_ai_turn_if_needed(db: Session, market_game: MarketGame) -> None:
    """Synchronous AI call for V1 (see strategy.py — the blocking sleep here
    is intentional and is what Phase 4's async worker replaces)."""
    if not market_game.include_ai:
        return
    already = (
        db.query(MarketAction)
        .filter(
            MarketAction.market_game_id == market_game.id,
            MarketAction.round_number == market_game.round_number,
            MarketAction.player_id == AI_PLAYER_ID,
        )
        .first()
    )
    if already:
        return

    observation = get_player_view(db, market_game, AI_PLAYER_ID)
    action = act_with_simulated_latency(observation, TrendFollowerStrategy())

    db.add(
        MarketAction(
            market_game_id=market_game.id,
            round_number=market_game.round_number,
            player_id=AI_PLAYER_ID,
            action_type=action.type,
            qty=action.qty,
        )
    )
    db.commit()


def resolve_round(db: Session, market_game: MarketGame) -> dict:
    state = load_state(db, market_game)
    event = rules.resolve_round(state, seed=market_game.rng_seed)

    save_player_states(db, market_game.id, state)

    db.add(
        MarketRoundResult(
            market_game_id=market_game.id,
            round_number=event.round_number,
            price_before=event.price_before,
            price_after=event.price_after,
            trades=event.trades,
        )
    )

    market_game.round_number = state.round_number
    market_game.price = state.price
    market_game.price_history = state.price_history
    market_game.finished = state.finished
    if state.finished:
        market_game.status = "completed"

    db.commit()

    return {
        "round_number": event.round_number,
        "price_before": event.price_before,
        "price_after": event.price_after,
        "trades": event.trades,
        "finished": state.finished,
    }


def final_scores(db: Session, market_game: MarketGame) -> List[dict]:
    state = load_state(db, market_game)
    scores = rules.final_scores(state)

    results = []
    for pid, score in scores.items():
        if pid == AI_PLAYER_ID:
            name = "AI (Trend Follower)"
        else:
            player = db.query(Player).filter(Player.id == pid).first()
            name = player.name if player else f"player_{pid}"
        results.append({"player_id": pid, "player_name": name, "score": score})

    results.sort(key=lambda r: r["score"], reverse=True)
    return results
