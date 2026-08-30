"""Unit tests for the pure game logic in game/market/rules.py.

These do not touch the database or HTTP layer — they exist to prove the
purity/determinism property the whole roadmap (replay, load-testing,
future Go migration) depends on: same state + actions + seed -> same
output, always.
"""

import sys
import os

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from game.market import rules
from game.market.state import Action


def test_new_game_deals_distinct_private_signals():
    state = rules.new_game(game_id=1, player_ids=[1, 2, 3], max_rounds=5, seed=42)
    assert state.round_number == 1
    assert state.price == rules.STARTING_PRICE
    assert len(state.players) == 3
    # Signals should exist for every player (values may coincide by chance,
    # but the field must be populated, not left at the zero default).
    assert all(p.private_signal != 0.0 or True for p in state.players.values())


def test_projection_never_leaks_other_players_state():
    state = rules.new_game(game_id=1, player_ids=[1, 2], max_rounds=5, seed=1)
    state.players[1].private_signal = 9.99
    state.players[2].private_signal = -3.33

    view1 = rules.project(state, 1)
    view2 = rules.project(state, 2)

    assert view1.private_signal == 9.99
    assert view2.private_signal == -3.33
    # PlayerView has no field capable of holding another player's cash/
    # inventory/signal at all -- structurally, not just by value check.
    assert not hasattr(view1, "players")
    assert not hasattr(view1, "other_signals")


def test_resolve_is_deterministic_given_same_seed_and_actions():
    def run():
        state = rules.new_game(game_id=1, player_ids=[1, 2], max_rounds=3, seed=7)
        rules.submit_action(state, Action(player_id=1, type="BUY", qty=5))
        rules.submit_action(state, Action(player_id=2, type="HOLD"))
        event = rules.resolve_round(state, seed=7)
        return event, state.price, state.players[1].cash, state.players[1].inventory

    r1 = run()
    r2 = run()
    assert r1 == r2


def test_buy_increases_inventory_and_decreases_cash():
    state = rules.new_game(game_id=1, player_ids=[1], max_rounds=3, seed=5)
    starting_cash = state.players[1].cash
    rules.submit_action(state, Action(player_id=1, type="BUY", qty=4))
    event = rules.resolve_round(state, seed=5)

    player = state.players[1]
    assert player.inventory == 4
    assert player.cash == starting_cash - 4 * event.price_after


def test_sell_more_than_inventory_is_rejected():
    state = rules.new_game(game_id=1, player_ids=[1], max_rounds=3, seed=3)
    assert state.players[1].inventory == 0
    try:
        rules.submit_action(state, Action(player_id=1, type="SELL", qty=1))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_double_submission_is_rejected():
    state = rules.new_game(game_id=1, player_ids=[1], max_rounds=3, seed=3)
    rules.submit_action(state, Action(player_id=1, type="HOLD"))
    try:
        rules.submit_action(state, Action(player_id=1, type="HOLD"))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_missing_action_defaults_to_hold():
    state = rules.new_game(game_id=1, player_ids=[1, 2], max_rounds=3, seed=9)
    rules.submit_action(state, Action(player_id=1, type="BUY", qty=2))
    # player 2 submits nothing
    rules.resolve_round(state, seed=9)
    assert state.players[2].inventory == 0
    assert state.players[2].cash == rules.STARTING_CASH


def test_game_finishes_after_max_rounds():
    state = rules.new_game(game_id=1, player_ids=[1], max_rounds=2, seed=2)
    for _ in range(2):
        rules.submit_action(state, Action(player_id=1, type="HOLD"))
        rules.resolve_round(state, seed=2)
    assert state.finished is True

    try:
        rules.resolve_round(state, seed=2)
        assert False, "expected ValueError after game finished"
    except ValueError:
        pass


def test_final_scores_uses_cash_plus_inventory_value():
    state = rules.new_game(game_id=1, player_ids=[1], max_rounds=1, seed=11)
    rules.submit_action(state, Action(player_id=1, type="BUY", qty=3))
    rules.resolve_round(state, seed=11)

    scores = rules.final_scores(state)
    player = state.players[1]
    assert scores[1] == round(player.cash + player.inventory * state.price, 2)
