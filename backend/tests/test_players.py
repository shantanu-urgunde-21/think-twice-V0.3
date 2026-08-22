def test_create_player(client, make_player):
    player = make_player("alice")
    assert player["name"].startswith("alice_")
    assert player["total_score"] == 0


def test_duplicate_name_without_passcode_is_rejected(client):
    resp1 = client.post("/api/players", json={"name": "bob_dup", "passcode": "1111"})
    assert resp1.status_code == 200

    resp2 = client.post("/api/players", json={"name": "bob_dup"})
    assert resp2.status_code == 400


def test_duplicate_name_with_correct_passcode_logs_in(client):
    resp1 = client.post("/api/players", json={"name": "carol_dup", "passcode": "2222"})
    assert resp1.status_code == 200
    player_id = resp1.json()["id"]

    resp2 = client.post("/api/players", json={"name": "carol_dup", "passcode": "2222"})
    assert resp2.status_code == 200
    assert resp2.json()["id"] == player_id


def test_verify_player_wrong_passcode_is_rejected(client):
    client.post("/api/players", json={"name": "dave_verify", "passcode": "3333"})

    resp = client.post(
        "/api/players/verify", json={"name": "dave_verify", "passcode": "0000"}
    )
    assert resp.status_code == 401


def test_verify_player_correct_passcode_succeeds(client):
    client.post("/api/players", json={"name": "erin_verify", "passcode": "4444"})

    resp = client.post(
        "/api/players/verify", json={"name": "erin_verify", "passcode": "4444"}
    )
    assert resp.status_code == 200


def test_verify_unknown_player_is_not_found(client):
    resp = client.post(
        "/api/players/verify", json={"name": "does_not_exist_xyz", "passcode": "0000"}
    )
    assert resp.status_code == 404


def test_get_players_returns_a_list(client, make_player):
    make_player("frank")
    resp = client.get("/api/players")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


def test_get_single_player(client, make_player):
    player = make_player("grace")
    resp = client.get(f"/api/players/{player['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == player["id"]


def test_get_unknown_player_is_not_found(client):
    resp = client.get("/api/players/999999")
    assert resp.status_code == 404


def test_leaderboard_returns_a_list(client, make_player):
    make_player("henry")
    resp = client.get("/api/leaderboard")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
