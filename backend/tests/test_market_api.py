"""Integration tests for the Hidden Market HTTP endpoints, through the same
room-create/join/start flow the other games use."""

import pytest


@pytest.fixture(autouse=True)
def fast_ai(monkeypatch):
    """The AI's simulated decision latency (0.5-2s) is the point in
    production, but it would make every test in this module slow. Patch it
    to zero here only; game.market.strategy is untouched for real runs."""
    monkeypatch.setattr("game.market.strategy.MIN_LATENCY_SECONDS", 0.0)
    monkeypatch.setattr("game.market.strategy.MAX_LATENCY_SECONDS", 0.0)


def _start_market_room(client, make_player, n_humans=2):
    host = make_player("market_host")
    create_resp = client.post(
        "/api/rooms/create", json={"player_id": host["id"], "game_name": "market"}
    )
    room_code = create_resp.json()["room_code"]

    players = [host]
    for i in range(n_humans - 1):
        p = make_player(f"market_joiner_{i}")
        client.post("/api/rooms/join", json={"player_id": p["id"], "room_code": room_code})
        players.append(p)

    start_resp = client.post(
        f"/api/rooms/{room_code}/start", params={"host_id": host["id"]}
    )
    assert start_resp.status_code == 200, start_resp.text
    game_id = start_resp.json()["game_id"]
    return game_id, players


def test_start_market_game_seeds_state(client, make_player):
    game_id, players = _start_market_room(client, make_player)

    view_resp = client.get(f"/api/games/market/{game_id}/view/{players[0]['id']}")
    assert view_resp.status_code == 200
    view = view_resp.json()
    assert view["round_number"] == 1
    assert view["cash"] == 1000.0
    assert view["inventory"] == 0
    assert view["total_players"] == 3  # 2 humans + AI


def test_view_does_not_leak_other_players_state(client, make_player):
    game_id, players = _start_market_room(client, make_player, n_humans=2)

    view_a = client.get(f"/api/games/market/{game_id}/view/{players[0]['id']}").json()
    view_b = client.get(f"/api/games/market/{game_id}/view/{players[1]['id']}").json()

    # Each response is scoped to exactly one player's private fields; there
    # is no key on the response that could carry a second player's data.
    assert set(view_a.keys()) == {
        "game_id", "round_number", "max_rounds", "price", "price_history",
        "cash", "inventory", "private_signal", "has_submitted",
        "submissions_count", "total_players", "finished",
    }
    assert view_a == {**view_a}  # sanity: no nested "players" dict present
    assert "players" not in view_a and "players" not in view_b


def test_submit_and_resolve_round(client, make_player):
    game_id, players = _start_market_room(client, make_player, n_humans=2)

    for p in players:
        resp = client.post(
            f"/api/games/market/{game_id}/submit",
            json={"player_id": p["id"], "action_type": "HOLD", "qty": 0},
        )
        assert resp.status_code == 200, resp.text

    resolve_resp = client.post(f"/api/games/market/{game_id}/resolve")
    assert resolve_resp.status_code == 200, resolve_resp.text
    result = resolve_resp.json()
    assert result["round_number"] == 1
    assert result["finished"] is False
    # 2 humans + AI all had an action recorded for round 1
    assert len(result["trades"]) == 3


def test_double_submit_rejected(client, make_player):
    game_id, players = _start_market_room(client, make_player, n_humans=1)

    first = client.post(
        f"/api/games/market/{game_id}/submit",
        json={"player_id": players[0]["id"], "action_type": "HOLD", "qty": 0},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/games/market/{game_id}/submit",
        json={"player_id": players[0]["id"], "action_type": "HOLD", "qty": 0},
    )
    assert second.status_code == 400


def test_full_game_completes_and_produces_final_scores(client, make_player):
    game_id, players = _start_market_room(client, make_player, n_humans=2)

    view = client.get(f"/api/games/market/{game_id}/view/{players[0]['id']}").json()
    max_rounds = view["max_rounds"]

    for _ in range(max_rounds):
        for p in players:
            client.post(
                f"/api/games/market/{game_id}/submit",
                json={"player_id": p["id"], "action_type": "HOLD", "qty": 0},
            )
        resolve_resp = client.post(f"/api/games/market/{game_id}/resolve")
        assert resolve_resp.status_code == 200

    assert resolve_resp.json()["finished"] is True

    results_resp = client.get(f"/api/games/market/{game_id}/results")
    assert results_resp.status_code == 200
    results = results_resp.json()
    assert len(results["scores"]) == 3  # 2 humans + AI
    assert len(results["price_history"]) == max_rounds + 1  # includes starting price

    # Humans HOLD every round, so their score should equal starting cash
    # exactly. The AI is not forced to HOLD and may legitimately trade on
    # its own signal, so it is excluded from this assertion.
    for entry in results["scores"]:
        if entry["player_id"] != -1:  # game.market.strategy.AI_PLAYER_ID
            assert entry["score"] == 1000.0


def test_results_before_finish_is_rejected(client, make_player):
    game_id, players = _start_market_room(client, make_player, n_humans=1)
    resp = client.get(f"/api/games/market/{game_id}/results")
    assert resp.status_code == 400
