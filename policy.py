"""
policy.py — 权限判断引擎

严格依据 C 提供的 permission.docx 权限规则实现。
支持三种决策：ALLOW（允许）、DENY（拒绝）、PENDING_APPROVAL（待审批）。
对所有无效输入（未知角色/文件/操作、None、空串、类型错误）一律返回 DENY，
遵循"默认拒绝"安全原则。

规则来源：permission.docx（C 提供），共 3 角色 × 3 文件 × 2 操作 = 18 条规则。
"""

from enum import Enum
from typing import Optional, Tuple


class Decision(Enum):
    """权限判定结果的三种状态。"""
    ALLOW = "ALLOW"
    DENY = "DENY"
    PENDING_APPROVAL = "PENDING_APPROVAL"


# ── 合法值集合 ──
VALID_ROLES = frozenset({"employee", "finance", "admin"})
VALID_FILES = frozenset({"F001", "F002", "F003"})
VALID_ACTIONS = frozenset({"read", "export"})

# ── 权限规则表 ──
# 键格式：(role, file_id, action)
# 值：(Decision, reason)
# 严格对应 permission.docx 中的 18 条规则，不做任何修改或扩展。
POLICY_TABLE = {
    # 普通员工 employee
    ("employee", "F001", "read"):   (Decision.ALLOW,            "该角色对该文件有读取权限"),
    ("employee", "F001", "export"): (Decision.ALLOW,            "该角色对该文件有导出权限"),
    ("employee", "F002", "read"):   (Decision.DENY,             "普通员工无权访问内部财务报告"),
    ("employee", "F002", "export"): (Decision.PENDING_APPROVAL, "导出内部财务报告需要审批"),
    ("employee", "F003", "read"):   (Decision.DENY,             "普通员工无权访问敏感工资数据"),
    ("employee", "F003", "export"): (Decision.DENY,             "普通员工无权导出敏感工资数据"),
    # 财务人员 finance
    ("finance", "F001", "read"):    (Decision.ALLOW,            "该角色对该文件有读取权限"),
    ("finance", "F001", "export"):  (Decision.ALLOW,            "该角色对该文件有导出权限"),
    ("finance", "F002", "read"):    (Decision.ALLOW,            "该角色对该文件有读取权限"),
    ("finance", "F002", "export"):  (Decision.ALLOW,            "该角色对该文件有导出权限"),
    ("finance", "F003", "read"):    (Decision.DENY,             "财务人员无权访问敏感工资数据"),
    ("finance", "F003", "export"):  (Decision.DENY,             "财务人员无权导出敏感工资数据"),
    # 管理员 admin
    ("admin", "F001", "read"):      (Decision.ALLOW,            "该角色对该文件有读取权限"),
    ("admin", "F001", "export"):    (Decision.ALLOW,            "该角色对该文件有导出权限"),
    ("admin", "F002", "read"):      (Decision.ALLOW,            "该角色对该文件有读取权限"),
    ("admin", "F002", "export"):    (Decision.ALLOW,            "该角色对该文件有导出权限"),
    ("admin", "F003", "read"):      (Decision.ALLOW,            "该角色对该文件有读取权限"),
    ("admin", "F003", "export"):    (Decision.ALLOW,            "该角色对该文件有导出权限"),
}

# ── 无效输入的拒绝理由 ──
_REASON_UNKNOWN_ROLE = "未知用户角色，按安全策略默认拒绝"
_REASON_UNKNOWN_FILE = "未知文件编号，按安全策略默认拒绝"
_REASON_UNKNOWN_ACTION = "未知操作类型，按安全策略默认拒绝"
_REASON_INVALID_INPUT = "输入参数无效，按安全策略默认拒绝"
_REASON_NO_RULE = "未匹配到任何授权规则，按安全策略默认拒绝"


def _is_valid_string(value) -> bool:
    """检查 value 是否为非空字符串。"""
    return isinstance(value, str) and len(value) > 0


def check_permission(role: str, file_id: str, action: str) -> Tuple[Decision, str]:
    """
    权限判断统一入口。

    严格依据 POLICY_TABLE 查表判定。对任何无效输入（None、空串、非字符串、
    未知角色/文件/操作）一律返回 (DENY, reason)，不泄露内部细节。

    Args:
        role:    用户角色，合法值为 "employee" / "finance" / "admin"
        file_id: 文件编号，合法值为 "F001" / "F002" / "F003"
        action:  操作类型，合法值为 "read" / "export"

    Returns:
        (Decision, reason) 二元组。Decision 为枚举值，reason 为中文说明。
    """
    # ── 输入安全检查：类型与空值 ──
    if not _is_valid_string(role):
        return (Decision.DENY, _REASON_INVALID_INPUT)
    if not _is_valid_string(file_id):
        return (Decision.DENY, _REASON_INVALID_INPUT)
    if not _is_valid_string(action):
        return (Decision.DENY, _REASON_INVALID_INPUT)

    # ── 合法值检查 ──
    if role not in VALID_ROLES:
        return (Decision.DENY, _REASON_UNKNOWN_ROLE)
    if file_id not in VALID_FILES:
        return (Decision.DENY, _REASON_UNKNOWN_FILE)
    if action not in VALID_ACTIONS:
        return (Decision.DENY, _REASON_UNKNOWN_ACTION)

    # ── 查表判定 ──
    key = (role, file_id, action)
    result = POLICY_TABLE.get(key)
    if result is None:
        return (Decision.DENY, _REASON_NO_RULE)

    return result


def is_executable(decision: Decision) -> bool:
    """
    判断某决策是否允许执行实际文件操作。

    只有 ALLOW 才允许执行；DENY 和 PENDING_APPROVAL 都必须拦截。
    """
    return decision == Decision.ALLOW
