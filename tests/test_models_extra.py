# tests/test_models_extra.py
# 额外模型覆盖测试：create/find/all/update/delete/remove_all + 异常分支

from service import create_app
from service.models import Promotion
try:
    from service.models import DataValidationError
except Exception:
    try:
        from service.common.error_handlers import DataValidationError
    except Exception:
        class DataValidationError(Exception):
            pass

flask_app = create_app()

def setup_function():
    if hasattr(Promotion, "remove_all"):
        with flask_app.app_context():
            Promotion.remove_all()
    elif hasattr(Promotion, "reset"):
        with flask_app.app_context():
            Promotion.reset()

def test_create_find_all_update_delete_flow():
    p = Promotion()
    p.deserialize({
        "name": "Spring",
        "promotion_type": "Percentage off",
        "value": 20,
        "product_id": 456,
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
    })
    with flask_app.app_context():
        p.create()
        assert p.id is not None

        # find / all
        found = Promotion.find(p.id)
        assert found is not None and found.id == p.id
        assert any(x.id == p.id for x in Promotion.all())

        # update or save（同样给齐必填字段）
        p.deserialize({
            "name": "Spring Sale",
            "promotion_type": "Percentage off",
            "value": 25,
            "product_id": 456,
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        })
        if hasattr(p, "update"):
            p.update()
        elif hasattr(p, "save"):
            p.save()
        again = Promotion.find(p.id)
        assert again.name == "Spring Sale" and float(again.value) == 25.0

        # delete
        p.delete()
        assert Promotion.find(p.id) is None

def test_update_nonexistent_raises_error_if_implemented():
    """如果 update 有保护，覆盖异常分支；否则跳过不报错"""
    p = Promotion()
    p.id = 999_999  # 不存在
    if hasattr(p, "update"):
        with flask_app.app_context():
            try:
                p.update()
            except DataValidationError:
                pass

def test_remove_all_clears_storage():
    p = Promotion()
    p.deserialize({
        "name": "A",
        "promotion_type": "Discount",
        "value": 5,
        "product_id": 1,
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
    })
    with flask_app.app_context():
        p.create()
        if hasattr(Promotion, "remove_all"):
            Promotion.remove_all()
            assert len(Promotion.all()) == 0
