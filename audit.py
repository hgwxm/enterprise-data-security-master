"""
audit.py — 审计日志服务

使用 SQLite 持久化记录每一次访问请求和权限判定结果。
每条记录包含 9 个统一字段：id, timestamp, request_id, user_role,
file_id, action, decision, reason, executed。

审计日志不可篡改：仅支持插入和查询，不提供更新和删除接口。
"""

import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from policy import Decision


# ── 数据库路径 ──
_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_DB_PATH = os.path.join(_DB_DIR, "audit.db")

# 线程锁，保证 SQLite 写入线程安全
_lock = threading.Lock()


def _get_connection() -> sqlite3.Connection:
    """获取 SQLite 连接，自动建库建表。"""
    os.makedirs(_DB_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init_db():
    """初始化数据库表。"""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT    NOT NULL,
                request_id  TEXT    NOT NULL,
                user_role   TEXT    NOT NULL,
                file_id     TEXT    NOT NULL,
                action      TEXT    NOT NULL,
                decision    TEXT    NOT NULL,
                reason      TEXT    NOT NULL,
                executed    INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_request_id
            ON audit_log (request_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_decision
            ON audit_log (decision)
        """)
        conn.commit()
    finally:
        conn.close()


# 模块加载时自动初始化
_init_db()


def _utc_now() -> str:
    """返回当前 UTC 时间的 ISO 格式字符串。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def log_access(
    request_id: str,
    user_role: str,
    file_id: str,
    action: str,
    decision: Decision,
    reason: str,
    executed: bool,
) -> Dict[str, Any]:
    """
    记录一条审计日志。

    Args:
        request_id:  请求唯一编号
        user_role:   用户角色
        file_id:     文件编号
        action:      操作类型
        decision:    判定结果（Decision 枚举）
        reason:      判定原因
        executed:    是否实际执行了文件操作

    Returns:
        本次记录的字典形式
    """
    timestamp = _utc_now()
    executed_int = 1 if executed else 0
    decision_str = decision.value if isinstance(decision, Decision) else str(decision)

    with _lock:
        conn = _get_connection()
        try:
            conn.execute(
                """
                INSERT INTO audit_log
                    (timestamp, request_id, user_role, file_id, action, decision, reason, executed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (timestamp, request_id, user_role, file_id, action,
                 decision_str, reason, executed_int),
            )
            conn.commit()
        finally:
            conn.close()

    return {
        "timestamp": timestamp,
        "request_id": request_id,
        "user_role": user_role,
        "file_id": file_id,
        "action": action,
        "decision": decision_str,
        "reason": reason,
        "executed": executed,
    }


def get_logs(
    decision_filter: Optional[str] = None,
    exec_filter: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """
    查询审计日志。

    Args:
        decision_filter: 按判定筛选（"ALLOW" / "DENY" / "PENDING_APPROVAL" / None=全部）
        exec_filter:     按执行状态筛选（"yes" / "no" / None=全部）
        keyword:         搜索关键词（匹配 request_id / file_id / user_role / reason）
        limit:           最多返回条数

    Returns:
        日志记录列表，按时间倒序排列
    """
    sql = "SELECT * FROM audit_log WHERE 1=1"
    params: list = []

    if decision_filter and decision_filter != "ALL":
        sql += " AND decision = ?"
        params.append(decision_filter)

    if exec_filter == "yes":
        sql += " AND executed = 1"
    elif exec_filter == "no":
        sql += " AND executed = 0"

    if keyword:
        kw = f"%{keyword}%"
        sql += " AND (request_id LIKE ? OR file_id LIKE ? OR user_role LIKE ? OR reason LIKE ?)"
        params.extend([kw, kw, kw, kw])

    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with _lock:
        conn = _get_connection()
        try:
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    return [_row_to_dict(r) for r in rows]


def get_stats() -> Dict[str, int]:
    """
    获取审计日志统计信息。

    Returns:
        {"total": N, "allow": N, "deny": N, "pending": N}
    """
    with _lock:
        conn = _get_connection()
        try:
            total = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
            allow = conn.execute(
                "SELECT COUNT(*) FROM audit_log WHERE decision = 'ALLOW'"
            ).fetchone()[0]
            deny = conn.execute(
                "SELECT COUNT(*) FROM audit_log WHERE decision = 'DENY'"
            ).fetchone()[0]
            pending = conn.execute(
                "SELECT COUNT(*) FROM audit_log WHERE decision = 'PENDING_APPROVAL'"
            ).fetchone()[0]
        finally:
            conn.close()

    return {"total": total, "allow": allow, "deny": deny, "pending": pending}


def clear_all() -> int:
    """
    清空全部审计日志（仅供演示"清空日志"按钮使用）。

    Returns:
        被删除的记录数
    """
    with _lock:
        conn = _get_connection()
        try:
            count = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
            conn.execute("DELETE FROM audit_log")
            conn.commit()
        finally:
            conn.close()
    return count


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """将 sqlite3.Row 转换为字典。"""
    return {
        "id": row["id"],
        "timestamp": row["timestamp"],
        "request_id": row["request_id"],
        "user_role": row["user_role"],
        "file_id": row["file_id"],
        "action": row["action"],
        "decision": row["decision"],
        "reason": row["reason"],
        "executed": bool(row["executed"]),
    }
