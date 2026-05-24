# Agent Framework - 技术设计文档

## 文档信息
- **项目名称**: Agent Framework（智能体框架）
- **版本**: v2.0
- **日期**: 2026-05-17
- **状态**: 设计中（去 Dify 架构演进版）

---

## 1. 设计目标

### 1.1 核心定位
面向中小企业提供**行业定制智能体**服务的多租户 SaaS 平台。

### 1.2 设计原则
1. **纯自主引擎**：去中心化架构，彻底剥离 Dify 依赖，采用 `LiteLLM` 作为大模型网关协议统一层，核心业务流（上下文管理、工具循环）完全自主掌控。
2. **多租户数据隔离**：强隔离机制，精细化管理租户与用户维度的模型选用与成本计费（Token 计算）。
3. **领域驱动设计 (DDD)**：按 `ui`（表现层） -> `app`（应用层） -> `domain`（领域层） -> `infra`（基础设施层）解耦，提升业务复杂度管理。
4. **低运维成本**：轻量级依赖，Docker 部署。
5. **可扩展**：支持 MCP 协议接入，以及通过技能插件化实现行业定制。

---

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        客户端层                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Web网页  │  │ 微信小程序 │  │   Taro   │  │  嵌入组件 │       │
│  │          │  │          │  │  (iOS/安卓)│  │          │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
└───────┼─────────────┼─────────────┼─────────────┼───────────────┘
        │             │             │             │
        └─────────────┴──────┬──────┴─────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                      FastAPI 服务集群 (DDD 分层)                │
│  ┌─────────────────────────┴──────────────────────────────┐    │
│  │              API Gateway (Nginx / Traefik)              │    │
│  │              认证 / 限流 / 路由 / SSL                    │    │
│  └─────────────────────────┬──────────────────────────────┘    │
│                            │                                     │
│  ┌─────────────────────────┴──────────────────────────────┐    │
│  │     UI层 (表现层)                                       │    │
│  │     REST API、渠道Webhook（微信/钉钉）、管理后台接口          │    │
│  └─────────────────────────┬──────────────────────────────┘    │
│                            │                                     │
│  ┌─────────────────────────┴──────────────────────────────┐    │
│  │     App层 (应用层 - AppServices)                        │    │
│  │     AssistantChatAppService、EcommerceChatAppService    │    │
│  └─────────────────────────┬──────────────────────────────┘    │
│                            │                                     │
│  ┌─────────────────────────┴──────────────────────────────┐    │
│  │     Domain层 (领域层)                                   │    │
│  │     Entities (Message, Tenant)                          │    │
│  │     Domain Services (ConversationContextService)        │    │
│  │     Outbound Ports (ILLMChatPort, IToolGateway)         │    │
│  └─────────────────────────┬──────────────────────────────┘    │
│                            │                                     │
│  ┌─────────────────────────┴──────────────────────────────┐    │
│  │     Infra层 (基础设施层)                                │    │
│  │     LiteLLM Adapter (大模型网关路由)                      │    │
│  │     PostgreSQL Repository, Skill/MCP Executor           │    │
│  └─────────────────────────┬──────────────────────────────┘    │
└────────────────────────────┼────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                      基础设施环境                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │PostgreSQL│  │  Redis   │  │  MinIO   │  │  Nginx   │       │
│  │          │  │          │  │          │  │          │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 分层说明

| 层级 | 组件 | 职责 | 技术选型 |
|------|------|------|----------|
| **客户端层** | Web/小程序/APP | 用户交互界面 | React / Taro / 微信小程序 |
| **API网关** | API Gateway | 统一入口、认证、限流 | Nginx / Traefik |
| **UI 层** | HTTP 路由 | 解析参数，身份鉴权，组装 `TenantContext`，返回 JSON | FastAPI |
| **App 层** | AppServices | 业务场景编排，依赖领域对象和抽象端口 | Python |
| **Domain 层** | Domain Services | 核心业务规则（会话历史截断、计费抽象） | Python |
| **Infra 层** | LiteLLM Adapter | 统一不同 LLM 厂商的调用协议、计算 Token 成本 | LiteLLM |
| | PostgreSQL | 业务及对话数据持久化 | PostgreSQL 15 |
| | Redis | 缓存、限流 | Redis 7 |
| | MinIO | 附件/图片对象存储 | MinIO |

---

## 3. 核心模块设计

