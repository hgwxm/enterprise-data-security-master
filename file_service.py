"""
file_service.py — 受保护文件读取与导出服务

负责对 F001/F002/F003 三个受保护文件执行读取和导出操作。
所有操作前必须先经过 policy.check_permission 判定：
  - ALLOW           → 执行操作并返回结果
  - DENY            → 拦截，不执行任何文件操作
  - PENDING_APPROVAL → 拦截，不执行任何文件操作，等待审批

文件内容均为虚构数据，不含真实企业信息。
"""

import io
import json
from typing import Optional, Tuple, Dict, Any

from policy import Decision, check_permission, is_executable


# ── 受保护文件注册表 ──
# 对应 file-list.docx（C 提供）中的三个文件。
FILE_REGISTRY = {
    "F001": {
        "id": "F001",
        "name": "普通业务报告",
        "description": "各部门日常业务进展汇总，所有角色可读可导出",
        "format": "json",
    },
    "F002": {
        "id": "F002",
        "name": "内部财务报告",
        "description": "公司内部财务数据，仅财务人员和管理员可读可导出",
        "format": "json",
    },
    "F003": {
        "id": "F003",
        "name": "敏感工资表",
        "description": "员工薪资明细，仅管理员可读可导出",
        "format": "json",
    },
}

# ── 虚构文件内容 ──
# 全部为演示用虚构数据，不含任何真实企业信息。
_FILE_CONTENTS = {
    "F001": {
        "title": "2026年Q3普通业务报告",
        "department": "业务部",
        "summary": "本季度业务进展顺利，新增客户 12 家，完成项目 8 个。",
        "metrics": {"new_clients": 12, "completed_projects": 8, "satisfaction": 0.92},
        "note": "本文件为虚构数据，仅供权限系统演示使用。",
    },
    "F002": {
        "title": "2026年Q3内部财务报告",
        "department": "财务部",
        "revenue": 12500000,
        "expenditure": 8300000,
        "net_profit": 4200000,
        "note": "本文件为虚构数据，仅供权限系统演示使用。",
    },
    "F003": {
        "title": "2026年9月工资表",
        "department": "人力资源部",
        "records": [
            {"name": "张三（虚构）", "position": "工程师", "salary": 18000},
            {"name": "李四（虚构）", "position": "经理",   "salary": 25000},
            {"name": "王五（虚构）", "position": "总监",   "salary": 35000},
        ],
        "note": "本文件为虚构数据，仅供权限系统演示使用。",
    },
}


class FileAccessResult:
    """
    文件访问操作的结果。

    Attributes:
        success:      操作是否成功执行（仅 ALLOW 时为 True）
        decision:     权限判定结果
        reason:       判定原因
        content:      文件内容（仅 ALLOW 读取时有值）
        export_data:  导出数据字节流（仅 ALLOW 导出时有值）
        file_info:    文件元信息
    """

    def __init__(self, success: bool, decision: Decision, reason: str,
                 content: Optional[Dict] = None,
                 export_data: Optional[bytes] = None,
                 file_info: Optional[Dict] = None):
        self.success = success
        self.decision = decision
        self.reason = reason
        self.content = content
        self.export_data = export_data
        self.file_info = file_info

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 响应）。"""
        d = {
            "success": self.success,
            "decision": self.decision.value,
            "reason": self.reason,
        }
        if self.content is not None:
            d["content"] = self.content
        if self.file_info is not None:
            d["file_info"] = self.file_info
        return d


def _get_file_info(file_id: str) -> Optional[Dict]:
    """获取文件元信息。"""
    return FILE_REGISTRY.get(file_id)


def read_file(role: str, file_id: str) -> FileAccessResult:
    """
    读取受保护文件。

    流程：
    1. 调用 policy.check_permission 判定权限
    2. 仅当判定为 ALLOW 时才读取文件内容
    3. DENY / PENDING_APPROVAL 一律拦截，不执行读取

    Args:
        role:    用户角色
        file_id: 文件编号

    Returns:
        FileAccessResult: 包含判定结果和（可能的）文件内容
    """
    decision, reason = check_permission(role, file_id, "read")
    file_info = _get_file_info(file_id)

    # ── 安全拦截：非 ALLOW 一律不执行文件操作 ──
    if not is_executable(decision):
        return FileAccessResult(
            success=False,
            decision=decision,
            reason=reason,
            file_info=file_info,
        )

    # ── 执行读取 ──
    content = _FILE_CONTENTS.get(file_id, {})
    return FileAccessResult(
        success=True,
        decision=decision,
        reason=reason,
        content=content,
        file_info=file_info,
    )


def export_file(role: str, file_id: str) -> FileAccessResult:
    """
    导出受保护文件。

    流程：
    1. 调用 policy.check_permission 判定权限
    2. 仅当判定为 ALLOW 时才生成导出数据
    3. DENY / PENDING_APPROVAL 一律拦截，不执行导出

    导出格式为 JSON 字节流。

    Args:
        role:    用户角色
        file_id: 文件编号

    Returns:
        FileAccessResult: 包含判定结果和（可能的）导出数据
    """
    decision, reason = check_permission(role, file_id, "export")
    file_info = _get_file_info(file_id)

    # ── 安全拦截：非 ALLOW 一律不执行文件操作 ──
    if not is_executable(decision):
        return FileAccessResult(
            success=False,
            decision=decision,
            reason=reason,
            file_info=file_info,
        )

    # ── 执行导出：生成 JSON 字节流 ──
    content = _FILE_CONTENTS.get(file_id, {})
    export_data = json.dumps(
        {"file_id": file_id, "file_info": file_info, "content": content},
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")

    return FileAccessResult(
        success=True,
        decision=decision,
        reason=reason,
        export_data=export_data,
        file_info=file_info,
    )


def get_file_list() -> list:
    """返回所有受保护文件的元信息列表。"""
    return list(FILE_REGISTRY.values())
