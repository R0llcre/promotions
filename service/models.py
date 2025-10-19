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

WHY this change:
- Unify the query contract: single-item lookup (find) returns object|None;
  multi-item lookups (find_by_name/product_id/promotion_type) return list.
- Replace ambiguous 'category' with explicit 'product_id' for clarity.
- Keep a backward-compatible alias find_by_category -> find_by_product_id.
"""

import logging
from datetime import date
from typing import List, Optional, Union

from flask_sqlalchemy import SQLAlchemy

logger = logging.getLogger("flask.app")

# SQLAlchemy handle; initialized in init_db()
db = SQLAlchemy()


class DataValidationError(Exception):
    """Used for data validation errors when deserializing or updating."""


class DatabaseError(Exception):
    """Used for database operation failures (commit/connection/constraint errors)."""


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

    def __repr__(self):
        return f"<Promotion {self.name} id=[{self.id}]>"

    def create(self):
        """Creates this Promotion in the database."""
        logger.info("Creating %s", self.name)
        self.id = None  # make sure id is None so SQLAlchemy will assign one
        try:
            db.session.add(self)
            # Ensure PK is assigned even if commit() is mocked in tests:
            # flush sends pending INSERTs to the DB within the tx and assigns IDs
            db.session.flush()
            db.session.commit()
        except Exception as e:  # pragma: no cover - exercised via exception tests
            db.session.rollback()
            logger.error("Error creating record: %s", self)
            raise DatabaseError(e) from e

    def update(self):
        """Updates this Promotion in the database."""
        logger.info("Saving %s", self.name)
        if not self.id:
            # more friendly message
            raise DataValidationError("Field 'id' is required for update")
        try:
            db.session.commit()
        except Exception as e:  # pragma: no cover - exercised via exception tests
            db.session.rollback()
            logger.error("Error updating record: %s", self)
            raise DatabaseError(e) from e

    def delete(self):
        """Removes this Promotion from the data store."""
        logger.info("Deleting %s", self.name)
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as e:  # pragma: no cover - exercised via exception tests
            db.session.rollback()
            logger.error("Error deleting record: %s", self)
            raise DatabaseError(e) from e

    def serialize(self) -> dict:
        """Serializes a Promotion into a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "promotion_type": self.promotion_type,
            "value": self.value,
            "product_id": self.product_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
        }

    def deserialize(self, data: dict):
        """
        Deserializes a Promotion from a dictionary.

        Args:
            data (dict): a dictionary containing the promotion data
        """
        try:
            # required string fields
            self.name = data["name"]
            self.promotion_type = data["promotion_type"]

            # integer fields with human-friendly messages
            if isinstance(data.get("value"), int):
                self.value = data["value"]
            else:
                raise DataValidationError("Field 'value' must be an integer")

            if isinstance(data.get("product_id"), int):
                self.product_id = data["product_id"]
            else:
                raise DataValidationError("Field 'product_id' must be an integer")

            # dates with explicit per-field validation messages
            try:
                self.start_date = date.fromisoformat(data["start_date"])
            except Exception as e:
                raise DataValidationError(
                    "Field 'start_date' must be an ISO date (YYYY-MM-DD)"
                ) from e

            try:
                self.end_date = date.fromisoformat(data["end_date"])
            except Exception as e:
                raise DataValidationError(
                    "Field 'end_date' must be an ISO date (YYYY-MM-DD)"
                ) from e

        except AttributeError as error:
            # e.g., data is not a dict-like
            raise DataValidationError("Invalid attribute: " + error.args[0]) from error
        except KeyError as error:
            # missing required field
            missing = error.args[0]
            raise DataValidationError(f"Invalid promotion: missing '{missing}'") from error
        except TypeError as error:
            # non-dict body or incompatible structure
            raise DataValidationError(
                "Invalid promotion: request body contained malformed or invalid data"
            ) from error

        return self


    ##################################################
    # CLASS METHODS  (Unified contract)
    ##################################################

    @classmethod
    def all(cls) -> List["Promotion"]:
        """Returns all Promotions in the database (as a list)."""
        logger.info("Processing all Promotions")
        return list(cls.query.all())

    @classmethod
    def find(cls, by_id: Union[int, str]) -> Optional["Promotion"]:
        """Finds a Promotion by its ID (single object or None)."""
        logger.info("Processing lookup for id %s ...", by_id)
        try:
            pid = int(by_id)
        except (TypeError, ValueError):
            return None
        return cls.query.session.get(cls, pid)

    @classmethod
    def find_by_name(cls, name: str) -> List["Promotion"]:
        """Returns all Promotions that match the given name (as a list)."""
        logger.info("Processing name query for %s ...", name)
        return list(cls.query.filter(cls.name == name).all())

    @classmethod
    def find_by_promotion_type(cls, promotion_type: str) -> List["Promotion"]:
        """Returns all Promotions that match the given promotion_type exactly (as a list)."""
        logger.info("Processing promotion_type query for %s ...", promotion_type)
        return list(cls.query.filter(cls.promotion_type == promotion_type).all())

    @classmethod
    def find_by_product_id(cls, product_id: Union[int, str]) -> List["Promotion"]:
        """Returns all Promotions that match the given product_id (as a list).

        WHY: This replaces the ambiguous 'category' naming with explicit 'product_id',
        and returns a concrete list to unify multi-item query semantics.
        """
        logger.info("Processing product_id query for %s ...", product_id)
        try:
            pid = int(product_id)
        except (TypeError, ValueError):
            return []
        return list(cls.query.filter(cls.product_id == pid).all())

    @classmethod
    def find_active(cls, on_date: date | None = None) -> list["Promotion"]:
        """
        Returns all Promotions that are active on the given date (inclusive).
        Active means: start_date <= on_date <= end_date.

        """
        if on_date is None:
            on_date = date.today()
        return list(
            cls.query.filter(
                cls.start_date <= on_date,
                cls.end_date >= on_date,
            ).all()
        )
