# 微信公众号快速接入（Nidari Demo）

> 目标：在 **30 分钟内** 让一个微信公众号连上 Nidari，实现多租户隔离的 AI 对话回复。

## 前置条件

| 项目 | 说明 |
|------|------|
| 微信公众号 | 已认证的服务号或订阅号（需有「服务器配置」权限；测试可用测试号） |
| 公网 HTTPS | 微信要求 `https://` 回调；本地开发用 [ngrok](https://ngrok.com/) 或 Cloudflare Tunnel |
| LLM API Key | `.env` 中配置 `DEEPSEEK_API_KEY`（或其他 LiteLLM 支持的模型） |
| 数据库 | Docker Compose（PostgreSQL）或本地 SQLite（仅 Web API 测试，微信生产建议 PostgreSQL） |

## 架构

```
微信用户 → 微信服务器 → GET/POST https://your-domain/webhook/wechat/{tenant_id}
                              ↓
                        Nidari WechatAdapter（验签 + 解析 XML）
                              ↓
                        AssistantChatAppService（多租户对话）
                              ↓
                        回复 XML → 微信 → 用户
```

每个 `{tenant_id}` 对应一套独立的微信配置（Token / AppID / AppSecret）和技能白名单——**一套 Nidari 实例，服务多个公众号客户**。

---

## 步骤 1：启动 Nidari

### 方式 A — Docker Compose（推荐，含 PostgreSQL）

```bash
cp .env.example .env
# 编辑 .env：DEEPSEEK_API_KEY、POSTGRES_PASSWORD 等

docker compose up -d agent-engine postgres
curl http://localhost:8000/health
```

### 方式 B — 本地开发

```bash
pip install -r requirements.txt
cp .env.example .env
cd src && python -m nidari --config-path ../res/conf/config.yaml --reload
```

---

## 步骤 2：创建带微信配置的租户

微信配置存在租户 `config.wechat` 字段中：

```json
{
  "wechat": {
    "token": "你在微信公众平台填写的 Token",
    "app_id": "wxXXXXXXXX",
    "app_secret": "XXXXXXXX",
    "encoding_aes_key": ""
  },
  "enabled_skills": ["weather_query", "express_query"],
  "window_size": 10,
  "default_model": "deepseek/deepseek-chat"
}
```

### 方式 A — API 创建（开发模式 `AUTH_ENABLED=false`）

```bash
curl -X POST http://localhost:8000/v1/admin/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "name": "WeChat Demo Tenant",
    "plan": "professional",
    "config": {
      "wechat": {
        "token": "YOUR_WECHAT_TOKEN",
        "app_id": "wxYOUR_APP_ID",
        "app_secret": "YOUR_APP_SECRET"
      },
      "enabled_skills": ["weather_query"],
      "window_size": 10,
      "default_model": "deepseek/deepseek-chat"
    }
  }'
```

记下返回的 `tenant_id`（如 `tnt_abc123`）和 `api_key`。

### 方式 B — 使用脚本（读取环境变量）

```bash
export DATABASE_URL="postgresql+asyncpg://agent:changeme@localhost:5432/agent_db"
export WECHAT_TOKEN="your_token"
export WECHAT_APP_ID="wx..."
export WECHAT_APP_SECRET="your_secret"
export TENANT_ID="tnt_wechat_demo"
export TENANT_NAME="WeChat Demo"

python3 scripts/setup_wechat_tenant.py
```

### 方式 C — 给默认租户追加微信配置（仅快速体验）

```sql
UPDATE tenants
SET config = config || '{
  "wechat": {
    "token": "YOUR_WECHAT_TOKEN",
    "app_id": "wxYOUR_APP_ID",
    "app_secret": "YOUR_APP_SECRET"
  }
}'::jsonb
WHERE id = 'tnt_default';
```

此时 `tenant_id` 使用 `tnt_default`。

---

## 步骤 3：暴露公网 HTTPS

微信无法访问 `localhost`，需要公网地址。

### ngrok 示例

```bash
ngrok http 8000
# 记下 https://xxxx.ngrok-free.app
```

回调 URL 格式：

```
https://xxxx.ngrok-free.app/webhook/wechat/{tenant_id}
```

示例：`https://xxxx.ngrok-free.app/webhook/wechat/tnt_wechat_demo`

> 生产环境使用 Nginx + 域名 + SSL（`docker compose` 已包含 nginx + certbot 模板）。

---

## 步骤 4：微信公众平台配置

1. 登录 [微信公众平台](https://mp.weixin.qq.com/) → **设置与开发** → **基本配置** → **服务器配置**
2. 填写：
   - **URL**：`https://your-domain/webhook/wechat/{tenant_id}`
   - **Token**：与租户 `config.wechat.token` 一致
   - **EncodingAESKey**：可选（明文模式留空）；若启用需同步写入 `encoding_aes_key`
   - **消息加解密方式**：开发阶段选 **明文模式**
3. 点击 **提交** — 微信会发 GET 请求验签，成功则启用。

---

## 步骤 5：本地验签测试（提交配置前）

无需真实微信，可先本地验证端点：

```bash
export WECHAT_TOKEN="your_token"
export TENANT_ID="tnt_wechat_demo"
export BASE_URL="http://localhost:8000"

python3 scripts/test_wechat_webhook.py verify
python3 scripts/test_wechat_webhook.py message --text "北京今天天气怎么样"
```

预期：`verify` 返回 `echostr`；`message` 返回含 AI 回复的 XML。

---

## 步骤 6：真机验证

1. 关注公众号（或扫码关注测试号）
2. 发送文字：`你好`
3. 应收到 AI 回复；订阅事件会触发欢迎语

查看日志：

```bash
docker compose logs -f agent-engine
# 或本地 uvicorn 终端输出
```

---

## 多租户：第二个公众号

再创建一个租户，使用**不同的** `tenant_id` 和微信凭证：

```
租户 A → /webhook/wechat/tnt_client_a  → 公众号 A 的 Token/AppID
租户 B → /webhook/wechat/tnt_client_b  → 公众号 B 的 Token/AppID
```

同一套 Nidari 实例，数据与配置完全隔离。

---

## 常见问题

| 现象 | 排查 |
|------|------|
| 微信提示「Token 验证失败」 | Token 是否与数据库 `config.wechat.token` 一致；URL 是否含正确 `tenant_id` |
| 403 / 401 | 确认 `/webhook/` 路径已放行（无需 Bearer）；服务是否可达 |
| 回复「服务暂时不可用」 | 租户 `status` 是否为 `active`；`DEEPSEEK_API_KEY` 是否配置 |
| 超时无回复 | 微信要求 **5 秒内**响应；LLM 慢时可先换更快模型或缩短 `max_tokens` |
| 语音不识别 | 需配置 `app_secret` 用于拉取语音素材；或开通微信语音识别 |

---

## 演示录屏建议（用于开源宣传）

1. 终端启动服务 + `curl /health`
2. 运行 `setup_wechat_tenant.py` 创建租户
3. 运行 `test_wechat_webhook.py message` 展示 XML 回复
4. （可选）ngrok + 微信公众平台验签成功截图
5. 手机发消息收到 AI 回复

---

## 相关文档

- [API 规范](API_SPEC.md)
- [技能开发 SDK](SKILL_SDK.md)
- [贡献指南](../CONTRIBUTING.md)
