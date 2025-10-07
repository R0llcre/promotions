# tests/test_routes_crud_extra.py
# Extra route coverage tests: GET / LIST / PUT / DELETE / 405

from service.common import status
from service import create_app
from service.models import Promotion

# Each module creates its own app instance to avoid interference with course tests
flask_app = create_app()


def setup_function():
    """Clear the database before each test"""
    if hasattr(Promotion, "remove_all"):
        with flask_app.app_context():
            Promotion.remove_all()
    elif hasattr(Promotion, "reset"):
        with flask_app.app_context():
            Promotion.reset()


def _mk(client, **override):
    """Create a valid Promotion and return its ID"""
    data = {
        "name": "BF",
        "promotion_type": "Discount",
        "value": 50,
        "product_id": 123,
        # Your models.deserialize requires date fields:
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
    }
    data.update(override)
    resp = client.post("/promotions", json=data)
    assert resp.status_code == status.HTTP_201_CREATED
    payload = resp.get_json()
    assert "id" in payload
    return payload["id"]


def test_get_promotion_after_create():
    """Verify retrieving a created promotion"""
    client = flask_app.test_client()
    pid = _mk(client)
    r = client.get(f"/promotions/{pid}")
    assert r.status_code == status.HTTP_200_OK
    body = r.get_json()
    assert body["id"] == pid and body["name"] == "BF"


def test_list_promotions_returns_array_and_counts():
    """GET /promotions should return an array of promotions"""
    client = flask_app.test_client()
    _ = _mk(client)
    _ = _mk(client, name="X")
    r = client.get("/promotions")
    assert r.status_code == status.HTTP_200_OK
    body = r.get_json()
    assert isinstance(body, list) and len(body) >= 2


def test_update_promotion_changes_fields():
    """PUT /promotions/<id> should update fields"""
    client = flask_app.test_client()
    pid = _mk(client)
    # Your deserialize performs a full update; all required fields (including dates) must be provided
    r = client.put(
        f"/promotions/{pid}",
        json={
            "name": "Updated",
            "promotion_type": "Discount",
            "value": 99,
            "product_id": 123,
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        },
    )
    assert r.status_code == status.HTTP_200_OK
    body = r.get_json()
    assert body["name"] == "Updated" and float(body["value"]) == 99.0


def test_delete_then_get_404():
    """DELETE /promotions/<id> should remove the record"""
    client = flask_app.test_client()
    pid = _mk(client)
    r = client.delete(f"/promotions/{pid}")
    assert r.status_code == status.HTTP_204_NO_CONTENT
    r = client.get(f"/promotions/{pid}")
    assert r.status_code == status.HTTP_404_NOT_FOUND


def test_method_not_allowed_returns_json():
    """Trigger 405 Method Not Allowed to cover JSON error handling"""
    client = flask_app.test_client()
    r = client.put("/promotions")  # PUT /promotions is not defined → should return 405
    assert r.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    body = r.get_json()
    assert "error" in body and "message" in body
