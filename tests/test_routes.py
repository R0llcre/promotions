######################################################################
# Copyright 2016, 2024 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
######################################################################

"""
Promotion API Service Test Suite
"""

import os
import logging
from http import HTTPStatus as S
from unittest import TestCase
from unittest.mock import patch
from datetime import date, timedelta

from wsgi import app
from service.common import status
from service.models import Promotion, db, DataValidationError

# Use the same env var as the app for tests; default to local Postgres test DB
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
)
BASE_URL = "/promotions"


def make_payload(**overrides) -> dict:
    """Build a valid promotion JSON payload"""
    base = {
        "name": "NYU Demo",
        "promotion_type": "AMOUNT_OFF",
        "value": 10,
        "product_id": 123,
        "start_date": "2025-10-01",
        "end_date": "2025-10-31",
    }
    base.update(overrides)
    return base


######################################################################
#  H A P P Y   P A T H S
######################################################################
class TestPromotionService(TestCase):
    """REST API Server Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        # clean DB between tests
        db.session.query(Promotion).delete()
        db.session.commit()

    def tearDown(self):
        """Runs after each test"""
        db.session.remove()

    # ---------- Home ----------
    def test_index(self):
        """It should call the home page"""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["name"], "Promotions Service")
        self.assertEqual(data["version"], "1.0.0")
        self.assertIn("promotions", data["paths"])

    # ---------- Create ----------
    def test_create_promotion(self):
        """It should Create a new Promotion"""
        payload = make_payload()
        resp = self.client.post(BASE_URL, json=payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Location header
        location = resp.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check body
        body = resp.get_json()
        self.assertEqual(body["name"], payload["name"])
        self.assertEqual(body["promotion_type"], payload["promotion_type"])
        self.assertEqual(body["value"], payload["value"])
        self.assertEqual(body["product_id"], payload["product_id"])

        # Follow the Location
        follow = self.client.get(location)
        self.assertEqual(follow.status_code, status.HTTP_200_OK)
        again = follow.get_json()
        self.assertEqual(again["name"], payload["name"])

    # ---------- Query by promotion_type ----------
    def test_query_by_promotion_type_returns_matches(self):
        """It should return only promotions with the given promotion_type (exact match)"""
        # Arrange: two types
        self.client.post(
            BASE_URL,
            json=make_payload(
                name="Percent10",
                promotion_type="Percentage off",
                value=10,
            ),
        )
        self.client.post(
            BASE_URL,
            json=make_payload(
                name="BOGO",
                promotion_type="Buy One Get One",
                value=100,
            ),
        )

        # Act
        resp = self.client.get(f"{BASE_URL}?promotion_type=Buy One Get One")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()

        # Assert: only BOGO
        self.assertTrue(isinstance(data, list))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["promotion_type"], "Buy One Get One")
        self.assertEqual(data[0]["name"], "BOGO")

    def test_query_by_promotion_type_returns_empty_when_no_match(self):
        """It should return 200 and empty list when no promotions match"""
        # Arrange: create other type
        self.client.post(
            BASE_URL,
            json=make_payload(
                name="Percent10",
                promotion_type="Percentage off",
                value=10,
            ),
        )

        # Act
        resp = self.client.get(f"{BASE_URL}?promotion_type=Nonexistent Type")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

    # ---------- Extra filters to cover branches in routes ----------
    def test_list_promotions_filter_by_name(self):
        """It should filter promotions by ?name=..."""
        self.client.post(BASE_URL, json=make_payload(name="OnlyMe", product_id=10))
        self.client.post(BASE_URL, json=make_payload(name="Other", product_id=11))
        resp = self.client.get(f"{BASE_URL}?name=OnlyMe")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "OnlyMe")

    def test_list_promotions_filter_by_product_id(self):
        """It should filter promotions by ?product_id=..."""
        self.client.post(BASE_URL, json=make_payload(name="A", product_id=2222))
        self.client.post(BASE_URL, json=make_payload(name="B", product_id=3333))
        resp = self.client.get(f"{BASE_URL}?product_id=2222")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["product_id"], 2222)

    def test_list_promotions_filter_by_id_found_and_not_found(self):
        """It should filter by ?id=... returning [one] or []"""
        created = self.client.post(BASE_URL, json=make_payload(name="Single", product_id=555))
        self.assertEqual(created.status_code, 201)
        pid = created.get_json()["id"]

        resp = self.client.get(f"{BASE_URL}?id={pid}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], pid)

        resp2 = self.client.get(f"{BASE_URL}?id=99999999")
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.get_json(), [])

    # ---------- Delete ----------
    def test_delete_promotion_happy_path(self):
        """It should delete an existing Promotion and return 204"""
        # create one
        created = self.client.post(BASE_URL, json=make_payload())
        self.assertEqual(created.status_code, S.CREATED)
        pid = created.get_json()["id"]

        # delete it
        resp = self.client.delete(f"{BASE_URL}/{pid}")
        self.assertEqual(resp.status_code, S.NO_CONTENT)
        self.assertEqual(resp.data, b"")

        # verify gone
        self.assertEqual(self.client.get(f"{BASE_URL}/{pid}").status_code, S.NOT_FOUND)

    def test_query_active_returns_only_current_promotions(self):
        """It should return only promotions that are active today when ?active=true"""
        today = date.today()

        # Active: past -> future
        self.client.post(BASE_URL, json=make_payload(
            name="ActiveNow",
            start_date=(today - timedelta(days=2)).isoformat(),
            end_date=(today + timedelta(days=2)).isoformat(),
        ))

        # Expired: past -> yesterday
        self.client.post(BASE_URL, json=make_payload(
            name="Expired",
            start_date=(today - timedelta(days=10)).isoformat(),
            end_date=(today - timedelta(days=1)).isoformat(),
        ))

        # Future: tomorrow -> future
        self.client.post(BASE_URL, json=make_payload(
            name="Future",
            start_date=(today + timedelta(days=1)).isoformat(),
            end_date=(today + timedelta(days=10)).isoformat(),
        ))

        resp = self.client.get(f"{BASE_URL}?active=true")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()

        # Only the active one should be returned
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "ActiveNow")

    def test_deactivate_promotion_sets_end_date_to_yesterday_and_excludes_from_active(self):
        """It should set end_date to yesterday and immediately exclude it from ?active=true"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Preparation: create a promotion that ends in the future (currently active)
        created = self.client.post(
            BASE_URL,
            json=make_payload(
                name="ToDeactivate",
                start_date=(today - timedelta(days=5)).isoformat(),
                end_date=(today + timedelta(days=5)).isoformat(),
            ),
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        pid = created.get_json()["id"]

        # Action: deactivate the promotion
        resp = self.client.put(f"{BASE_URL}/{pid}/deactivate")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.get_json()
        self.assertEqual(body["id"], pid)
        self.assertEqual(body["end_date"], yesterday.isoformat())

        # Verification: it should no longer appear in the active promotions list
        active_resp = self.client.get(f"{BASE_URL}?active=true")
        self.assertEqual(active_resp.status_code, status.HTTP_200_OK)
        active_list = active_resp.get_json()
        self.assertTrue(all(p["id"] != pid for p in active_list))

    def test_deactivate_is_idempotent_and_never_extends(self):
        """Deactivating twice does not push end_date forward; deactivating an already expired promo won't extend it"""
        today = date.today()
        yesterday = today - timedelta(days=1)
        much_earlier = today - timedelta(days=10)

        # Case 1: Created with a future end date → first deactivation sets it to yesterday;
        # a second deactivation keeps it at yesterday (it should NOT be pushed to a “new yesterday”)
        created = self.client.post(
            BASE_URL,
            json=make_payload(
                name="WillDeactivateTwice",
                start_date=(today - timedelta(days=5)).isoformat(),
                end_date=(today + timedelta(days=5)).isoformat(),
            ),
        )
        pid = created.get_json()["id"]

        self.client.put(f"{BASE_URL}/{pid}/deactivate")
        body1 = self.client.get(f"{BASE_URL}/{pid}").get_json()
        self.assertEqual(body1["end_date"], yesterday.isoformat())

        self.client.put(f"{BASE_URL}/{pid}/deactivate")
        body2 = self.client.get(f"{BASE_URL}/{pid}").get_json()
        self.assertEqual(body2["end_date"], yesterday.isoformat())

        # Case 2: Promotion that already expired earlier → deactivation should NOT move end_date to yesterday
        # (prevents “extending history”)
        created2 = self.client.post(
            BASE_URL,
            json=make_payload(
                name="AlreadyExpired",
                start_date=(today - timedelta(days=20)).isoformat(),
                end_date=much_earlier.isoformat(),
            ),
        )
        pid2 = created2.get_json()["id"]
        self.client.put(f"{BASE_URL}/{pid2}/deactivate")
        body3 = self.client.get(f"{BASE_URL}/{pid2}").get_json()
        self.assertEqual(body3["end_date"], much_earlier.isoformat())


######################################################################
#  S A D   P A T H S
######################################################################
class TestSadPaths(TestCase):
    """Test REST Exception Handling"""

    def setUp(self):
        self.client = app.test_client()

    # missing data
    def test_create_promotion_no_data(self):
        """It should not Create a Promotion with missing data"""
        resp = self.client.post(BASE_URL, json={})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # no / wrong content type
    def test_create_promotion_no_content_type(self):
        """It should not Create a Promotion with no content type"""
        resp = self.client.post(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_promotion_wrong_content_type(self):
        """It should not Create a Promotion with the wrong content type"""
        resp = self.client.post(BASE_URL, data="hello", content_type="text/html")
        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    # bad integer fields
    def test_create_promotion_bad_value(self):
        """It should not Create a Promotion with bad value data"""
        resp = self.client.post(BASE_URL, json=make_payload(value="bad_value"))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_promotion_bad_product_id(self):
        """It should not Create a Promotion with bad product_id data"""
        resp = self.client.post(BASE_URL, json=make_payload(product_id="not_a_number"))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # delete not found
    def test_delete_promotion_not_found(self):
        """It should return 404 when deleting a non-existent Promotion"""
        resp = self.client.delete(f"{BASE_URL}/999999")
        self.assertEqual(resp.status_code, S.NOT_FOUND)

    def test_deactivate_promotion_not_found(self):
        """It should return 404 when trying to deactivate a non-existent Promotion"""
        resp = self.client.put(f"{BASE_URL}/999999/deactivate")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    @patch("service.routes.Promotion.update", side_effect=DataValidationError("boom"))
    def test_deactivate_promotion_update_error_returns_400(self, _mock_update):
        """
        Return 400 when deactivate triggers DataValidationError from Promotion.update().
        """
        today = date.today()
        # Preparation: create a promotion that is currently active
        created = self.client.post(
            BASE_URL,
            json=make_payload(
                start_date=(today - timedelta(days=1)).isoformat(),
                end_date=(today + timedelta(days=1)).isoformat(),
            ),
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        pid = created.get_json()["id"]
        # During deactivation, simulate update raising DataValidationError -> should return 400
        resp = self.client.put(f"{BASE_URL}/{pid}/deactivate")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        body = resp.get_json()
        self.assertIsInstance(body, dict)


def test_update_promotion_success():
    """It should Update an existing Promotion (200)"""
    client = app.test_client()

    # create one
    payload = {
        "name": "Promo A",
        "promotion_type": "Percentage off",
        "value": 10,
        "product_id": 111,
        "start_date": "2025-10-01",
        "end_date": "2025-10-31",
    }
    created = client.post("/promotions", json=payload)
    assert created.status_code == 201
    pid = created.get_json()["id"]

    # update it
    payload["name"] = "Promo A+"
    resp = client.put(f"/promotions/{pid}", json=payload)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["name"] == "Promo A+"


def test_update_promotion_not_found():
    """It should return 404 when updating a non-existent Promotion"""
    client = app.test_client()

    payload = {
        "name": "Ghost",
        "promotion_type": "Percentage off",
        "value": 5,
        "product_id": 222,
        "start_date": "2025-10-01",
        "end_date": "2025-10-31",
    }
    resp = client.put("/promotions/999999", json=payload)
    assert resp.status_code == 404
    data = resp.get_json()
    assert isinstance(data, dict)


def test_update_promotion_id_mismatch_returns_400():
    """It should return 400 when body.id != path id"""
    client = app.test_client()
    created = client.post("/promotions", json={
        "name": "Mismatch", "promotion_type": "X", "value": 1, "product_id": 9,
        "start_date": "2025-10-01", "end_date": "2025-10-31",
    })
    assert created.status_code == 201
    pid = created.get_json()["id"]

    payload = {
        "id": pid + 1,  # mismatch on purpose
        "name": "Mismatch", "promotion_type": "X", "value": 1, "product_id": 9,
        "start_date": "2025-10-01", "end_date": "2025-10-31",
    }
    resp = client.put(f"/promotions/{pid}", json=payload)
    assert resp.status_code == 400


def test_list_promotions_all_returns_list():
    """It should list all promotions when no query params are given"""
    client = app.test_client()

    # ensure at least 2 items
    a = {
        "name": "ListA",
        "promotion_type": "TypeA",
        "value": 1,
        "product_id": 1,
        "start_date": "2025-10-01",
        "end_date": "2025-10-31",
    }
    b = {
        "name": "ListB",
        "promotion_type": "TypeB",
        "value": 2,
        "product_id": 2,
        "start_date": "2025-10-01",
        "end_date": "2025-10-31",
    }
    client.post("/promotions", json=a)
    client.post("/promotions", json=b)

    resp = client.get("/promotions")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) >= 2


def test_query_promotion_type_405_on_wrong_method_root():
    """It should return JSON 405 for wrong method on /promotions (PATCH not allowed)"""
    client = app.test_client()
    resp = client.patch("/promotions", json={"x": 1})
    assert resp.status_code == 405
    data = resp.get_json()
    assert isinstance(data, dict)  # our JSON error handler


def test_method_not_allowed_returns_json_on_item():
    """It should return JSON 405 for wrong method on /promotions/<id> (POST not allowed)"""
    client = app.test_client()
    resp = client.post("/promotions/1")  # POST not allowed here
    assert resp.status_code == 405
    data = resp.get_json()
    assert isinstance(data, dict)  # our JSON error handler


def test_not_found_returns_json():
    """It should return JSON 404 for unknown routes"""
    client = app.test_client()
    resp = client.get("/no-such-route")
    assert resp.status_code == 404
    data = resp.get_json()
    assert isinstance(data, dict)  # our JSON error handler


def test_internal_server_error_returns_json():
    """It should return JSON 500 when an unhandled exception occurs"""
    client = app.test_client()
    # In testing mode Flask propagates exceptions; disable propagation for this test
    prev = app.config.get("PROPAGATE_EXCEPTIONS", None)
    app.config["PROPAGATE_EXCEPTIONS"] = False
    try:
        with patch("service.routes.Promotion.find", side_effect=Exception("boom")):
            resp = client.get("/promotions/1")
        assert resp.status_code == 500
        data = resp.get_json()
        assert isinstance(data, dict)
    finally:
        # restore previous config
        if prev is None:
            app.config.pop("PROPAGATE_EXCEPTIONS", None)
        else:
            app.config["PROPAGATE_EXCEPTIONS"] = prev
