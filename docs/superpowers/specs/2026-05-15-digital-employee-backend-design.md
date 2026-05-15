# 智能数字员工后端 — 设计规格（MVP 与扩展）

**日期**: 2026-05-15  
**状态**: Draft → 待实现计划（`writing-plans`）  
**仓库上下文**: 绿field，以本规格为首次架构基线。

---

## 1. 背景与目标

企业需要可与业务系统集成的「数字员工」：**无头（Headless）、API 优先** 的后端，支持多轮对话、自动工具调用，并保留 MCP、多模型协议、RBAC、自进化与可观测扩展能力。

本规格 **锁定 MVP 范围**（见第 3 节），其余能力在架构上 **预留接口与扩展点**，不纳入 MVP 必交付。

---

## 2. 角色（全愿景 / MVP 相关度）

| 角色 | MVP |
|------|-----|
| 终端用户（经第三方聊天入口） | 通过集成方调用本服务；不直接暴露技能选择细节。 |
| 系统管理员 | MVP 无管理 UI；配置通过部署文件/环境变量完成。 |
| 集成方开发者 | 调用 `/chat`，负责传入 `session_id` 与用户消息；可传可选会话元数据（若规格定义）。 |

---

## 3. MVP 范围

### 3.1 纳入 MVP

- **标准 Chat**：统一 `POST /chat`（路径名可在实现阶段微调，规格以「单一主入口」为准）。
- **多轮会话**：客户端提供 **`session_id`**；服务端持久化消息序列。
- **上下文治理**：Token 计量近似 + **滑动窗口**；**单条 tool 结果硬上限 + 截断后缀**；**不做** 依赖额外 LLM 调用的自动摘要。
- **工具闭环**：模型返回 `tool_calls` 时，自动执行 **原生注册工具**，写回 `assistant` / `tool` 消息并继续循环，直至无工具调用或达到轮次上限。
- **MCP**：**抽象接口** + **一种参考实现**（transport 在实现计划中选定，如 stdio 子进程）。
- **技能（Skills）**：
  - **内部 `SkillPackage` 模型** + **`SkillProvider` 接口**；
  - **一个内置示例 Skill**（固定 id，用于验收）；
  - **技能选用**：**规则路由（配置驱动）**——根据**用户当前消息**匹配规则，解析出本次生效的 `resolved_skill_ids`（见第 7 节）；
  - **不交付**：从磁盘加载完整 Claude Skill 目录（`SKILL.md` 解析器等）——仅在第 12 节作为后续扩展说明。
- **模型协议**：**仅 OpenAI 兼容** `chat.completions`（含 tools）；**Anthropic** 仅预留 **LLM 适配层接口**，无 MVP 实现。
- **技术栈**：**Python + FastAPI + SQLite**；异步 HTTP 客户端调用模型 API。
- **可调试性**：**`request_id`** + 结构化/常规应用日志；**不做** 业务指标表或完整 Trace 模型。

### 3.2 明确不纳入 MVP

- 鉴权（内网/开发假设；接口层 **预留** 鉴权挂载点）。
- RBAC、按用户动态工具过滤。
- 自进化：用户偏好记忆、失败纠正知识库。
- 可观测性落库与健康大盘数据表。
- 流式响应（SSE）：**默认 MVP 以非流式为主**以降低复杂度；若实现阶段提前完成，规格不禁止，但 **不作为 MVP 验收必要条件**。
- Claude 目录式 Skill 加载器、Skill 内任意代码执行沙箱。

---

## 4. 架构总览

**形态**：单体服务，模块边界清晰、进程内解耦。

```text
HTTP (/chat) → Session/Message Store (SQLite)
            → SkillRouter (config rules → resolved_skill_ids)
            → SkillProvider.merge(system fragments)
            → ContextBuilder (token window + tool truncation)
            → Orchestrator loop → LLMClient (OpenAI-compatible)
                              → ToolRegistry / McpToolProvider
```

