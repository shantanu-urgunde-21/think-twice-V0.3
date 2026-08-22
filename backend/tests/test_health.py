def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Game Theory Platform API"


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


def test_stats_endpoint(client):
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert "total_players" in body
    assert "max_players" in body
    assert "active_games" in body
