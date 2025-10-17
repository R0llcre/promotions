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
from unittest.mock import patch
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

    def test_update_a_promotion(self):
        """It should Update a Promotion"""
        promotion = PromotionFactory()
        promotion.create()
        self.assertIsNotNone(promotion.id)
        # Change it and save it
        original_id = promotion.id
        promotion.name = "Updated Name"
        promotion.update()
        self.assertEqual(promotion.id, original_id)
        self.assertEqual(promotion.name, "Updated Name")
        # Fetch it back and make sure the id hasn't changed but the data did change
        promotions = Promotion.all()
        self.assertEqual(len(promotions), 1)
        self.assertEqual(promotions[0].id, original_id)
        self.assertEqual(promotions[0].name, "Updated Name")

    def test_update_no_id(self):
        """It should not Update a Promotion with no id"""
        promotion = PromotionFactory()
        promotion.id = None
        self.assertRaises(DataValidationError, promotion.update)

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

    def test_deserialize_attribute_error(self):
        """It should not deserialize with attribute error"""
        promotion = Promotion()
        # This should trigger AttributeError -> DataValidationError
        with self.assertRaises(DataValidationError):
            promotion.deserialize({"invalid_field": "value"})

    def test_deserialize_key_error(self):
        """It should not deserialize with missing key"""
        promotion = Promotion()
        # Missing required fields should trigger KeyError -> DataValidationError
        with self.assertRaises(DataValidationError):
            promotion.deserialize({"name": "Test"})  # Missing other required fields


######################################################################
#  T E S T   E X C E P T I O N   H A N D L E R S
######################################################################
class TestExceptionHandlers(TestCaseBase):
    """Promotion Model Exception Handlers"""

    @patch("service.models.db.session.commit")
    def test_create_exception(self, mock_commit):
        """It should catch a create exception"""
        mock_commit.side_effect = Exception("Database error")
        promotion = PromotionFactory()
        self.assertRaises(DataValidationError, promotion.create)

    @patch("service.models.db.session.commit")
    def test_update_exception(self, mock_commit):
        """It should catch a update exception"""
        # First create the promotion normally
        promotion = PromotionFactory()
        promotion.create()
        promotion.name = "Updated Name"

        # Then mock only the update call
        mock_commit.side_effect = Exception("Database error")
        self.assertRaises(DataValidationError, promotion.update)

    @patch("service.models.db.session.commit")
    def test_delete_exception(self, mock_commit):
        """It should catch a delete exception"""
        # First create the promotion normally
        promotion = PromotionFactory()
        promotion.create()

        # Then mock only the delete call
        mock_commit.side_effect = Exception("Database error")
        self.assertRaises(DataValidationError, promotion.delete)


######################################################################
#  Q U E R Y   T E S T   C A S E S
######################################################################
class TestModelQueries(TestCaseBase):
    """Promotion Model Query Tests"""

    def test_find_promotion(self):
        """It should Find a Promotion by ID"""
        promotions = []
        for _ in range(5):
            promotion = PromotionFactory()
            promotion.create()
            promotions.append(promotion)
        # make sure they got saved
        self.assertEqual(len(Promotion.all()), 5)
        # find the 2nd promotion in the list
        promotion = Promotion.find(promotions[1].id)
        self.assertIsNotNone(promotion)
        self.assertEqual(promotion.id, promotions[1].id)
        self.assertEqual(promotion.name, promotions[1].name)
        self.assertEqual(promotion.promotion_type, promotions[1].promotion_type)

    def test_find_by_name(self):
        """It should Find Promotions by Name"""
        for _ in range(10):
            promotion = PromotionFactory()
            promotion.create()
        name = Promotion.all()[0].name
        found = Promotion.find_by_name(name)
        count = len([p for p in Promotion.all() if p.name == name])
        self.assertEqual(found.count(), count)
        for promotion in found:
            self.assertEqual(promotion.name, name)

    def test_find_by_category(self):
        """It should Find Promotions by Category (product_id)"""
        for _ in range(10):
            promotion = PromotionFactory()
            promotion.create()
        product_id = Promotion.all()[0].product_id
        found = Promotion.find_by_category(str(product_id))
        count = len([p for p in Promotion.all() if p.product_id == product_id])
        self.assertEqual(found.count(), count)
        for promotion in found:
            self.assertEqual(promotion.product_id, product_id)

    def test_find_by_id_method(self):
        """It should Find a Promotion by ID using find_by_id method"""
        promotion = PromotionFactory()
        promotion.create()
        found = Promotion.find_by_id(promotion.id)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].id, promotion.id)
        self.assertEqual(found[0].name, promotion.name)

    def test_find_by_category_invalid(self):
        """It should handle invalid category gracefully"""
        found = Promotion.find_by_category("invalid")
        self.assertEqual(found.count(), 0)

    def test_find_by_id_invalid(self):
        """It should handle invalid id gracefully"""
        found = Promotion.find_by_id("invalid")
        self.assertEqual(len(found), 0)
