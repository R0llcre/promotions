# service/models.py
# -*- coding: utf-8 -*-
"""
Promotion data model and data operations
"""

from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import delete

# SQLAlchemy database instance (initialized by the app in create_app)
db = SQLAlchemy()


class DataValidationError(Exception):
    """Used for data validation errors (e.g., during deserialization)"""
    pass


class Promotion(db.Model):  # type: ignore[name-defined]
    """Promotion Model"""

    __tablename__ = "promotions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(63), nullable=False)
    promotion_type = db.Column(db.String(63), nullable=False)
    value = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - for debugging only
        return f"<Promotion {self.name} id=[{self.id}]>"

    # ------------------------------------------------------------------
    # Basic Persistence Operations
    # ------------------------------------------------------------------
    def create(self) -> None:
        """Insert the current object into the database"""
        logging.debug("Creating %r", self)
        db.session.add(self)
        db.session.commit()

    def update(self) -> None:
        """Update the current object (by its own ID)"""
        logging.debug("Updating %r", self)
        if not self.id:
            raise DataValidationError("Update called with empty id")
        # Optional safeguard: check existence for better test coverage
        if Promotion.find(self.id) is None:
            raise DataValidationError(f"Promotion with id {self.id} does not exist")
        db.session.commit()

    def delete(self) -> None:
        """Delete the current object from the database"""
        logging.debug("Deleting %r", self)
        db.session.delete(self)
        db.session.commit()

    # ------------------------------------------------------------------
    # Query / Utility Methods
    # ------------------------------------------------------------------
    @classmethod
    def all(cls) -> List["Promotion"]:
        """Return all Promotion records"""
        return cls.query.all()

    @classmethod
    def find(cls, by_id: int) -> Optional["Promotion"]:
        """Find a Promotion by its ID"""
        return cls.query.get(by_id)

    @classmethod
    def find_by_name(cls, name: str) -> List["Promotion"]:
        """Find promotions by exact name match"""
        return cls.query.filter_by(name=name).all()

    @classmethod
    def remove_all(cls) -> None:
        """Completely clear the promotions table

        First performs a bulk delete; if for any reason (e.g., transaction/connection state)
        the table still has remaining rows, perform a hard reset (drop_all + create_all)
        to guarantee the table is empty.
        """
        logging.debug("Removing all rows from %s", cls.__tablename__)
        # 1) Regular bulk delete
        db.session.execute(delete(cls))
        db.session.commit()

        # 2) Fallback check: ensure the table is truly empty
        remain = cls.query.count()
        if remain != 0:
            logging.warning(
                "Table %s still has %d rows after delete(); performing hard reset",
                cls.__tablename__,
                remain,
            )
            db.session.remove()
            db.drop_all()
            db.create_all()

    # ------------------------------------------------------------------
    # Serialization / Deserialization
    # ------------------------------------------------------------------
    def serialize(self) -> dict:
        """Convert the object into a dictionary (JSON-friendly)"""
        return {
            "id": self.id,
            "name": self.name,
            "promotion_type": self.promotion_type,
            "value": self.value,
            "product_id": self.product_id,
            "start_date": (
                self.start_date.isoformat()
                if isinstance(self.start_date, date)
                else self.start_date
            ),
            "end_date": (
                self.end_date.isoformat()
                if isinstance(self.end_date, date)
                else self.end_date
            ),
        }

    def deserialize(self, data: dict) -> "Promotion":
        """Convert a dictionary into a Promotion object (with strict validation)

        Required fields:
        - name: str
        - promotion_type: str
        - value: int
        - product_id: int
        - start_date: ISO8601 string, e.g., '2025-01-01'
        - end_date: ISO8601 string, e.g., '2025-12-31'
        """
        try:
            self.name = data["name"]
            self.promotion_type = data["promotion_type"]

            # Validate value
            if isinstance(data["value"], int):
                self.value = data["value"]
            else:
                raise DataValidationError(
                    "Invalid type for integer [value]: " + str(type(data["value"]))
                )

            # Validate product_id
            if isinstance(data["product_id"], int):
                self.product_id = data["product_id"]
            else:
                raise DataValidationError(
                    "Invalid type for integer [product_id]: "
                    + str(type(data["product_id"]))
                )

            # Validate date format (must be ISO8601)
            self.start_date = date.fromisoformat(data["start_date"])
            self.end_date = date.fromisoformat(data["end_date"])

        except AttributeError as error:
            raise DataValidationError("Invalid attribute: " + error.args[0]) from error
        except KeyError as error:
            # Missing required field
            raise DataValidationError("Invalid promotion: missing " + error.args[0]) from error
        except ValueError as error:
            # Invalid date format, etc.
            raise DataValidationError("Invalid date format: " + str(error)) from error

        return self
