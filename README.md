# Assistant - 多租户智能体框架

面向中小企业的多租户 AI 智能体 SaaS 平台。纯自主引擎，DDD 架构，支持多渠道接入、行业技能插件化、MCP 协议扩展。

## 技术栈

- **后端**: Python 3.10+ / FastAPI / SQLAlchemy (async)
- **LLM 网关**: LiteLLM（统一接入 DeepSeek、Qwen、Zhipu、OpenAI 等）
- **数据库**: SQLite（开发）/ PostgreSQL 15（生产）+ Redis 7
- **协议**: Claude Skill 规范 + MCP (Model Context Protocol)
- **监控**: Prometheus + Grafana + 飞书告警
- **容器**: Docker Compose + Nginx + Certbot (HTTPS)
- **架构**: DDD 分层（UI → App → Domain → Infrastructure）

## 项目结构

```
├── src/assistant/                 # 核心应用
│   ├── main.py                    # FastAPI 入口 + 生命周期管理
│   ├── app/                       # 应用层（AppServices、UseCases）
│   │   └── services/
│   │       ├── assistant_chat_app_service.py  # 对话编排 + 工具循环
│   │       └── billing_service.py             # 账单报表
│   ├── domain/                    # 领域层
│   │   ├── entities/              # Tenant, Message, Conversation, Product, Skill
│   │   ├── models/                # TenantContext, LLMConfig
│   │   ├── ports/                 # ILLMChatPort, IToolGateway（出站端口）
│   │   ├── repositories/          # 仓储接口
│   │   ├── services/              # ConversationContextService（上下文管理+自动摘要）
│   │   └── value_objects/         # ApiKey, Quota, Channel
│   ├── infrastructure/            # 基础设施层
│   │   ├── alerting/              # 飞书告警（FeishuAlerter）
│   │   ├── config/                # Settings（pydantic-settings + .env）
│   │   ├── external_services/     # LiteLLMAdapter, ToolGatewayAdapter
│   │   ├── mcp/                   # MCP Client（stdio + SSE）
│   │   ├── metrics.py             # Prometheus 11 项指标
│   │   ├── middleware/             # TenantAuthMiddleware（Bearer API Key）
│   │   ├── persistence/           # SQLAlchemy ORM + Repository 实现
│   │   └── skill_loader.py        # Claude Skill 规范加载器（YAML + PyYAML）
│   └── ui/http/routes/            # 表现层
│       ├── chat.py                # POST /v1/chat（统一对话端点）
│       ├── wechat.py              # 微信公众号 Webhook
│       ├── billing.py             # 账单 + 用量 API
│       ├── skills.py              # 技能管理 API
│       ├── adapters/              # 渠道适配器
│       │   └── wechat_adapter.py  # 微信 XML 解析/签名/回复
│       └── ...
├── skills/                        # 行业技能包（Claude Skill 规范）
│   ├── weather_query/             # 天气查询（2 工具）
│   ├── express_query/             # 快递查询（2 工具）
│   └── elder_care/                # 社区养老关怀（4 工具）
│       ├── SKILL.md               # 技能定义 + 工具 Schema
│       ├── references/            # system.md（人设）+ rules.md（业务规则）
│       └── scripts/               # 可执行脚本
├── monitoring/                    # 监控配置
│   ├── prometheus.yml
│   ├── alert_rules.yml            # 4 条告警规则
│   └── grafana/
│       ├── dashboards/agent_overview.json  # 8 面板仪表盘
│       └── datasources/prometheus.yml
├── scripts/
│   └── backup.sh                  # 数据库自动备份（pg_dump + gzip + OSS）
├── nginx/                         # Nginx 反向代理 + SSL
├── init.sql                       # 数据库 Schema（Docker 自动建表）
├── docker-compose.yml             # 容器编排（10 个服务）
└── .env                           # 环境变量
```

## 核心特性

### 多租户引擎
- Bearer API Key 认证（`TenantAuthMiddleware`）
- 租户数据完全隔离（session + DB 级别）
- 每租户独立配置：模型选择、技能白名单、上下文窗口大小、配额限制
- 开发模式（`AUTH_ENABLED=false`）自动注入默认租户

### 统一对话端点
- `POST /v1/chat` — 认证 → 多租户隔离 → 上下文管理 → LLM 路由 → 技能调用 → 响应
- 工具思考循环（最多 5 轮），自动执行 tool_calls
- 上下文滑动窗口（默认 10 轮，最大 50 轮），超长自动摘要

