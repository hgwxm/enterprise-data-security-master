"""
tests/test_policy.py — 权限判断引擎测试

严格依据 C 提供的 test_cases.xlsx 中的 8 条测试用例（T001-T008），
并补充无效输入安全处理测试。
"""

import sys
import os
import pytest

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from policy import Decision, check_permission, is_executable


# ══════════ test_cases.xlsx 中的 8 条测试用例 ══════════

TEST_CASES = [
    # (test_id, role, file_id, action, expected_decision, expected_executed)
    ("T001", "employee", "F001", "read",   "ALLOW",            True),
    ("T002", "employee", "F002", "read",   "DENY",             False),
    ("T003", "employee", "F003", "read",   "DENY",             False),
    ("T004", "finance",  "F002", "read",   "ALLOW",            True),
    ("T005", "finance",  "F003", "read",   "DENY",             False),
    ("T006", "employee", "F002", "export", "PENDING_APPROVAL", False),
    ("T007", "admin",    "F003", "read",   "ALLOW",            True),
    ("T008", "admin",    "F003", "export", "ALLOW",            True),
]


@pytest.mark.parametrize("test_id,role,file_id,action,exp_decision,exp_executed", TEST_CASES)
def test_permission_matrix(test_id, role, file_id, action, exp_decision, exp_executed):
    """逐条验证 test_cases.xlsx 中的权限判定结果。"""
    decision, reason = check_permission(role, file_id, action)
    assert decision.value == exp_decision, (
        f"{test_id}: 期望 {exp_decision}，实际 {decision.value}，原因：{reason}"
    )
    assert is_executable(decision) == exp_executed, (
        f"{test_id}: 期望 executed={exp_executed}，实际 {is_executable(decision)}"
    )


# ══════════ 无效输入安全处理 ══════════

def test_invalid_role():
    """未知角色应返回 DENY。"""
    decision, reason = check_permission("hacker", "F001", "read")
    assert decision == Decision.DENY
    assert "拒绝" in reason


def test_invalid_file():
    """未知文件编号应返回 DENY。"""
    decision, reason = check_permission("employee", "F999", "read")
    assert decision == Decision.DENY
    assert "拒绝" in reason


def test_invalid_action():
    """未知操作类型应返回 DENY。"""
    decision, reason = check_permission("employee", "F001", "delete")
    assert decision == Decision.DENY
    assert "拒绝" in reason


def test_none_role():
    """role=None 应返回 DENY。"""
    decision, reason = check_permission(None, "F001", "read")
    assert decision == Decision.DENY


def test_none_file():
    """file_id=None 应返回 DENY。"""
    decision, reason = check_permission("employee", None, "read")
    assert decision == Decision.DENY


def test_none_action():
    """action=None 应返回 DENY。"""
    decision, reason = check_permission("employee", "F001", None)
    assert decision == Decision.DENY


def test_empty_string_role():
    """空字符串角色应返回 DENY。"""
    decision, reason = check_permission("", "F001", "read")
    assert decision == Decision.DENY


def test_non_string_role():
    """非字符串角色（整数）应返回 DENY。"""
    decision, reason = check_permission(123, "F001", "read")
    assert decision == Decision.DENY


def test_non_string_file():
    """非字符串文件编号（列表）应返回 DENY。"""
    decision, reason = check_permission("employee", ["F001"], "read")
    assert decision == Decision.DENY


# ══════════ is_executable 测试 ══════════

def test_is_executable_allow():
    assert is_executable(Decision.ALLOW) is True


def test_is_executable_deny():
    assert is_executable(Decision.DENY) is False


def test_is_executable_pending():
    assert is_executable(Decision.PENDING_APPROVAL) is False