### 3.1 客户管理面板（Tenant Portal）

#### 功能模块

```
Tenant Portal
├── 登录/注册
│   └── 手机号 + 验证码
├── 仪表盘
│   ├── 今日对话数
│   ├── 今日新增客户
│   ├── API 用量
│   └── 告警通知
├── 对话管理
│   ├── 实时对话列表
│   ├── 历史记录查看
│   ├── 对话导出（Excel）
│   └── 对话标注
├── 机器人配置
│   ├── 欢迎语设置
│   ├── 菜单/知识库编辑
│   ├── 工作时间设置
│   ├── 自动转人工规则
│   └── 品牌样式（颜色、头像）
├── 数据统计
│   ├── 对话趋势图
│   ├── 热门问题 TOP10
│   ├── 客户满意度
│   ├── 响应时间统计
│   └── 技能使用分布
├── 渠道管理
│   ├── 微信公众号接入
│   ├── 微信小程序接入
│   ├── 网站嵌入代码
│   └── 飞书/钉钉接入
└── 账户管理
    ├── 套餐信息
    ├── 用量明细
    ├── 充值/续费
    └── 发票申请
```

#### 技术设计

- **前端**: React + Ant Design + ECharts（图表）
- **后端 API**: FastAPI（Python）
- **数据库**: PostgreSQL（租户隔离）
- **部署**: Docker + Nginx

---

### 3.2 渠道适配器（Channel Adapters）

#### 设计思路

每个渠道一个适配器，统一消息格式：

```
微信消息 ──→ 微信适配器 ──→ UI 层 (API)
飞书消息 ──→ 飞书适配器 ──→ UI 层 (API)
钉钉消息 ──→ 钉钉适配器 ──→ UI 层 (API)
Web消息 ───→ Web适配器 ───→ UI 层 (API)
```

#### 统一消息格式

```json
{
  "message_id": "msg_abc123",
  "channel": "wechat",        // wechat / feishu / dingtalk / web
  "tenant_id": "tnt_xxx",
  "user_id": "user_xxx",
  "session_id": "sess_xxx",
  "content": "用户消息内容",
  "content_type": "text",     // text / image / voice / file
  "timestamp": "2026-05-16T10:00:00Z",
  "metadata": {
    "openid": "wx_xxx",
    "nickname": "用户昵称",
    "avatar": "https://..."
  }
}
```

#### 微信适配器设计

```python
# adapters/wechat_adapter.py
from fastapi import APIRouter, Request
import xml.etree.ElementTree as ET
import hashlib
import time

router = APIRouter()

class WechatAdapter:
    """微信渠道适配器"""
    
    def __init__(self, config):
        self.app_id = config["app_id"]
        self.app_secret = config["app_secret"]
        self.token = config["token"]
        self.encoding_aes_key = config.get("encoding_aes_key")
    
    async def handle_message(self, request: Request) -> dict:
        """处理微信消息"""
        # 1. 验证签名
        signature = request.query_params.get("signature")
        timestamp = request.query_params.get("timestamp")
        nonce = request.query_params.get("nonce")
        
        if not self.verify_signature(signature, timestamp, nonce):
            return {"error": "Invalid signature"}
        
        # 2. 解析 XML 消息
        body = await request.body()
        xml_data = ET.fromstring(body)
        
        msg_type = xml_data.find("MsgType").text
        from_user = xml_data.find("FromUserName").text
        to_user = xml_data.find("ToUserName").text
        content = xml_data.find("Content").text if xml_data.find("Content") else ""
        
        # 3. 转换为统一格式
        unified_msg = {
            "message_id": f"wx_{xml_data.find('MsgId').text if xml_data.find('MsgId') else int(time.time() * 1000)}",
            "channel": "wechat",
            "tenant_id": self.get_tenant_by_appid(self.app_id),
            "user_id": from_user,
            "session_id": f"sess_{from_user}",
            "content": content,
            "content_type": self.map_msg_type(msg_type),
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "openid": from_user,
                "app_id": self.app_id
            }
        }
        
        return unified_msg
    
    def map_msg_type(self, wx_type: str) -> str:
        """微信消息类型映射"""
        type_map = {
            "text": "text",
            "image": "image",
            "voice": "voice",
            "video": "video",
            "location": "location",
            "link": "link"
        }
        return type_map.get(wx_type, "text")
    
    def verify_signature(self, signature, timestamp, nonce):
        """验证微信签名"""
        tmp_list = [self.token, timestamp, nonce]
        tmp_list.sort()
        tmp_str = "".join(tmp_list)
        hashcode = hashlib.sha1(tmp_str.encode()).hexdigest()
        return hashcode == signature
    
    def build_reply(self, to_user: str, from_user: str, content: str) -> str:
        """构建微信回复 XML"""
        return f"""
        <xml>
            <ToUserName><![CDATA[{to_user}]]></ToUserName>
            <FromUserName><![CDATA[{from_user}]]></FromUserName>
            <CreateTime>{int(time.time())}</CreateTime>
            <MsgType><![CDATA[text]]></MsgType>
            <Content><![CDATA[{content}]]></Content>
        </xml>
        """

# FastAPI 路由
@router.post("/webhook/wechat/{tenant_id}")
async def wechat_webhook(tenant_id: str, request: Request):
    """微信消息回调"""
    adapter = get_adapter("wechat", tenant_id)
    
    # 处理消息
    msg = await adapter.handle_message(request)
    
    # 交由对应的 AppService 编排
    app_service = request.app.state.assistant_chat_app_service
    reply = await app_service.execute(msg)
    
    # 返回微信 XML 格式
    return Response(
        content=adapter.build_reply(
            msg["metadata"]["openid"],
            msg["metadata"]["app_id"],
            reply.text
        ),
        media_type="application/xml"
    )
```

