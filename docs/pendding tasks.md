### ❌ Pending Tasks — Full PRD Checklist

The following is every requirement item from your PRD mapped to its current status.

#### 3.1 Core Engine (核心引擎层)

| ID     | Requirement                                           | Status      | Notes                                                        |
| ------ | ----------------------------------------------------- | ----------- | ------------------------------------------------------------ |
| US-001 | Multi-turn context, 10-round default, max 50          | 🟡 Partial   | Basic chat works; configurable window size not confirmed     |
| US-001 | Auto-summarize long conversations                     | ❌ Not done  | No summarization logic found                                 |
| US-001 | Session isolation between tenants                     | ❌ Not done  | Test scripts use `user_id` only, no `tenant_id`              |
| US-002 | Per-tenant config space (LLM, skills, knowledge base) | ❌ Not done  | DB schema designed, not implemented                          |
| US-002 | Physical data isolation (schema prefix)               | ❌ Not done  |                                                              |
| US-002 | Tenant resource quota management                      | ❌ Not done  |                                                              |
| US-002 | Tenant enable/disable/suspend controls                | ❌ Not done  |                                                              |
| US-003 | Multi-LLM support (DeepSeek, Qwen, Zhipu, OpenAI)     | 🟡 Partial   | LiteLLM is in docker-compose; routing logic unconfirmed      |
| US-003 | Hot model switching without restart                   | ❌ Not done  |                                                              |
| US-003 | Fallback mechanism (primary → backup model)           | ❌ Not done  |                                                              |
| US-003 | Per-tenant default model config                       | ❌ Not done  |                                                              |
| US-004 | Standardized Skill directory structure                | ✅ Spec done | SKILL_SDK.md is complete                                     |
| US-004 | Dynamic skill load/unload without restart             | ❌ Not done  | `SkillRegistry._load_skill()` is a stub (`pass`) in DESIGN.md |
| US-004 | Inter-skill invocation                                | ❌ Not done  |                                                              |
| US-004 | Per-skill config and permission control               | ❌ Not done  |                                                              |
| US-004 | Skill SDK + example templates                         | 🟡 Partial   | SDK spec written; no example skill package committed         |
| US-005 | MCP Server auto-discovery and registration            | ❌ Not done  | MCPClient class is designed but not implemented              |
| US-005 | MCP Tool call and result passback                     | ❌ Not done  |                                                              |
| US-005 | MCP connection status monitoring                      | ❌ Not done  |                                                              |
| US-005 | Custom MCP Server onboarding                          | ❌ Not done  |                                                              |
| US-006 | Group session support with `user_id` + `name` binding | ❌ Not done  |                                                              |
| US-006 | LLM context correctly attributes different speakers   | ❌ Not done  |                                                              |
| US-006 | Group chat history viewable in admin panel            | ❌ Not done  |                                                              |

#### 3.2 Industry Skills (行业技能层)

| ID     | Requirement                                             | Status     |
| ------ | ------------------------------------------------------- | ---------- |
| US-101 | Catering AI: Meituan/Dianping/WeChat integration        | ❌ Not done |
| US-101 | Intent recognition (order/inquiry/complaint/review)     | ❌ Not done |
| US-101 | Menu-based dish recommendation                          | ❌ Not done |
| US-101 | Reservation booking                                     | ❌ Not done |
| US-101 | Negative review alert push to owner                     | ❌ Not done |
| US-102 | Education AI: course Q&A (price/schedule/teachers)      | ❌ Not done |
| US-102 | Lead capture + intent grading (high/mid/low)            | ❌ Not done |
| US-102 | Trial class booking                                     | ❌ Not done |
| US-102 | 3-day no-reply follow-up reminder                       | ❌ Not done |
| US-103 | E-commerce AI: Taobao/Pinduoduo/Douyin shop integration | 🟡 Partial  |
| US-103 | Order status + logistics auto-query                     | ❌ Not done |
| US-103 | Returns/exchange handling                               | ❌ Not done |
| US-103 | Multi-language reply (cross-border)                     | ❌ Not done |
| US-103 | Escalate complex issues to human agent                  | ❌ Not done |

#### 3.3 Monitoring Layer (后台监控层)

