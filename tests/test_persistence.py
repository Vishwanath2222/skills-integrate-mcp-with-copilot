import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fastapi.testclient import TestClient

import app


def test_activities_persist_in_sqlite(tmp_path, monkeypatch):
    db_path = tmp_path / "activities.db"
    monkeypatch.setattr(app, "DB_PATH", db_path)

    app.init_db()

    client = TestClient(app.app)
    response = client.post("/activities/Chess Club/signup?email=newstudent@example.com")
    assert response.status_code == 200

    activities = client.get("/activities").json()
    assert "newstudent@example.com" in activities["Chess Club"]["participants"]

    app.init_db()
    activities_after_reload = client.get("/activities").json()
    assert "newstudent@example.com" in activities_after_reload["Chess Club"]["participants"]


def test_signup_respects_capacity_limit(tmp_path, monkeypatch):
    db_path = tmp_path / "activities.db"
    monkeypatch.setattr(app, "DB_PATH", db_path)

    app.init_db()

    client = TestClient(app.app)
    activity = client.get("/activities").json()["Chess Club"]
    max_participants = activity["max_participants"]
    starting_count = len(activity["participants"])

    for i in range(max_participants - starting_count):
        email = f"student{i}@example.com"
        response = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response.status_code == 200

    response = client.post("/activities/Chess Club/signup?email=overflow@example.com")
    assert response.status_code == 400
    assert "full" in response.json()["detail"].lower()