---

### 3.3 行业技能包（Skill Packages）

#### 设计思路

基于 Dify 的 Tools 机制，封装行业特定能力：

```
Skill Package
├── SKILL.md            # 技能唯一规范与定义文件（包含元数据与工具 Schema）
├── references/         # 参考文档与参考知识 (Markdown)
│   └── rules.md
├── scripts/            # 工具执行脚本 (Python/Bash)
│   └── execute.py
└── assets/             # 媒体与资源文件 (可选)
│   └── logo.png
```

#### 技能注册表

```python
# skill_registry.py
from typing import Dict, List
from pathlib import Path
import yaml
import re

class SkillRegistry:
    """技能注册中心 (Claude Skill 规范)"""
    
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, dict] = {}
        self.load_all()
    
    def load_all(self):
        """加载所有符合 Claude Skill 规范的技能"""
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                self._load_skill(skill_dir)
                
    def _load_skill(self, skill_dir: Path):
        # 解析 SKILL.md 中的 Frontmatter 和 Tools 定义
        pass
    
    def get_skill(self, skill_id: str) -> dict:
        return self.skills.get(skill_id)
    
    def list_skills(self) -> List[dict]:
        return list(self.skills.values())
```

---

### 3.4 MCP 集成

#### 设计思路

通过 MCP 协议连接外部工具和服务：

```
AppService 工作流 ──→ MCP Client ──→ MCP Server ──→ 外部服务
                │               │
                │               ├── Search Server (搜索引擎)
                │               ├── Database Server (数据库查询)
                │               ├── CRM Server (客户关系管理)
                │               └── Custom Server (自定义服务)
                │
                └── 统一接口：list_tools / call_tool
```

#### MCP Client 实现

```python
# mcp/client.py
import httpx
from typing import Dict, List, Any

class MCPClient:
    """MCP 客户端"""
    
    def __init__(self):
        self.servers: Dict[str, httpx.AsyncClient] = {}
    
    async def connect(self, server_id: str, url: str, api_key: str = None):
        """连接 MCP Server"""
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        self.servers[server_id] = httpx.AsyncClient(
            base_url=url,
            headers=headers,
            timeout=30.0
        )
    
    async def list_tools(self, server_id: str) -> List[Dict]:
        """获取工具列表"""
        client = self.servers.get(server_id)
        if not client:
            raise ValueError(f"Server {server_id} not connected")
        
        response = await client.get("/tools")
        return response.json().get("tools", [])
    
    async def call_tool(self, server_id: str, tool_name: str, parameters: Dict) -> Any:
        """调用工具"""
        client = self.servers.get(server_id)
        if not client:
            raise ValueError(f"Server {server_id} not connected")
        
        response = await client.post(
            "/call",
            json={
                "tool": tool_name,
                "parameters": parameters
            }
        )
        return response.json()
```

---

## 4. 数据库设计