| ID     | Requirement                                                  | Status     | Notes                                                        |
| ------ | ------------------------------------------------------------ | ---------- | ------------------------------------------------------------ |
| US-201 | Dashboard: active agents, today's chats, API usage           | ❌ Not done | Prometheus + Grafana containers exist; dashboards not provisioned |
| US-201 | Per-tenant real-time status (online/offline/error)           | ❌ Not done |                                                              |
| US-201 | Conversation quality monitoring (response time, satisfaction) | ❌ Not done |                                                              |
| US-201 | Anomaly alerts (downtime, quota exceeded, error spike)       | ❌ Not done |                                                              |
| US-202 | Conversation log viewer with tenant/time/keyword filter      | ❌ Not done |                                                              |
| US-202 | Content desensitization (mask phone numbers etc.)            | ❌ Not done |                                                              |
| US-202 | Tag "good" and "problem" conversations                       | ❌ Not done |                                                              |
| US-202 | Export conversation records to Excel/CSV                     | ❌ Not done |                                                              |
| US-203 | Per-tenant token consumption statistics                      | ❌ Not done | DB schema for `api_usage` table is designed                  |
| US-203 | Per-model cost breakdown                                     | ❌ Not done |                                                              |
| US-203 | Per-skill call frequency stats                               | ❌ Not done |                                                              |
| US-203 | Auto-generate monthly usage report                           | ❌ Not done |                                                              |
| US-204 | Alert notifications: Feishu/DingTalk/WeCom/email             | ❌ Not done |                                                              |
| US-204 | Alert severity levels (urgent/important/general)             | ❌ Not done |                                                              |
| US-204 | Configurable alert rules                                     | ❌ Not done |                                                              |
| US-204 | Alert silence period                                         | ❌ Not done |                                                              |

#### 3.4 Deployment & Ops (部署与运维层)

| ID     | Requirement                               | Status     | Notes                                             |
| ------ | ----------------------------------------- | ---------- | ------------------------------------------------- |
| US-301 | Docker Compose one-command deployment     | ✅ Done     | docker-compose.yml complete                       |
| US-301 | Auto DB init + default config             | 🟡 Partial  | `init.sql` referenced but not checked             |
| US-301 | Environment variable configuration        | ✅ Done     | `.env` pattern in place                           |
| US-301 | HTTPS auto-config (Let's Encrypt)         | ❌ Not done | Nginx SSL mount exists; cert automation not wired |
| US-302 | dev/staging/prod environment separation   | ❌ Not done |                                                   |
| US-302 | Blue-green / rolling deployment           | ❌ Not done |                                                   |
| US-303 | Daily DB auto-backup                      | ❌ Not done |                                                   |
| US-303 | Backup upload to Aliyun OSS / Tencent COS | ❌ Not done |                                                   |
| US-303 | 30-day retention + auto-purge             | ❌ Not done |                                                   |
| US-303 | One-click restore                         | ❌ Not done |                                                   |
| US-304 | Centralized log collection                | ❌ Not done | `logs/` volume mounted; aggregation not set up    |
| US-304 | Filter by service/tenant/time             | ❌ Not done |                                                   |
| US-304 | Error log highlighting                    | ❌ Not done |                                                   |

#### 3.5 Client Integration Layer (客户端接入层)

| ID     | Requirement                                                  | Status                                                       |
| ------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| US-401 | Embeddable web chat widget (iframe / JS SDK)                 | ❌ Not done                                                   |
| US-401 | Custom style (colors, avatar, welcome text)                  | ❌ Not done                                                   |
| US-401 | File upload (image, PDF)                                     | ❌ Not done                                                   |
| US-401 | Mobile-responsive layout                                     | ❌ Not done                                                   |
| US-402 | WeChat Official Account integration (subscription/service)   | ❌ Not done — WechatAdapter class is designed in DESIGN.md, not committed |
| US-402 | WeCom (企业微信) customer service                            | ❌ Not done                                                   |
| US-402 | WeChat Mini Program                                          | ❌ Not done                                                   |
| US-402 | WeChat message format handling (rich text, voice, mini-program card) | ❌ Not done                                                   |
| US-403 | Feishu bot (group + 1:1)                                     | ❌ Not done                                                   |
| US-403 | DingTalk bot                                                 | ❌ Not done                                                   |
| US-403 | @robot trigger                                               | ❌ Not done                                                   |
| US-403 | Feishu/DingTalk approval and calendar integration            | ❌ Not done                                                   |

