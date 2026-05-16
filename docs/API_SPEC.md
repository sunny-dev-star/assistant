# Agent Framework - API 接口规范

## 基础信息
- **Base URL**: `https://api.agent-framework.com/v1`
- **认证方式**: Bearer Token（租户级别）
- **Content-Type**: `application/json`
- **响应格式**: 统一 JSON 包装

## 统一响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "request_id": "req_abc123"
}
```

错误响应：
```json
{
  "code": 4001,
  "message": "tenant quota exceeded",
  "data": null,
  "request_id": "req_abc123"
}
```

## 接口列表

### 1. 对话接口

#### POST /chat
发起对话

**请求头：**
```
Authorization: Bearer {tenant_token}
Content-Type: application/json
```

**请求体：**
```json
{
  "session_id": "sess_xxx",
  "message": "你好，我想订座",
  "context": {
    "user_id": "user_123",
    "channel": "wechat"
  }
}
```

**响应：**
```json
{
  "code": 200,
  "data": {
    "session_id": "sess_xxx",
    "message_id": "msg_abc",
    "reply": "您好！请问几位？需要什么时间？",
    "skill_used": "catering_reservation",
    "tokens_used": 156
  }
}
```

#### POST /chat/stream
流式对话（SSE）

**请求体：** 同 `/chat`

**响应：**
```
data: {"type": "start", "message_id": "msg_abc"}

data: {"type": "chunk", "content": "您好"}

data: {"type": "chunk", "content": "！请问"}

data: {"type": "end", "tokens_used": 156}
```

### 2. 技能管理接口

#### GET /skills
获取技能列表

**响应：**
```json
{
  "code": 200,
  "data": {
    "skills": [
      {
        "id": "catering_service",
        "name": "餐饮服务",
        "version": "1.0.0",
        "status": "active",
        "description": "餐饮行业的客服和订座服务"
      }
    ]
  }
}
```

#### POST /skills/{skill_id}/reload
热重载技能

**响应：**
```json
{
  "code": 200,
  "data": {
    "skill_id": "catering_service",
    "status": "reloaded",
    "timestamp": "2026-05-16T10:00:00Z"
  }
}
```

### 3. 租户管理接口（运营者使用）

#### POST /admin/tenants
创建租户

**请求体：**
```json
{
  "name": "老王烧烤",
  "industry": "catering",
  "contact": "13800138000",
  "plan": "basic",
  "config": {
    "llm_model": "deepseek-chat",
    "skills": ["catering_service"]
  }
}
```

**响应：**
```json
{
  "code": 200,
  "data": {
    "tenant_id": "tnt_abc123",
    "api_key": "ak_xxxxxxxx",
    "status": "active",
    "created_at": "2026-05-16T10:00:00Z"
  }
}
```

#### GET /admin/tenants/{tenant_id}/stats
获取租户统计

**响应：**
```json
{
  "code": 200,
  "data": {
    "tenant_id": "tnt_abc123",
    "total_sessions": 128,
    "total_messages": 1024,
    "tokens_used_this_month": 50000,
    "quota_remaining": 450000,
    "active_skills": ["catering_service"]
  }
}
```

### 4. 监控接口

#### GET /admin/metrics
系统指标

**响应：**
```json
{
  "code": 200,
  "data": {
    "active_tenants": 15,
    "online_agents": 12,
    "total_messages_today": 3456,
    "avg_response_time": 1.23,
    "error_rate": 0.02
  }
}
```

#### GET /admin/alerts
告警列表

**响应：**
```json
{
  "code": 200,
  "data": {
    "alerts": [
      {
        "id": "alt_001",
        "level": "warning",
        "tenant_id": "tnt_abc",
        "message": "API 调用量接近上限（85%）",
        "created_at": "2026-05-16T09:00:00Z"
      }
    ]
  }
}
```

## 错误码表

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 4001 | 租户配额超限 |
| 4002 | 技能未找到 |
| 4003 | LLM API 调用失败 |
| 4010 | 认证失败 |
| 4030 | 权限不足 |
| 4040 | 资源不存在 |
| 5000 | 服务器内部错误 |
| 5001 | 数据库连接失败 |
| 5002 | LLM 服务不可用 |