### 4.1 ER 图

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   Tenant    │       │  Conversation│       │   Message   │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │◄──────┤ tenant_id   │◄──────┤ conv_id     │
│ name        │       │ id (PK)     │       │ id (PK)     │
│ industry    │       │ tenant_id   │       │ role        │
│ plan        │       │ user_id     │       │ content     │
│ api_key     │       │ channel     │       │ tokens      │
│ config      │       │ status      │       │ skill_used  │
│ quota_used  │       │ created_at  │       │ created_at  │
│ quota_limit │       └─────────────┘       └─────────────┘
│ status      │
└─────────────┘
       │
       │         ┌─────────────┐
       └────────►│  ApiUsage   │
                 ├─────────────┤
                 │ id (PK)     │
                 │ tenant_id   │
                 │ model       │
                 │ tokens_in   │
                 │ tokens_out  │
                 │ cost        │
                 │ date        │
                 └─────────────┘
```

### 4.2 表结构

```sql
-- 租户表
CREATE TABLE tenants (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    industry VARCHAR(50),
    contact VARCHAR(50),
    plan VARCHAR(20) DEFAULT 'basic',
    config JSONB DEFAULT '{}',
    api_key VARCHAR(100) UNIQUE,
    status VARCHAR(20) DEFAULT 'active',
    quota_used INTEGER DEFAULT 0,
    quota_limit INTEGER DEFAULT 100000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 对话表
CREATE TABLE conversations (
    id VARCHAR(50) PRIMARY KEY,
    tenant_id VARCHAR(50) REFERENCES tenants(id),
    user_id VARCHAR(50),
    channel VARCHAR(20), -- wechat / feishu / dingtalk / web
    status VARCHAR(20) DEFAULT 'active',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 消息表
CREATE TABLE messages (
    id VARCHAR(50) PRIMARY KEY,
    conversation_id VARCHAR(50) REFERENCES conversations(id),
    role VARCHAR(20) NOT NULL, -- user / assistant / system
    content TEXT NOT NULL,
    content_type VARCHAR(20) DEFAULT 'text',
    tokens_used INTEGER DEFAULT 0,
    skill_used VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API 用量统计表
CREATE TABLE api_usage (
    id VARCHAR(50) PRIMARY KEY,
    tenant_id VARCHAR(50) REFERENCES tenants(id),
    model VARCHAR(50),
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    cost DECIMAL(10, 4) DEFAULT 0,
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 告警表
CREATE TABLE alerts (
    id VARCHAR(50) PRIMARY KEY,
    tenant_id VARCHAR(50) REFERENCES tenants(id),
    level VARCHAR(20) NOT NULL, -- emergency / warning / info
    message TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'open', -- open / resolved
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 渠道配置表
CREATE TABLE channel_configs (
    id VARCHAR(50) PRIMARY KEY,
    tenant_id VARCHAR(50) REFERENCES tenants(id),
    channel_type VARCHAR(20) NOT NULL, -- wechat / feishu / dingtalk
    config JSONB NOT NULL, -- 各渠道特定配置
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_conversations_tenant ON conversations(tenant_id);
CREATE INDEX idx_api_usage_tenant_date ON api_usage(tenant_id, date);
```

---

## 5. API 设计

### 5.1 接口规范

- **Base URL**: `https://api.your-domain.com/v1`
- **认证方式**: Bearer Token（租户 API Key）
- **响应格式**: 统一 JSON 包装

### 5.2 核心接口

#### 对话接口

```http
POST /chat
Authorization: Bearer {tenant_api_key}
Content-Type: application/json

{
  "session_id": "sess_xxx",
  "message": "你好",
  "channel": "wechat",
  "user_id": "user_xxx"
}
```

#### 租户管理接口（管理员）

```http
POST /admin/tenants
GET /admin/tenants
GET /admin/tenants/{id}/stats
PUT /admin/tenants/{id}
DELETE /admin/tenants/{id}
```

#### 监控接口

```http
GET /admin/metrics
GET /admin/alerts
GET /admin/logs
```

---

## 6. 部署架构

### 6.1 容器编排

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Dify 服务（官方镜像）
  # dify-api:
  #   image: langgenius/dify-api:latest
  #   # ... Dify 官方配置

  # dify-web:
  #   image: langgenius/dify-web:latest
  #   # ... Dify 官方配置

  # dify-worker:
  #   image: langgenius/dify-worker:latest
  #   # ... Dify 官方配置

  # 你的后端服务
  agent-portal:
    build: ./portal
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://agent:agent123@postgres:5432/agent_db
      - LITELLM_API_KEY=${LITELLM_API_KEY}

  # 渠道适配器
  channel-adapter:
    build: ./adapters
    ports:
      - "8001:8000"
    environment:
      - DATABASE_URL=postgresql://agent:agent123@postgres:5432/agent_db

  # 数据库
  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # 缓存
  redis:
    image: redis:7-alpine

  # 反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf

volumes:
  postgres_data:
```

### 6.2 部署流程

```bash
# 1. 克隆项目
git clone https://github.com/yourname/agent-framework.git
cd agent-framework

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 3. 启动服务
docker-compose up -d

# 4. 初始化数据库
docker-compose exec agent-portal python init_db.py

# 5. 检查状态
docker-compose ps
```

---

## 7. 安全设计

### 7.1 认证授权

- **租户认证**: API Key + Bearer Token
- **管理员认证**: JWT Token
- **微信认证**: 微信服务器签名验证

### 7.2 数据安全

- **传输加密**: HTTPS/TLS 1.3
- **数据隔离**: 租户级别数据库隔离
- **敏感信息**: API Key 加密存储
- **日志脱敏**: 手机号、身份证号等敏感信息脱敏

### 7.3 防护措施

- **限流**: 每分钟 100 次请求（按租户）
- **防重放**: 请求时间戳校验
- **IP 白名单**: 可选配置
- **CORS**: 严格限制域名

---

## 8. 监控告警

### 8.1 监控指标

| 指标 | 类型 | 告警阈值 |
|------|------|---------|
| 系统可用性 | 百分比 | < 99.5% |
| 平均响应时间 | 秒 | > 3s |
| 错误率 | 百分比 | > 5% |
| API 调用量 | 次/小时 | > 100K |
| 磁盘使用率 | 百分比 | > 80% |
| 内存使用率 | 百分比 | > 85% |

### 8.2 告警通道

- 飞书机器人
- 钉钉机器人
- 企业微信
- 邮件

---

## 9. 扩展性设计

### 9.1 水平扩展

- **无状态服务**: API 服务无状态，可水平扩展
- **负载均衡**: Nginx 反向代理 + 负载均衡
- **数据库**: 读写分离（未来）
- **缓存**: Redis Cluster（未来）

### 9.2 技能扩展

```python
# 新技能开发流程 (Claude Skill 规范)
1. 创建 skills/new_skill/ 目录
2. 编写 SKILL.md 定义技能说明和工具 Schema
3. 实现 scripts/ 工具执行脚本
4. 准备 references/ 参考知识
5. 准备 assets/ 媒体文件 (可选)
6. 热加载到系统
```

---

## 10. 开发计划

| 阶段 | 时间 | 目标 | 产出 |
|------|------|------|------|
| **Phase 1** | Week 1-2 | 部署 LiteLLM + 基础后端 | 可运行的基础平台 |
| **Phase 2** | Week 3-4 | 客户面板 + 微信适配器 | 可交付的 MVP |
| **Phase 3** | Week 5-6 | 行业技能包 + 监控告警 | 第一个行业方案 |
| **Phase 4** | Week 7-8 | 小程序/APP + 计费系统 | 完整产品 |
| **Phase 5** | Month 3+ | 多行业扩展 + 优化 | 规模化运营 |

---

## 11. 技术栈汇总

| 层级 | 技术选型 | 版本 |
|------|---------|------|
| **前端** | React | ^18.2 |
| | Taro | ^3.6 |
| | Ant Design | ^5.0 |
| | ECharts | ^5.4 |
| **后端** | Python | 3.11 |
| | FastAPI | ^0.109 |
| | SQLAlchemy | ^2.0 |
| | Celery | ^5.3 |
| **模型网关** | LiteLLM | latest |
| **数据库** | PostgreSQL | 15 |
| | Redis | 7 |
| **消息队列** | Redis | 7 |
| **文件存储** | MinIO | latest |
| **容器** | Docker | 24+ |
| | Docker Compose | 2+ |
| **监控** | Prometheus | latest |
| | Grafana | latest |
| **反向代理** | Nginx | latest |

---

*本文档为设计阶段文档，具体实现可能根据实际情况调整。*
