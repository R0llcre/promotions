# tests/test_routes_more.py
# -*- coding: utf-8 -*-

from unittest.mock import patch

from service import app as flask_app
from service.common import status
from service.models import Promotion


def test_get_empty_list_returns_200_and_empty_array():
    """当没有任何记录时，GET /promotions 返回空数组并 200"""
    client = flask_app.test_client()

    # 必须在 app_context 下清库，否则 remove_all 不会真正执行
    try:
        with flask_app.app_context():
            if hasattr(Promotion, "remove_all"):
                Promotion.remove_all()
    except Exception:  # noqa: BLE001
        # 没有 remove_all 也不阻塞测试
        pass

    resp = client.get("/promotions")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_update_nonexistent_returns_404():
    """更新不存在的 id → 404"""
    client = flask_app.test_client()
    payload = {
        "name": "Updated",
        "promotion_type": "Discount",
        "value": 10,
        "product_id": 1,
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
    }
    resp = client.put("/promotions/999999", json=payload)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_delete_nonexistent_returns_404():
    """删除不存在的 id → 404"""
    client = flask_app.test_client()
    resp = client.delete("/promotions/999999")
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_internal_server_error_returns_json():
    """构造一个会抛异常的路径来触发 500，覆盖 500 JSON 错误处理
    通过对模型层打补丁（让 Promotion.find 抛 RuntimeError），
    触发 error_handlers 的 500 分支，而不需要在运行时动态加路由。
    注意：测试里需要暂时关闭异常传播（TESTING/PROPAGATE_EXCEPTIONS），否则 Flask 会把异常抛到测试进程而不是返回 500。
    """
    client = flask_app.test_client()

    prev_testing = flask_app.testing
    prev_propagate = flask_app.config.get("PROPAGATE_EXCEPTIONS", None)
    flask_app.testing = False
    flask_app.config["PROPAGATE_EXCEPTIONS"] = False

    try:
        with patch.object(Promotion, "find", side_effect=RuntimeError("kaboom")):
            resp = client.get("/promotions/1")
            assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = resp.get_json()
            assert isinstance(data, dict)
            assert any(k in data for k in {"error", "message", "status", "code"})
    finally:
        flask_app.testing = prev_testing
        if prev_propagate is None:
            flask_app.config.pop("PROPAGATE_EXCEPTIONS", None)
        else:
            flask_app.config["PROPAGATE_EXCEPTIONS"] = prev_propagate


# ------- 额外增加两个过滤分支用例，提高覆盖率 -------

def _mk(client, **override):
    """创建一条合法的 Promotion 并返回 id"""
    data = {
        "name": "BF",
        "promotion_type": "Discount",
        "value": 50,
        "product_id": 123,
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
    }
    data.update(override)
    r = client.post("/promotions", json=data)
    assert r.status_code == status.HTTP_201_CREATED
    return r.get_json()["id"]


def test_list_filter_by_name_no_match():
    """带 name 查询参数但没有匹配项 → 返回空数组"""
    client = flask_app.test_client()
    # 保证至少存在一条非匹配数据
    _mk(client, name="SomethingElse")

    resp = client.get("/promotions", query_string={"name": "NotExistName"})
    assert resp.status_code == status.HTTP_200_OK
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_list_filter_by_name_match():
    """带 name 查询参数且有匹配项 → 返回包含该项"""
    client = flask_app.test_client()
    target_name = "FilterMe"
    pid = _mk(client, name=target_name)

    resp = client.get("/promotions", query_string={"name": target_name})
    assert resp.status_code == status.HTTP_200_OK
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1
    ids = {item["id"] for item in data}
    assert pid in ids