**原则**：编排引擎不持久化业务规则；规则与默认配置来自 **版本化配置文件**（或等价机制），便于集成方在不发版情况下调整（若部署流程允许）。

---

## 5. 核心模块职责

| 模块 | 职责 |
|------|------|
| **HTTP/API** | 校验请求体；生成 `request_id`；错误映射；鉴权占位。 |
| **Session/Message 仓储** | `session_id` 维度追加与读取消息；建议含角色 `system|user|assistant|tool` 与 tool 元数据字段。 |
| **SkillRouter** | 输入：最新用户消息文本（及可选轻量上下文，**MVP 仅用户消息**）。输出：**有序、去重**的 `resolved_skill_ids`。完全 **配置驱动**。 |
| **SkillProvider** | 根据 id 返回 `SkillPackage`（片段、描述等）；内置示例 + 预留扩展。 |
| **ContextBuilder** | 组装：base system + skill fragments + 历史消息；应用 token 预算与 tool 截断策略。 |
| **Orchestrator** | `max_tool_rounds`、总请求超时；驱动「模型 → 工具 → 模型」循环。 |
| **LLMClient** | OpenAI 兼容适配；预留 `AnthropicLLMClient` 接口。 |
| **ToolRegistry** | 名字 → 可调用实现；对外暴露 OpenAI 格式 `tools` schema。 |
| **McpToolProvider** | 与 Registry 统一执行接口；MVP 一种 transport 的参考实现。 |

---

## 6. 数据流（单次请求）

1. 接收：`session_id`、用户消息正文；可选字段在实现计划中细化（**不在 MVP 要求客户端传 `skill_ids`** 作为主路径）。
2. 写入用户消息；读取完整历史（或 ContextBuilder 按需读取）。
3. **SkillRouter** 根据用户消息与配置文件得到 `resolved_skill_ids`。
4. **SkillProvider** 将对应 system 片段按稳定顺序合并到 prompt 装配输入。
5. **ContextBuilder** 应用 token 窗口与 tool 结果截断规则。
6. **Orchestrator**：调用模型；若有 `tool_calls` 则执行并写回消息，重复直至结束条件。
7. 返回最终 assistant 文本（及可选的调试字段，默认关闭）；日志贯穿 `request_id`。

---

## 7. 技能与规则路由（MVP 定案）

### 7.1 决策来源

- **主路径**：系统 **内部** 通过 **规则路由** 决定技能集合，**不**要求终端用户或聊天 UI 传入 `skill_ids`。
- **调试覆盖（可选）**：仅开发/内网可通过配置开启「请求头或查询参数允许强制指定技能列表」，**生产默认关闭**。实现计划需写明开关与审计日志策略。

### 7.2 规则语义（MVP）

配置文件（如 YAML）定义 **有序规则列表**。每条规则至少包含：

- **匹配**：对用户消息执行 **子串包含** 匹配（**MVP**）；**正则** 可作为实现计划中的可选增强（若实现正则，须在规格测试策略中增加用例）。
- **技能集**：匹配成功时贡献的一组 `skill_id`（有序）。

**合并策略（MVP）**：按配置顺序遍历规则，**将所有匹配规则的技能 id 依次合并，去重并保持首次出现顺序**；设 **`max_skills_per_request`** 上限（配置项，默认小整数如 3），超出则截断并打 WARN 日志。

若无任何规则匹配：使用 **`default_skill_ids`**（可为空或仅含内置示例，由部署决定）。

### 7.3 内置示例 Skill

- 固定 id（实现时命名，如 `builtin.example`），内容以简短 **英文** 说明为主（与代码注释语言策略一致），用于验证「规则命中 → 片段进入 system → 模型可见」全链路。

### 7.4 与 Claude Skill 的关系（扩展）