### 行业技能系统
- Claude Skill 规范（SKILL.md + 三级加载：元数据 → 主体 → 按需脚本/知识）
- 支持完整的 OpenAI Tools JSON Schema（YAML frontmatter 定义）
- 动态工具执行（scripts/ 目录下同名 .py 脚本）
- 已内置 3 个技能 8 个工具：天气查询、快递查询、社区养老关怀

### MCP 协议
- 支持 stdio 和 SSE 两种传输方式
- 自动发现 MCP Server 工具并注册
- 本地技能 → MCP 工具自动路由

### 渠道适配
- 微信公众号（XML 消息解析 + 签名验证 + 语音识别）
- Web API（REST）
- 可扩展：飞书、钉钉、企业微信

### 监控告警
- 11 项 Prometheus 指标（对话量/延迟/Token/费用/工具调用/错误率）
- Grafana 8 面板仪表盘（开箱即用）
- 飞书 Webhook 告警（高延迟/高错误率/配额/无活动）
- AlertManager 4 条告警规则

### 运营能力
- 数据库每日自动备份（pg_dump + gzip + 30 天保留 + OSS 上传）
- HTTPS 自动证书（Certbot + Let's Encrypt）
- API 用量账单（按月/按模型/按技能/按渠道统计，CSV 导出）

## 快速开始

### 开发模式（本地 WSL/macOS）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY 等

# 3. 启动服务（SQLite，无需 Docker）
cd src
uvicorn assistant.main:app --host 0.0.0.0 --port 8000

# 4. 测试
curl http://localhost:8000/health
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"你好","user_id":"u1"}'
```

### 生产部署（Docker Compose）

```bash
# 1. 配置 .env
cp .env.example .env
# 编辑 .env，填入生产配置

# 2. 一键部署
docker-compose up -d

# 包含 10 个服务：
# agent-engine, postgres, pgvector, redis, minio,
# nginx, certbot, prometheus, grafana, backup

# 3. 验证
curl https://your-domain/health
```

### 认证模式

```bash
# 开发模式（无需 token）
AUTH_ENABLED=false

# 生产模式（Bearer API Key）
AUTH_ENABLED=true
curl -X POST http://localhost:8000/v1/chat \
  -H "Authorization: Bearer ak_tenant_a_key_001" \
  -H "Content-Type: application/json" \
  -d '{"message":"你好","user_id":"u1"}'
```

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/v1/chat` | POST | 统一对话（需认证） |
| `/v1/chat/history/{session_id}` | GET | 对话历史 |
| `/v1/skills` | GET | 技能列表 |
| `/v1/skills/{id}` | GET | 技能详情 |
| `/v1/skills/{id}/references/{name}` | GET | 参考文档 |
| `/v1/admin/tenants/{id}/billing` | GET | 月度账单 |
| `/v1/admin/tenants/{id}/billing/export` | GET | 账单 CSV 导出 |
| `/v1/admin/tenants/{id}/usage` | GET | 近期用量统计 |
| `/webhook/wechat/{tenant_id}` | GET | 微信服务器验证 |
| `/webhook/wechat/{tenant_id}` | POST | 微信消息接收 |
| `/metrics` | GET | Prometheus 指标 |

## 添加新技能

```bash
# 1. 创建技能目录
mkdir -p skills/my_skill/{references,scripts}

# 2. 编写 SKILL.md（YAML frontmatter + Markdown body）
cat > skills/my_skill/SKILL.md << 'EOF'
---
name: my_skill
description: 我的自定义技能
version: 1.0.0
tools:
  - name: my_tool
    description: 工具描述
    parameters:
      type: object
      properties:
        query:
          type: string
          description: 查询内容
      required:
        - query
---

# 我的技能

技能说明和使用方法。
EOF

# 3. 实现工具脚本
cat > skills/my_skill/scripts/my_tool.py << 'EOF'
import argparse, json
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    args = parser.parse_args()
    print(json.dumps({"result": f"查询结果: {args.query}"}))
if __name__ == "__main__":
    main()
EOF

# 4. 重启服务，技能自动加载
```

## 文档

- [落地方案](docs/落地方案.md) — 8 周执行路线图（Phase 1-4 已完成）
- [PRD](docs/PRD.md) — 产品需求文档
- [DESIGN](docs/DESIGN.md) — 技术设计文档
- [API_SPEC](docs/API_SPEC.md) — API 接口规范
- [SKILL_SDK](docs/SKILL_SDK.md) — 技能开发 SDK

## 许可证

MIT
