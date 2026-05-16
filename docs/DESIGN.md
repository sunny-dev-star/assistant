# Agent Framework - 技术设计文档

## 文档信息
- **项目名称**: Agent Framework（智能体框架）
- **版本**: v1.0
- **日期**: 2026-05-16
- **状态**: 设计中

---

## 1. 设计目标

### 1.1 核心定位
基于 **Dify 开源框架** 二次开发，面向中小企业提供**行业定制智能体**服务。

### 1.2 设计原则
1. **不重复造轮子**：底层引擎用 Dify，专注做行业差异化
2. **快速交付**：2-4 周完成一个行业方案
3. **低运维成本**：Docker 一键部署，自动监控告警
4. **可扩展**：技能插件化，支持 MCP 协议

---

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        客户端层                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Web网页  │  │ 微信小程序 │  │  uni-app │  │  嵌入组件 │       │
│  │          │  │          │  │  (iOS/安卓)│  │          │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
└───────┼─────────────┼─────────────┼─────────────┼───────────────┘
        │             │             │             │
        └─────────────┴──────┬──────┴─────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                      你的后端服务层                              │
│  ┌─────────────────────────┴──────────────────────────────┐    │
│  │              API Gateway (Nginx / Traefik)              │    │
│  │              认证 / 限流 / 路由 / SSL                    │    │
│  └─────────────────────────┬──────────────────────────────┘    │
│                            │                                     │
│  ┌─────────────────────────┴──────────────────────────────┐    │
│  │              客户管理面板 (Vue 3 + Element Plus)         │    │
│  │  • 租户管理  • 对话记录  • 数据统计  • 计费系统          │    │
│  └─────────────────────────┬──────────────────────────────┘    │
│                            │                                     │
│  ┌─────────────────────────┴──────────────────────────────┐    │
│  │              渠道适配器 (Channel Adapters)               │    │
│  │  • 微信适配器  • 飞书适配器  • 钉钉适配器  • WebSocket   │    │
│  └─────────────────────────┬──────────────────────────────┘    │
└────────────────────────────┼────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                      Dify 引擎层                                │
│  ┌─────────────────────────┴──────────────────────────────┐    │
│  │              Dify Self-Hosted (Docker)                  │    │
│  │  • 工作流编排  • 知识库  • LLM 路由  • 对话管理          │    │
│  └─────────────────────────┬──────────────────────────────┘    │
└────────────────────────────┼────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                      基础设施层                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │PostgreSQL│  │  Redis   │  │  MinIO   │  │  Nginx   │       │
│  │          │  │          │  │          │  │          │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 分层说明

| 层级 | 组件 | 职责 | 技术选型 |
|------|------|------|----------|
| **客户端层** | Web/小程序/APP | 用户交互界面 | Vue 3 / uni-app / 微信小程序 |
| **后端服务层** | API Gateway | 统一入口、认证、限流 | Nginx / Traefik |
| | 客户管理面板 | 租户管理、数据统计、计费 | Vue 3 + Element Plus |
| | 渠道适配器 | 微信/飞书/钉钉消息转换 | Python / Node.js |
| **引擎层** | Dify | LLM 编排、知识库、对话管理 | Dify Self-Hosted |
| **基础设施层** | PostgreSQL | 业务数据存储 | PostgreSQL 15 |
| | Redis | 缓存、会话、队列 | Redis 7 |
| | MinIO | 文件存储 | MinIO |
| | Nginx | 反向代理、SSL | Nginx |

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

- **前端**: Vue 3 + Element Plus + ECharts（图表）
- **后端 API**: FastAPI（Python）
- **数据库**: PostgreSQL（租户隔离）
- **部署**: Docker + Nginx

---

### 3.2 渠道适配器（Channel Adapters）

#### 设计思路

每个渠道一个适配器，统一消息格式：