- 内部统一为 **`SkillPackage`**；未来通过 **`ClaudeSkillDirectoryLoader`** 将含 `SKILL.md` 的目录加载为多个 `SkillPackage`，并注册到 `SkillProvider`。
- **不承诺** MVP 内执行 Skill 附带任意代码；可执行能力需未来 **独立沙箱模块**。

---

## 8. 上下文与 Token

- **计量**：`tiktoken` 或等价，按模型名选择 encoding；未知模型采用保守默认。
- **滑动窗口**：在预算内从最新消息向旧消息保留。
- **Tool 消息**：单条内容 **token/字符硬上限**；超出 **截断 + 固定后缀**（如 `[truncated]`）。
- **摘要**：不在 MVP；后续可单独成章引入「对最旧块单次摘要」等策略。

---

## 9. 工具与 MCP

- **原生工具**：Python 注册；schema 与 OpenAI `tools` 对齐生成。
- **MCP**：`McpToolProvider` 与原生工具共享执行路径；MVP **一种** reference transport。
- **权限**：MVP **无 RBAC**，会话可见 **全部** 已注册工具（含 MCP 暴露的工具名）。

---

## 10. 错误处理与边界

- **模型 HTTP 错误**：映射为 502/503；body 含 `request_id`、`error.code`；日志记录摘要。
- **工具失败**：错误文本作为 `tool` 角色内容返回模型；单工具超时可配置。
- **编排上限**：达到 `max_tool_rounds` 时返回明确状态（如 `finish_reason: tool_round_limit` 或等价自定义字段），由 API schema 固定。

---

## 11. 数据模型（逻辑）

最小表/集合建议（实现计划细化字段类型与索引）：

- **sessions**：`session_id`（主键或 UUID）、`created_at`、可选 `metadata`（JSON，MVP 可空）。
- **messages**：自增 id、`session_id`、角色、内容、`tool_calls` JSON（若有）、`tool_call_id`（tool 消息）、`created_at`。

**迁移**：初期 SQLite；通过仓储抽象保留迁 Postgres 可能。

---

## 12. 后续扩展（非 MVP）

- 鉴权：API Key / JWT / 网关透传身份。
- 多租户与 RBAC；按角色过滤工具列表。
- Anthropic Messages API 适配与原生 skill 字段映射（若需要）。
- 可观测：请求级指标落库、OpenTelemetry。
- 自进化：用户偏好、纠正知识库与检索。
- 流式输出、Redis 会话缓存、水平扩展。
- Skill 路由：由规则升级为 **轻量分类器或二次 LLM 路由**（可配置开关）。

---

## 13. 测试策略（MVP）

- **单元**：SkillRouter（匹配、合并、上限）、ContextBuilder（窗口与截断）、编排状态机（mock LLM）。
- **集成**：HTTP 层 + mock OpenAI 兼容服务端（覆盖无工具 / 单次工具 / 多轮工具）。
- **E2E**：依赖真实密钥的不进入默认 CI。

---

## 14. 风险与假设

- **规则路由**可能重叠或冲突：由 **有序合并 + max_skills** 约束；需集成方维护规则可读性。
- **Token 计量**与上游模型实际计费可能不一致：仅服务本服务上下文裁剪，不声称计费精度。
- **无鉴权**：仅适用于可信网络；对外暴露前必须补鉴权与限流。

---

## 15. 规格自检记录

- 无 `TBD` 占位；开放项已归入「实现计划」或第 12 节扩展。
- 与用户确认的 MVP 决策一致：A+C 能力、无鉴权、无自进化、OpenAI-only、可观测延后、Python 栈、方案一（自研编排 + SDK）、技能为 **接口 + 示例 + 规则路由**。

---

## 16. 审批与下一步

- **设计评审**：已由需求方确认总体章节；技能主路径为 **§7 规则路由**。
- **下一步**：经需求方书面确认本文件后，使用 **`writing-plans`** 产出实现计划与任务拆分。
