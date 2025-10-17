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
Promotion API Service Test Suite (focused on Issue #24: query by promotion_type)
"""

import os
import logging
from http import HTTPStatus as S
from unittest import TestCase

from wsgi import app
from service.common import status
from service.models import Promotion, db

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

    def test_query_promotion_type_blank(self):
        """It should return 200 and [] when ?promotion_type= is blank (only spaces)"""
        # Arrange: prepare some promotions that should NOT be returned
        self.client.post(
            BASE_URL,
            json=make_payload(
                name="X",
                promotion_type="SomeType",
            ),
        )
        # Act: blank param (spaces)
        resp = self.client.get(f"{BASE_URL}?promotion_type=   ")
        # Assert
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

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


# ---------------------- Extra coverage to reach >=95% ----------------------


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


def test_method_not_allowed_returns_json():
    """It should return JSON 405 for wrong method on /promotions/<id>"""
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
