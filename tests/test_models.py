######################################################################
# Copyright 2016, 2024 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################

"""
Test cases for Promotion Model
"""

# pylint: disable=duplicate-code
import os
import logging
from unittest import TestCase
from datetime import date
from wsgi import app
from service.models import Promotion, DataValidationError, db
from tests.factories import PromotionFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
)

######################################################################
#  B A S E   T E S T   C A S E S
######################################################################


class TestCaseBase(TestCase):
    """Base Test Case for common setup"""

    # pylint: disable=duplicate-code
    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Promotion).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

######################################################################
#  P R O M O T I O N   M O D E L   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods


class TestPromotionModel(TestCaseBase):
    """Test Cases for Promotion Model"""

    def test_delete_a_promotion(self):
        """It should Delete a Promotion"""
        promotion = PromotionFactory()
        promotion.create()
        self.assertEqual(len(Promotion.all()), 1)
        # delete the promotion and make sure it isn't in the database
        promotion.delete()
        self.assertEqual(len(Promotion.all()), 0)

    def test_serialize_a_promotion(self):
        """It should serialize a Promotion"""
        promotion = PromotionFactory()
        data = promotion.serialize()
        self.assertNotEqual(data, None)
        self.assertIn("id", data)
        self.assertEqual(data["id"], promotion.id)
        self.assertIn("name", data)
        self.assertEqual(data["name"], promotion.name)
        self.assertIn("promotion_type", data)
        self.assertEqual(data["promotion_type"], promotion.promotion_type)
        self.assertIn("value", data)
        self.assertEqual(data["value"], promotion.value)
        self.assertIn("product_id", data)
        self.assertEqual(data["product_id"], promotion.product_id)
        self.assertIn("start_date", data)
        self.assertEqual(date.fromisoformat(data["start_date"]), promotion.start_date)
        self.assertIn("end_date", data)
        self.assertEqual(date.fromisoformat(data["end_date"]), promotion.end_date)

    def test_deserialize_a_promotion(self):
        """It should de-serialize a Promotion"""
        data = PromotionFactory().serialize()
        promotion = Promotion()
        promotion.deserialize(data)
        self.assertNotEqual(promotion, None)
        self.assertEqual(promotion.id, None)
        self.assertEqual(promotion.name, data["name"])
        self.assertEqual(promotion.promotion_type, data["promotion_type"])
        self.assertEqual(promotion.value, data["value"])
        self.assertEqual(promotion.product_id, data["product_id"])
        self.assertEqual(promotion.start_date, date.fromisoformat(data["start_date"]))
        self.assertEqual(promotion.end_date, date.fromisoformat(data["end_date"]))

    def test_deserialize_missing_data(self):
        """It should not deserialize a Promotion with missing data"""
        data = {"id": 1, "name": "Sale", "promotion_type": "Percentage off"}
        promotion = Promotion()
        self.assertRaises(DataValidationError, promotion.deserialize, data)

    def test_deserialize_bad_data(self):
        """It should not deserialize bad data"""
        data = "this is not a dictionary"
        promotion = Promotion()
        self.assertRaises(DataValidationError, promotion.deserialize, data)

    def test_deserialize_bad_value(self):
        """It should not deserialize a bad value attribute"""
        test_promotion = PromotionFactory()
        data = test_promotion.serialize()
        data["value"] = "not_a_number"
        promotion = Promotion()
        self.assertRaises(DataValidationError, promotion.deserialize, data)

    def test_deserialize_bad_product_id(self):
        """It should not deserialize a bad product_id attribute"""
        test_promotion = PromotionFactory()
        data = test_promotion.serialize()
        data["product_id"] = "not_a_number"
        promotion = Promotion()
        self.assertRaises(DataValidationError, promotion.deserialize, data)

    def test_deserialize_invalid_date(self):
        """It should not deserialize invalid date format"""
        test_promotion = PromotionFactory()
        data = test_promotion.serialize()
        data["start_date"] = "invalid-date"
        promotion = Promotion()
        self.assertRaises(DataValidationError, promotion.deserialize, data)
