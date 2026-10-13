# AegisData 企业数据安全管理平台

企业数据访问权限控制、风险识别与审计管理系统。

## 项目简介

本系统实现基于角色的文件访问权限控制（RBAC），支持三种决策：

- **ALLOW** — 允许操作，后端执行文件读取/导出
- **DENY** — 拒绝操作，后端拦截，不执行任何文件操作
- **PENDING_APPROVAL** — 待审批，后端拦截，不执行任何文件操作

### 权限规则（3 角色 × 3 文件 × 2 操作 = 18 条）

| 角色 \ 文件 | F001 普通业务报告 | F002 内部财务报告 | F003 敏感工资表 |
|---|---|---|---|
| employee（普通员工） | 读 ✅ 导 ✅ | 读 ❌ 导 ⏳ | 读 ❌ 导 ❌ |
| finance（财务人员） | 读 ✅ 导 ✅ | 读 ✅ 导 ✅ | 读 ❌ 导 ❌ |
| admin（管理员） | 读 ✅ 导 ✅ | 读 ✅ 导 ✅ | 读 ✅ 导 ✅ |

> ✅ = ALLOW　❌ = DENY　⏳ = PENDING_APPROVAL

规则来源：`permission.docx`（C 提供），严格遵循，不做任何修改。

## 项目结构

```
enterprise-data-security-master/
├── app.py              # Flask 后端服务（API 接口 + 页面路由）
├── policy.py           # 权限判断引擎（18 条规则 + 无效输入安全处理）
├── file_service.py     # 受保护文件读取与导出服务
├── audit.py            # 审计日志服务（SQLite 持久化）
├── requirements.txt    # Python 依赖
├── README.md           # 项目说明（本文件）
│
├── static/             # 前端静态资源
│   ├── style.css       # 样式表
│   └── app.js          # 前端交互逻辑
│
├── index.html          # 访问控制台
├── audit.html          # 审计日志页
├── rules.html          # 权限规则页
├── about.html          # 系统说明页
├── 单文件版.html       # 单文件版（所有页面合并）
│
├── tests/              # 测试目录
│   ├── test_policy.py      # 权限判断测试（8 条用例 + 无效输入测试）
│   ├── test_file_service.py # 文件访问控制测试
│   └── test_app.py         # 后端接口测试
│
├── data/               # 运行时自动创建
│   └── audit.db       # SQLite 审计日志数据库
│
├── permission.docx     # 权限规则说明（C 提供）
├── file-list.docx      # 文件清单说明（C 提供）
└── test_cases.xlsx     # 测试用例（C 提供）
```

## 环境要求

- Python 3.10+
- pip

## 安装依赖

```bash
pip install -r requirements.txt
```

依赖列表：

- **Flask** — Web 框架
- **openpyxl** — 读取测试用例 Excel 文件
- **pytest** — 测试框架

## 启动服务

```bash
python app.py
```

启动后访问 http://127.0.0.1:5000 即可打开访问控制台。

### 页面说明

| URL | 页面 | 说明 |
|---|---|---|
| `/` | 访问控制台 | 选择角色、文件、操作，提交权限判定请求 |
| `/audit` | 审计日志 | 查看所有访问请求的判定记录，支持筛选和搜索 |
| `/rules` | 权限规则 | 展示完整的权限矩阵 |
| `/about` | 系统说明 | 项目介绍和架构说明 |

### API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/access` | 权限判定 + 文件操作统一入口 |
| GET | `/api/audit/logs` | 查询审计日志（支持 decision/keyword/limit 筛选） |
| GET | `/api/audit/stats` | 审计日志统计 |
| POST | `/api/audit/clear` | 清空审计日志 |
| GET | `/api/files` | 受保护文件列表 |
| GET | `/api/health` | 健康检查 |

#### POST /api/access 请求示例

```json
{
  "user_role": "employee",
  "file_id": "F001",
  "action": "read"
}
```

#### 响应示例

```json
{
  "request_id": "REQ20261013130000A1B2C3",
  "decision": "ALLOW",
  "reason": "该角色对该文件有读取权限",
  "executed": true,
  "timestamp": "2026-10-13 13:00:00"
}
```

## 运行测试

```bash
python -m pytest tests/ -v
```

测试覆盖：

- **test_policy.py** — 8 条权限矩阵用例（T001-T008，来自 `test_cases.xlsx`）+ 9 条无效输入安全处理测试 + 3 条 `is_executable` 测试
- **test_file_service.py** — 14 条文件读取/导出测试，验证 DENY 和 PENDING_APPROVAL 时不执行文件操作
- **test_app.py** — 17 条接口测试，覆盖所有 API 端点和页面路由

## 模块职责

| 模块 | 职责 |
|---|---|
| `policy.py` | 权限查表判定，无效输入安全处理（默认拒绝） |
| `file_service.py` | 文件读取/导出，非 ALLOW 一律拦截 |
| `audit.py` | SQLite 审计日志，记录每次请求和判定结果 |
| `app.py` | Flask 后端，提供 API 接口和页面路由 |
| `static/app.js` | 前端交互，调用后端 API 渲染结果 |

## 安全设计

- **默认拒绝**：所有无效输入（未知角色/文件/操作、None、空串、类型错误）一律返回 DENY
- **后端拦截**：DENY 和 PENDING_APPROVAL 的请求在后端被拦截，不执行任何文件操作，不仅依赖前端提示
- **审计留痕**：每次请求都记录到 SQLite 审计日志，包含时间戳、请求 ID、角色、文件、操作、判定结果和执行状态
- **虚构数据**：所有文件内容均为虚构数据，不含真实企业信息

## 团队分工

- **A**（后端）：`policy.py`、`file_service.py`、`audit.py`、`app.py`、测试
- **B**（前端）：`index.html`、`audit.html`、`rules.html`、`about.html`、`static/app.js`、`static/style.css`
- **C**（规范）：`permission.docx`、`file-list.docx`、`test_cases.xlsx`
