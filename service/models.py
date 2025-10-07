# service/models.py
# -*- coding: utf-8 -*-
"""
Promotion 数据模型与数据操作
"""

from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import delete

# SQLAlchemy 数据库实例（在 create_app 中由 app 进行初始化）
db = SQLAlchemy()


class DataValidationError(Exception):
    """数据校验异常（用于反序列化等）"""
    pass


class Promotion(db.Model):  # type: ignore[name-defined]
    """Promotion 模型"""

    __tablename__ = "promotions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(63), nullable=False)
    promotion_type = db.Column(db.String(63), nullable=False)
    value = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        return f"<Promotion {self.name} id=[{self.id}]>"

    # ------------------------------------------------------------------
    # 基本持久化操作
    # ------------------------------------------------------------------
    def create(self) -> None:
        """插入当前对象"""
        logging.debug("Creating %r", self)
        db.session.add(self)
        db.session.commit()

    def update(self) -> None:
        """更新当前对象（根据 self.id）"""
        logging.debug("Updating %r", self)
        if not self.id:
            raise DataValidationError("Update called with empty id")
        # 确认存在（可选，便于测试覆盖“保护”分支）
        if Promotion.find(self.id) is None:
            raise DataValidationError(f"Promotion with id {self.id} does not exist")
        db.session.commit()

    def delete(self) -> None:
        """删除当前对象"""
        logging.debug("Deleting %r", self)
        db.session.delete(self)
        db.session.commit()

    # ------------------------------------------------------------------
    # 查询/工具类方法
    # ------------------------------------------------------------------
    @classmethod
    def all(cls) -> List["Promotion"]:
        """返回所有记录"""
        return cls.query.all()

    @classmethod
    def find(cls, by_id: int) -> Optional["Promotion"]:
        """按 id 查找"""
        return cls.query.get(by_id)

    @classmethod
    def find_by_name(cls, name: str) -> List["Promotion"]:
        """按 name 精确匹配"""
        return cls.query.filter_by(name=name).all()

    @classmethod
    def remove_all(cls) -> None:
        """强制清空表

        先做一次 bulk delete；若异常情况仍有遗留（例如某些事务/连接状态导致未完全清空），
        进行一次 drop_all + create_all 兜底，保证表确实为空。
        """
        logging.debug("Removing all rows from %s", cls.__tablename__)
        # 1) 常规批量删除
        db.session.execute(delete(cls))
        db.session.commit()

        # 2) 兜底：确保真的清空
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
    # 序列化 / 反序列化
    # ------------------------------------------------------------------
    def serialize(self) -> dict:
        """对象 -> dict（JSON 友好）"""
        return {
            "id": self.id,
            "name": self.name,
            "promotion_type": self.promotion_type,
            "value": self.value,
            "product_id": self.product_id,
            "start_date": self.start_date.isoformat() if isinstance(self.start_date, date) else self.start_date,
            "end_date": self.end_date.isoformat() if isinstance(self.end_date, date) else self.end_date,
        }

    def deserialize(self, data: dict) -> "Promotion":
        """dict -> 对象（带严格校验）

        需要字段：
        - name: str
        - promotion_type: str
        - value: int
        - product_id: int
        - start_date: ISO8601 日期字符串，如 '2025-01-01'
        - end_date: ISO8601 日期字符串，如 '2025-12-31'
        """
        try:
            self.name = data["name"]
            self.promotion_type = data["promotion_type"]

            # value
            if isinstance(data["value"], int):
                self.value = data["value"]
            else:
                raise DataValidationError(
                    "Invalid type for integer [value]: " + str(type(data["value"]))
                )

            # product_id
            if isinstance(data["product_id"], int):
                self.product_id = data["product_id"]
            else:
                raise DataValidationError(
                    "Invalid type for integer [product_id]: " + str(type(data["product_id"]))
                )

            # 日期必须是 ISO 字符串，可被 date.fromisoformat 解析
            self.start_date = date.fromisoformat(data["start_date"])
            self.end_date = date.fromisoformat(data["end_date"])

        except AttributeError as error:
            raise DataValidationError("Invalid attribute: " + error.args[0]) from error
        except KeyError as error:
            # 缺字段
            raise DataValidationError("Invalid promotion: missing " + error.args[0]) from error
        except ValueError as error:
            # 日期格式错误等
            raise DataValidationError("Invalid date format: " + str(error)) from error

        return self
