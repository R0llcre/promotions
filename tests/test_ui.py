"""UI smoke tests for the `/ui` entry point.

This test file validates that the admin UI blueprint is registered and can be
served at `/ui`. It is intentionally self-contained and uses an in-memory
SQLite database so that it does not depend on PostgreSQL for this check.
"""

import os
import pytest
from service import create_app


@pytest.fixture(name="ui_client")
def _ui_client():
    """Provide a Flask test client bound to an in-memory SQLite database.

    We set DATABASE_URI to `sqlite:///:memory:` to avoid touching Postgres.
    The function name is prefixed with `_` and the fixture is registered as
    `ui_client` via the decorator to prevent pylint W0621 (redefined-outer-name)
    when the test function parameter is also named `ui_client`.
    """
    os.environ["DATABASE_URI"] = "sqlite:///:memory:"
    app = create_app()
    app.config["TESTING"] = True

    testing_client = app.test_client()
    ctx = app.app_context()
    ctx.push()

    try:
        yield testing_client
    finally:
        ctx.pop()


def test_ui_route_returns_html_and_title(ui_client):
    """Ensure `/ui` returns HTTP 200 with an HTML payload containing the title."""
    # Act
    resp = ui_client.get("/ui")

    # Assert HTTP status and content-type
    assert resp.status_code == 200
    assert "text/html" in resp.content_type

    # Assert the page renders the expected title text
    html = resp.data.decode("utf-8")
    assert "Promotions Admin" in html
