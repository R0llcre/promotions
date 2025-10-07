# tests/test_routes_crud_extra.py
# 额外路由覆盖测试：GET/LIST/PUT/DELETE + 405

from service.common import status
from service import create_app
from service.models import Promotion

# 每个模块自己创建 app，避免和课程测试互相影响
flask_app = create_app()

def setup_function():
    # 清库（根据你们模型的方法名择一使用）
    if hasattr(Promotion, "remove_all"):
        with flask_app.app_context():
            Promotion.remove_all()
    elif hasattr(Promotion, "reset"):
        with flask_app.app_context():
            Promotion.reset()

def _mk(client, **override):
    """创建一条合法的 Promotion 并返回 id"""
    data = {
        "name": "BF",
        "promotion_type": "Discount",
        "value": 50,
        "product_id": 123,
        # 你的 models.deserialize 要求必须要有日期：
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
    client = flask_app.test_client()
    pid = _mk(client)
    r = client.get(f"/promotions/{pid}")
    assert r.status_code == status.HTTP_200_OK
    body = r.get_json()
    assert body["id"] == pid and body["name"] == "BF"

def test_list_promotions_returns_array_and_counts():
    client = flask_app.test_client()
    _ = _mk(client)
    _ = _mk(client, name="X")
    r = client.get("/promotions")
    assert r.status_code == status.HTTP_200_OK
    body = r.get_json()
    assert isinstance(body, list) and len(body) >= 2

def test_update_promotion_changes_fields():
    client = flask_app.test_client()
    pid = _mk(client)
    # 你的 deserialize 是“全量更新”模型：PUT 里也要给齐所有必填字段（含日期）
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
    client = flask_app.test_client()
    pid = _mk(client)
    r = client.delete(f"/promotions/{pid}")
    assert r.status_code == status.HTTP_204_NO_CONTENT
    r = client.get(f"/promotions/{pid}")
    assert r.status_code == status.HTTP_404_NOT_FOUND

def test_method_not_allowed_returns_json():
    """触发 405，覆盖 JSON 错误处理"""
    client = flask_app.test_client()
    r = client.put("/promotions")  # 未定义的 PUT /promotions → 405
    assert r.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    body = r.get_json()
    assert "error" in body and "message" in body

