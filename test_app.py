import pytest
from app import app, init_db


@pytest.fixture()
def client(tmp_path):
    app.config["TESTING"] = True
    app.config["DATABASE"] = str(tmp_path / "test.db")
    init_db()
    with app.test_client() as client:
        yield client


def test_dashboard(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"TaskFlow" in response.data


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "healthy"


def test_create_task(client):
    response = client.post("/tasks", data={
        "title": "Build CI pipeline",
        "description": "Automate testing",
        "priority": "High",
        "due_date": "2026-11-01"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Build CI pipeline" in response.data


def test_empty_title_rejected(client):
    response = client.post("/tasks", data={
        "title": "  ", "priority": "Low"
    }, follow_redirects=True)
    assert b"Enter a valid title" in response.data


def test_update_status(client):
    client.post("/tasks", data={"title": "Test task", "priority": "Medium"})
    response = client.post(
        "/tasks/1/status", data={"status": "Done"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Done" in response.data


def test_delete_task(client):
    client.post("/tasks", data={"title": "Temporary", "priority": "Low"})
    response = client.post("/tasks/1/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"Temporary" not in response.data


def test_search(client):
    client.post("/tasks", data={
        "title": "GitHub Actions setup", "priority": "High"
    })
    response = client.get("/?q=GitHub")
    assert b"GitHub Actions setup" in response.data