```
微信消息 ──→ 微信适配器 ──→ 统一消息格式 ──→ Dify API
飞书消息 ──→ 飞书适配器 ──→ 统一消息格式 ──→ Dify API
钉钉消息 ──→ 钉钉适配器 ──→ 统一消息格式 ──→ Dify API
Web消息 ───→ Web适配器 ───→ 统一消息格式 ──→ Dify API
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
    
    # 转发到 Dify
    reply = await forward_to_dify(msg)
    
    # 返回微信 XML 格式
    return Response(
        content=adapter.build_reply(
            msg["metadata"]["openid"],
            msg["metadata"]["app_id"],
            reply
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
├── skill.json          # 技能元数据
├── prompts/            # 提示词模板
│   └── system.txt
├── tools/              # 工具函数
│   ├── __init__.py
│   ├── menu_query.py
│   └── reservation.py
├── knowledge/          # 知识库
│   └── faq.json
└── tests/              # 测试用例
    └── test_skill.py
```

#### 技能注册表

```python
# skill_registry.py
from typing import Dict, List
import json
from pathlib import Path

class SkillRegistry:
    """技能注册中心"""
    
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, dict] = {}
        self.load_all()
    
    def load_all(self):
        """加载所有技能"""
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "skill.json").exists():
                with open(skill_dir / "skill.json") as f:
                    self.skills[skill_dir.name] = json.load(f)
    
    def get_skill(self, skill_id: str) -> dict:
        return self.skills.get(skill_id)
    
    def list_skills(self) -> List[dict]:
        return list(self.skills.values())
    
    def get_tools(self, skill_id: str) -> List[dict]:
        skill = self.get_skill(skill_id)
        return skill.get("tools", []) if skill else []
```

---

### 3.4 MCP 集成

#### 设计思路

通过 MCP 协议连接外部工具和服务：

```
Dify 工作流 ──→ MCP Client ──→ MCP Server ──→ 外部服务
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
  dify-api:
    image: langgenius/dify-api:latest
    # ... Dify 官方配置

  dify-web:
    image: langgenius/dify-web:latest
    # ... Dify 官方配置

  dify-worker:
    image: langgenius/dify-worker:latest
    # ... Dify 官方配置

  # 你的后端服务
  agent-portal:
    build: ./portal
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://agent:agent123@postgres:5432/agent_db
      - DIFY_API_URL=http://dify-api:5001
      - DIFY_API_KEY=${DIFY_API_KEY}

  # 渠道适配器
  channel-adapter:
    build: ./adapters
    ports:
      - "8001:8000"
    environment:
      - DATABASE_URL=postgresql://agent:agent123@postgres:5432/agent_db
      - DIFY_API_URL=http://dify-api:5001

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
# 新技能开发流程
1. 创建 skills/new_skill/ 目录
2. 编写 skill.json 元数据
3. 实现 tools/ 工具函数
4. 编写 prompts/ 提示词
5. 准备 knowledge/ 知识库
6. 运行测试
7. 热加载到系统
```

---

## 10. 开发计划

| 阶段 | 时间 | 目标 | 产出 |
|------|------|------|------|
| **Phase 1** | Week 1-2 | 部署 Dify + 基础后端 | 可运行的基础平台 |
| **Phase 2** | Week 3-4 | 客户面板 + 微信适配器 | 可交付的 MVP |
| **Phase 3** | Week 5-6 | 行业技能包 + 监控告警 | 第一个行业方案 |
| **Phase 4** | Week 7-8 | 小程序/APP + 计费系统 | 完整产品 |
| **Phase 5** | Month 3+ | 多行业扩展 + 优化 | 规模化运营 |

---

## 11. 技术栈汇总

| 层级 | 技术选型 | 版本 |
|------|---------|------|
| **前端** | Vue 3 | ^3.4 |
| | Element Plus | ^2.5 |
| | ECharts | ^5.4 |
| **后端** | Python | 3.11 |
| | FastAPI | ^0.109 |
| | SQLAlchemy | ^2.0 |
| | Celery | ^5.3 |
| **引擎** | Dify | latest |
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
