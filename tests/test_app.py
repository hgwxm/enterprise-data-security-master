"""
tests/test_app.py - Flask 后端接口测试

使用 Flask test client 验证：
1. POST /api/access 权限判定接口
2. GET  /api/audit/logs 审计日志查询
3. GET  /api/audit/stats 审计统计
4. POST /api/audit/clear 清空日志
5. GET  /api/files 文件列表
6. GET  /api/health 健康检查
7. 页面路由返回 200
"""

import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app


@pytest.fixture
def client():
    """Flask 测试客户端。"""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# === POST /api/access 测试 ===

def test_access_allow(client):
    """employee 读取 F001 应返回 ALLOW 且 executed=true。"""
    resp = client.post("/api/access", json={
        "user_role": "employee", "file_id": "F001", "action": "read"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["decision"] == "ALLOW"
    assert data["executed"] is True
    assert data["request_id"].startswith("REQ")
    assert data["timestamp"] != ""


def test_access_deny(client):
    """employee 读取 F002 应返回 DENY 且 executed=false。"""
    resp = client.post("/api/access", json={
        "user_role": "employee", "file_id": "F002", "action": "read"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["decision"] == "DENY"
    assert data["executed"] is False


def test_access_pending(client):
    """employee 导出 F002 应返回 PENDING_APPROVAL 且 executed=false。"""
    resp = client.post("/api/access", json={
        "user_role": "employee", "file_id": "F002", "action": "export"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["decision"] == "PENDING_APPROVAL"
    assert data["executed"] is False


def test_access_admin_sensitive(client):
    """admin 读取 F003 应返回 ALLOW 且 executed=true。"""
    resp = client.post("/api/access", json={
        "user_role": "admin", "file_id": "F003", "action": "read"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["decision"] == "ALLOW"
    assert data["executed"] is True


def test_access_invalid_role(client):
    """无效角色应返回 DENY。"""
    resp = client.post("/api/access", json={
        "user_role": "hacker", "file_id": "F001", "action": "read"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["decision"] == "DENY"
    assert data["executed"] is False


def test_access_missing_field(client):
    """缺少字段应返回 DENY（安全默认）。"""
    resp = client.post("/api/access", json={
        "user_role": "employee", "file_id": "F001"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["decision"] == "DENY"


def test_access_form_data(client):
    """支持 form-data 提交。"""
    resp = client.post("/api/access", data={
        "user_role": "employee", "file_id": "F001", "action": "read"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["decision"] == "ALLOW"


# === GET /api/audit/logs 测试 ===

def test_audit_logs_returns_list(client):
    """审计日志接口应返回列表。"""
    # 先发起一次请求产生日志
    client.post("/api/access", json={
        "user_role": "employee", "file_id": "F001", "action": "read"
    })
    resp = client.get("/api/audit/logs")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "logs" in data
    assert "count" in data
    assert isinstance(data["logs"], list)
    assert data["count"] >= 1


def test_audit_logs_filter_decision(client):
    """按 decision 筛选审计日志。"""
    client.post("/api/access", json={
        "user_role": "employee", "file_id": "F001", "action": "read"
    })
    client.post("/api/access", json={
        "user_role": "employee", "file_id": "F002", "action": "read"
    })
    resp = client.get("/api/audit/logs?decision=ALLOW")
    assert resp.status_code == 200
    data = resp.get_json()
    for log in data["logs"]:
        assert log["decision"] == "ALLOW"


# === GET /api/audit/stats 测试 ===

def test_audit_stats(client):
    """审计统计接口应返回 total/allow/deny/pending。"""
    resp = client.get("/api/audit/stats")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "total" in data
    assert "allow" in data
    assert "deny" in data
    assert "pending" in data


# === POST /api/audit/clear 测试 ===

def test_audit_clear(client):
    """清空审计日志。"""
    client.post("/api/access", json={
        "user_role": "employee", "file_id": "F001", "action": "read"
    })
    resp = client.post("/api/audit/clear")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "deleted" in data
    # 清空后查询应为空
    resp2 = client.get("/api/audit/logs")
    assert resp2.get_json()["count"] == 0


# === GET /api/files 测试 ===

def test_files_list(client):
    """文件列表接口应返回 3 个文件。"""
    resp = client.get("/api/files")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "files" in data
    assert len(data["files"]) == 3


# === GET /api/health 测试 ===

def test_health(client):
    """健康检查应返回 ok。"""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"


# === 页面路由测试 ===

def test_page_console(client):
    """访问控制台页面应返回 200。"""
    resp = client.get("/")
    assert resp.status_code == 200


def test_page_audit(client):
    """审计日志页面应返回 200。"""
    resp = client.get("/audit")
    assert resp.status_code == 200


def test_page_rules(client):
    """权限规则页面应返回 200。"""
    resp = client.get("/rules")
    assert resp.status_code == 200


def test_page_about(client):
    """系统说明页面应返回 200。"""
    resp = client.get("/about")
    assert resp.status_code == 200
