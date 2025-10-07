# tests/test_routes_more.py
# -*- coding: utf-8 -*-

from unittest.mock import patch

from service import app as flask_app
from service.common import status
from service.models import Promotion


def test_get_empty_list_returns_200_and_empty_array():
    """GET /promotions returns an empty array and 200 when there is no record"""
    client = flask_app.test_client()

    # Must clear the table inside app_context; otherwise remove_all won't actually execute
    try:
        with flask_app.app_context():
            if hasattr(Promotion, "remove_all"):
                Promotion.remove_all()
    except Exception:  # noqa: BLE001
        # If remove_all is not implemented, don't fail the test
        pass

    resp = client.get("/promotions")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_update_nonexistent_returns_404():
    """Updating a non-existent id should return 404"""
    client = flask_app.test_client()
    payload = {
        "name": "Updated",
        "promotion_type": "Discount",
        "value": 10,
        "product_id": 1,
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
    }
    resp = client.put("/promotions/999999", json=payload)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_delete_nonexistent_returns_404():
    """Deleting a non-existent id should return 404"""
    client = flask_app.test_client()
    resp = client.delete("/promotions/999999")
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_internal_server_error_returns_json():
    """Trigger a 500 to cover JSON 500 handler using a patched model method.

    We patch Promotion.find to raise RuntimeError so the error_handlers 500 branch
    is exercised without dynamically adding routes at runtime.

    NOTE: Temporarily disable exception propagation (TESTING / PROPAGATE_EXCEPTIONS)
    so Flask returns 500 instead of re-raising to the test process.
    """
    client = flask_app.test_client()

    prev_testing = flask_app.testing
    prev_propagate = flask_app.config.get("PROPAGATE_EXCEPTIONS", None)
    flask_app.testing = False
    flask_app.config["PROPAGATE_EXCEPTIONS"] = False

    try:
        with patch.object(Promotion, "find", side_effect=RuntimeError("kaboom")):
            resp = client.get("/promotions/1")
            assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = resp.get_json()
            assert isinstance(data, dict)
            assert any(k in data for k in {"error", "message", "status", "code"})
    finally:
        flask_app.testing = prev_testing
        if prev_propagate is None:
            flask_app.config.pop("PROPAGATE_EXCEPTIONS", None)
        else:
            flask_app.config["PROPAGATE_EXCEPTIONS"] = prev_propagate


# ------- Additional filter cases to increase coverage -------

def _mk(client, **override):
    """Create a valid Promotion and return its id"""
    data = {
        "name": "BF",
        "promotion_type": "Discount",
        "value": 50,
        "product_id": 123,
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
    }
    data.update(override)
    r = client.post("/promotions", json=data)
    assert r.status_code == status.HTTP_201_CREATED
    return r.get_json()["id"]


def test_list_filter_by_name_no_match():
    """GET /promotions?name=... with no match should return empty array"""
    client = flask_app.test_client()
    # Ensure there is at least one non-matching record
    _mk(client, name="SomethingElse")

    resp = client.get("/promotions", query_string={"name": "NotExistName"})
    assert resp.status_code == status.HTTP_200_OK
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_list_filter_by_name_match():
    """GET /promotions?name=... with a match should include that item"""
    client = flask_app.test_client()
    target_name = "FilterMe"
    pid = _mk(client, name=target_name)

    resp = client.get("/promotions", query_string={"name": target_name})
    assert resp.status_code == status.HTTP_200_OK
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1
    ids = {item["id"] for item in data}
    assert pid in ids
