"""
app.py — Flask 后端服务

提供网页所需的全部后端接口，并与现有网页对接。

接口列表：
  POST   /api/access         权限判定 + 文件操作统一入口
  GET    /api/audit/logs     查询审计日志
  GET    /api/audit/stats    审计日志统计
  DELETE /api/audit/clear    清空审计日志
  GET    /api/files          受保护文件列表
  GET    /api/health         健康检查

页面路由：
  GET /         → index.html（访问控制台）
  GET /audit    → audit.html（审计日志）
  GET /rules    → rules.html（权限规则）
  GET /about    → about.html（系统说明）
"""

import os
import uuid
from datetime import datetime, timezone

from flask import Flask, request, jsonify, send_file, render_template, abort

from policy import Decision, check_permission, is_executable
from file_service import read_file, export_file, get_file_list, FILE_REGISTRY
import audit

# ── Flask 应用配置 ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    static_url_path="/static",
    template_folder=BASE_DIR,  # HTML 文件在项目根目录
)
app.config["JSON_AS_ASCII"] = False


# ── 工具函数 ──

def _generate_request_id() -> str:
    """生成请求唯一编号：REQ + 时间戳 + 随机后缀。"""
    now = datetime.now(timezone.utc)
    suffix = uuid.uuid4().hex[:6].upper()
    return f"REQ{now.strftime('%Y%m%d%H%M%S')}{suffix}"


def _utc_now() -> str:
    """返回当前 UTC 时间字符串。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ══════════ API 接口 ══════════

@app.route("/api/access", methods=["POST"])
def api_access():
    """
    权限判定 + 文件操作统一入口。

    请求体（JSON 或 form-data）：
        user_role: 用户角色
        file_id:   文件编号
        action:    操作类型（read / export）

    响应：
        {
            "request_id": "REQ...",
            "decision":   "ALLOW" / "DENY" / "PENDING_APPROVAL",
            "reason":     "判定原因",
            "executed":   true / false,
            "timestamp":  "2026-10-13 13:00:00"
        }
    """
    # 兼容 JSON 和 form-data
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form

    role = data.get("user_role", "")
    file_id = data.get("file_id", "")
    action = data.get("action", "")

    # ── 权限判定 ──
    decision, reason = check_permission(role, file_id, action)
    request_id = _generate_request_id()
    timestamp = _utc_now()

    # ── 执行文件操作（仅 ALLOW） ──
    executed = False
    if is_executable(decision):
        if action == "read":
            result = read_file(role, file_id)
            executed = result.success
        elif action == "export":
            result = export_file(role, file_id)
            executed = result.success
        # action 已通过 check_permission 验证，此处无需 else

    # ── 记录审计日志 ──
    audit.log_access(
        request_id=request_id,
        user_role=role,
        file_id=file_id,
        action=action,
        decision=decision,
        reason=reason,
        executed=executed,
    )

    return jsonify({
        "request_id": request_id,
        "decision": decision.value,
        "reason": reason,
        "executed": executed,
        "timestamp": timestamp,
    })


@app.route("/api/audit/logs", methods=["GET"])
def api_audit_logs():
    """查询审计日志，支持筛选和搜索。"""
    decision_filter = request.args.get("decision", None)
    exec_filter = request.args.get("executed", None)
    keyword = request.args.get("keyword", None)
    limit = request.args.get("limit", 200, type=int)

    logs = audit.get_logs(
        decision_filter=decision_filter,
        exec_filter=exec_filter,
        keyword=keyword,
        limit=limit,
    )
    return jsonify({"logs": logs, "count": len(logs)})


@app.route("/api/audit/stats", methods=["GET"])
def api_audit_stats():
    """审计日志统计。"""
    return jsonify(audit.get_stats())


@app.route("/api/audit/clear", methods=["POST", "DELETE"])
def api_audit_clear():
    """清空审计日志。"""
    deleted = audit.clear_all()
    return jsonify({"deleted": deleted})


@app.route("/api/files", methods=["GET"])
def api_files():
    """受保护文件列表。"""
    return jsonify({"files": get_file_list()})


@app.route("/api/health", methods=["GET"])
def api_health():
    """健康检查。"""
    return jsonify({"status": "ok", "service": "AegisData"})


# ══════════ 页面路由 ══════════

@app.route("/")
def page_console():
    """访问控制台。"""
    return send_file(os.path.join(BASE_DIR, "index.html"))


@app.route("/audit")
def page_audit():
    """审计日志页。"""
    return send_file(os.path.join(BASE_DIR, "audit.html"))


@app.route("/rules")
def page_rules():
    """权限规则页。"""
    return send_file(os.path.join(BASE_DIR, "rules.html"))


@app.route("/about")
def page_about():
    """系统说明页。"""
    return send_file(os.path.join(BASE_DIR, "about.html"))


# ══════════ 启动 ══════════

if __name__ == "__main__":
    import socket

    def _get_lan_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    lan_ip = _get_lan_ip()
    print("=" * 60)
    print("AegisData 企业数据安全管理平台 — 后端服务")
    print("=" * 60)
    print(f"权限规则：3 角色 × 3 文件 × 2 操作 = 18 条规则")
    print(f"审计数据库：{os.path.join(BASE_DIR, 'data', 'audit.db')}")
    print(f"本机访问：  http://127.0.0.1:5000")
    print(f"局域网访问：http://{lan_ip}:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
