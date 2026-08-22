def test_create_room(client, make_player):
    host = make_player("host")

    resp = client.post(
        "/api/rooms/create", json={"player_id": host["id"], "game_name": "two_thirds"}
    )
    assert resp.status_code == 200
    room = resp.json()
    assert len(room["room_code"]) == 4
    assert room["host_id"] == host["id"]
    assert room["status"] == "waiting"
    assert len(room["members"]) == 1


def test_create_room_with_unknown_player_is_not_found(client):
    resp = client.post(
        "/api/rooms/create", json={"player_id": 999999, "game_name": "two_thirds"}
    )
    assert resp.status_code == 404


def test_join_room(client, make_player):
    host = make_player("host2")
    create_resp = client.post(
        "/api/rooms/create", json={"player_id": host["id"], "game_name": "two_thirds"}
    )
    room_code = create_resp.json()["room_code"]

    joiner = make_player("joiner")
    join_resp = client.post(
        "/api/rooms/join", json={"player_id": joiner["id"], "room_code": room_code}
    )
    assert join_resp.status_code == 200
    assert len(join_resp.json()["members"]) == 2


def test_join_nonexistent_room_is_not_found(client, make_player):
    player = make_player("lonely")
    resp = client.post(
        "/api/rooms/join", json={"player_id": player["id"], "room_code": "ZZZZ"}
    )
    assert resp.status_code == 404


def test_join_full_room_is_rejected(client, make_player):
    host = make_player("cap_host")
    create_resp = client.post(
        "/api/rooms/create",
        json={"player_id": host["id"], "game_name": "two_thirds", "max_players": 1},
    )
    room_code = create_resp.json()["room_code"]

    joiner = make_player("cap_joiner")
    resp = client.post(
        "/api/rooms/join", json={"player_id": joiner["id"], "room_code": room_code}
    )
    assert resp.status_code == 400


def test_toggle_ready(client, make_player):
    host = make_player("ready_host")
    create_resp = client.post(
        "/api/rooms/create", json={"player_id": host["id"], "game_name": "two_thirds"}
    )
    room_code = create_resp.json()["room_code"]

    resp = client.post(
        f"/api/rooms/{room_code}/ready",
        params={"player_id": host["id"], "is_ready": False},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_start_room_requires_host(client, make_player):
    host = make_player("start_host")
    create_resp = client.post(
        "/api/rooms/create", json={"player_id": host["id"], "game_name": "two_thirds"}
    )
    room_code = create_resp.json()["room_code"]

    not_host = make_player("not_the_host")
    resp = client.post(
        f"/api/rooms/{room_code}/start", params={"host_id": not_host["id"]}
    )
    assert resp.status_code == 403
