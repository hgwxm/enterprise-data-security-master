"""
tests/test_file_service.py - 文件访问控制测试

验证：
1. ALLOW 时能成功读取/导出文件内容
2. DENY 时不执行任何文件操作（content/export_data 为 None）
3. PENDING_APPROVAL 时不执行任何文件操作
"""

import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from policy import Decision
from file_service import read_file, export_file, get_file_list, FILE_REGISTRY


# === 读取操作测试 ===

def test_read_allow_returns_content():
    """ALLOW 时读取应返回文件内容。"""
    result = read_file("employee", "F001")
    assert result.success is True
    assert result.decision == Decision.ALLOW
    assert result.content is not None
    assert "title" in result.content


def test_read_deny_no_content():
    """DENY 时读取不应返回任何内容。"""
    result = read_file("employee", "F002")
    assert result.success is False
    assert result.decision == Decision.DENY
    assert result.content is None


def test_read_deny_sensitive_file():
    """普通员工读取敏感工资表应被拒绝。"""
    result = read_file("employee", "F003")
    assert result.success is False
    assert result.content is None


def test_read_allow_finance():
    """财务人员读取内部财务报告应成功。"""
    result = read_file("finance", "F002")
    assert result.success is True
    assert result.content is not None
    assert "revenue" in result.content


def test_read_deny_finance_salary():
    """财务人员读取敏感工资表应被拒绝。"""
    result = read_file("finance", "F003")
    assert result.success is False
    assert result.content is None


def test_read_allow_admin():
    """管理员读取敏感工资表应成功。"""
    result = read_file("admin", "F003")
    assert result.success is True
    assert result.content is not None
    assert "records" in result.content


# === 导出操作测试 ===

def test_export_allow_returns_data():
    """ALLOW 时导出应返回数据字节流。"""
    result = export_file("employee", "F001")
    assert result.success is True
    assert result.decision == Decision.ALLOW
    assert result.export_data is not None
    assert isinstance(result.export_data, bytes)
    parsed = json.loads(result.export_data.decode("utf-8"))
    assert parsed["file_id"] == "F001"


def test_export_pending_no_data():
    """PENDING_APPROVAL 时导出不应返回任何数据。"""
    result = export_file("employee", "F002")
    assert result.success is False
    assert result.decision == Decision.PENDING_APPROVAL
    assert result.export_data is None


def test_export_deny_no_data():
    """DENY 时导出不应返回任何数据。"""
    result = export_file("employee", "F003")
    assert result.success is False
    assert result.decision == Decision.DENY
    assert result.export_data is None


def test_export_allow_admin_sensitive():
    """管理员导出敏感工资表应成功。"""
    result = export_file("admin", "F003")
    assert result.success is True
    assert result.export_data is not None
    parsed = json.loads(result.export_data.decode("utf-8"))
    assert parsed["file_id"] == "F003"


# === 文件列表测试 ===

def test_file_list():
    """文件列表应包含 3 个文件。"""
    files = get_file_list()
    assert len(files) == 3
    ids = {f["id"] for f in files}
    assert ids == {"F001", "F002", "F003"}


def test_file_registry():
    """文件注册表应包含正确的元信息。"""
    assert "F001" in FILE_REGISTRY
    assert "F002" in FILE_REGISTRY
    assert "F003" in FILE_REGISTRY
    for fid, info in FILE_REGISTRY.items():
        assert "name" in info
        assert "description" in info


# === 无效输入测试 ===

def test_read_invalid_role():
    """无效角色读取应失败。"""
    result = read_file("hacker", "F001")
    assert result.success is False
    assert result.content is None


def test_read_invalid_file():
    """无效文件编号读取应失败。"""
    result = read_file("employee", "F999")
    assert result.success is False
    assert result.content is None
