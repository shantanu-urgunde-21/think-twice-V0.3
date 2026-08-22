import os
import sys
import tempfile

import pytest

# Make backend modules (database, config, main, routers, ...) importable when
# pytest is run from the repo root or from backend/.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# The app reads DATABASE_URL at import time (config.py / database.py), so the
# test database must be selected before anything under backend/ is imported.
_db_fd, _DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ.setdefault("ADMIN_USERNAME", "test-admin")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    """A TestClient backed by a throwaway SQLite database for the whole test session."""
    with TestClient(app) as test_client:
        yield test_client
    os.remove(_DB_PATH)


@pytest.fixture
def make_player(client):
    """Create a unique player for a test and return their player dict."""
    counter = {"n": 0}

    def _make(name_prefix="player"):
        counter["n"] += 1
        name = f"{name_prefix}_{os.urandom(4).hex()}_{counter['n']}"
        resp = client.post("/api/players", json={"name": name, "passcode": "1234"})
        assert resp.status_code == 200, resp.text
        return resp.json()

    return _make
