# tests/test_ui.py
import os
import pytest
from service import create_app

@pytest.fixture
def client():
    """
    Lightweight test client that points SQLAlchemy at an in-memory SQLite
    so we don't require Postgres for this UI test.
    """
    os.environ["DATABASE_URI"] = "sqlite:///:memory:"
    app = create_app()
    app.config["TESTING"] = True
    testing_client = app.test_client()
    ctx = app.app_context()
    ctx.push()
    yield testing_client
    ctx.pop()

def test_ui_route_returns_html_and_title(client):
    # Act
    resp = client.get("/ui")

    # Assert HTTP status and content-type
    assert resp.status_code == 200
    assert "text/html" in resp.content_type

    # Assert the page renders the expected title text
    html = resp.data.decode("utf-8")
    assert "Promotions Admin" in html
