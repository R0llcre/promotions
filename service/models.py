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
Models for Promotions
"""

import logging
from datetime import date
from flask_sqlalchemy import SQLAlchemy

logger = logging.getLogger("flask.app")

# SQLAlchemy object initialized later in init_db()
db = SQLAlchemy()


class DataValidationError(Exception):
    """Used for data validation errors when deserializing or updating"""


class Promotion(db.Model):
    """
    Class that represents a Promotion
    """

    ##################################################
    # Table Schema
    ##################################################
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(63), nullable=False)
    promotion_type = db.Column(db.String(63), nullable=False)
    value = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    # Auditing fields
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    last_updated = db.Column(
        db.DateTime, default=db.func.now(), onupdate=db.func.now(), nullable=False
    )

    ##################################################
    # INSTANCE METHODS
    ##################################################

    def __repr__(self) -> str:
        return f"<Promotion {self.name} id=[{self.id}]>"

    def create(self) -> None:
        """
        Creates this Promotion in the database
        """
        logger.info("Creating %s", self.name)
        # always reset id so SQLAlchemy allocates a new one
        self.id = None  # pylint: disable=invalid-name
        try:
            db.session.add(self)
            db.session.commit()
        except Exception as e:  # noqa: BLE001
            db.session.rollback()
            logger.error("Error creating record: %s", self)
            raise DataValidationError(e) from e

    def update(self) -> None:
        """
        Updates this Promotion in the database

        Raises:
            DataValidationError: if called without an id
        """
        logger.info("Saving %s", self.name)
        if not self.id:
            raise DataValidationError("Update called with empty ID field")
        try:
            db.session.commit()
        except Exception as e:  # noqa: BLE001
            db.session.rollback()
            logger.error("Error updating record: %s", self)
            raise DataValidationError(e) from e

    def delete(self) -> None:
        """
        Removes this Promotion from the database
        """
        logger.info("Deleting %s", self.name)
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as e:  # noqa: BLE001
            db.session.rollback()
            logger.error("Error deleting record: %s", self)
            raise DataValidationError(e) from e

    def serialize(self) -> dict:
        """
        Serializes a Promotion into a dictionary
        """
        return {
            "id": self.id,
            "name": self.name,
            "promotion_type": self.promotion_type,
            "value": self.value,
            "product_id": self.product_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
        }

    def deserialize(self, data: dict) -> "Promotion":
        """
        Deserializes a Promotion from a dictionary

        Args:
            data (dict): A dictionary with Promotion data

        Raises:
            DataValidationError: if data types/values are invalid or keys are missing
        """
        try:
            self.name = data["name"]
            self.promotion_type = data["promotion_type"]

            if isinstance(data["value"], int):
                self.value = data["value"]
            else:
                raise DataValidationError(
                    f"Invalid type for integer [value]: {type(data['value'])}"
                )

            if isinstance(data["product_id"], int):
                self.product_id = data["product_id"]
            else:
                raise DataValidationError(
                    f"Invalid type for integer [product_id]: {type(data['product_id'])}"
                )

            self.start_date = date.fromisoformat(data["start_date"])
            self.end_date = date.fromisoformat(data["end_date"])

        except AttributeError as error:
            raise DataValidationError(f"Invalid attribute: {error.args[0]}") from error
        except KeyError as error:
            raise DataValidationError(
                f"Invalid promotion: missing {error.args[0]}"
            ) from error
        except (TypeError, ValueError) as error:
            raise DataValidationError(
                f"Invalid promotion: body of request contained bad or no data {error}"
            ) from error

        return self

    ##################################################
    # CLASS METHODS
    ##################################################

    @classmethod
    def all(cls):
        """Returns all Promotions"""
        logger.info("Processing all Promotions")
        return cls.query.all()

    @classmethod
    def find(cls, by_id: int):
        """Finds a Promotion by its ID (single object or None)"""
        logger.info("Processing lookup for id %s ...", by_id)
        return cls.query.session.get(cls, by_id)

    @classmethod
    def find_by_name(cls, name: str):
        """
        Returns a SQLAlchemy Query filtered by name.

        Note: do NOT call .all() here; tests expect to be able to call .count() on the result.
        """
        logger.info("Processing name query for %s ...", name)
        return cls.query.filter(cls.name == name)

    @classmethod
    def find_by_promotion_type(cls, promotion_type: str):
        """Returns a list of Promotions that exactly match the given promotion_type"""
        logger.info("Processing promotion_type query for %s ...", promotion_type)
        return cls.query.filter(cls.promotion_type == promotion_type).all()

    @classmethod
    def find_by_category(cls, category):
        """
        Returns a list of Promotions that match the given category (product_id).

        The test suite passes category as a string; we must return an empty list
        gracefully when it cannot be parsed as an integer.
        """
        logger.info("Processing category query for %s ...", category)
        try:
            product_id = int(category)
            return cls.query.filter(cls.product_id == product_id).all()
        except (ValueError, TypeError):
            return []

    @classmethod
    def find_by_id(cls, promotion_id):
        """
        Returns a list with the Promotion found by id (0 or 1 element).

        The test suite expects a list, and also expects graceful handling
        when the id cannot be parsed as an integer.
        """
        logger.info("Processing id query for %s ...", promotion_id)
        try:
            pid = int(promotion_id)
            promotion = cls.query.session.get(cls, pid)
            return [promotion] if promotion else []
        except (ValueError, TypeError):
            return []
