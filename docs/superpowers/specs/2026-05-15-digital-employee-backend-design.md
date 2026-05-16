# 智能数字员工后端 — 设计规格（MVP 与扩展）

**日期**: 2026-05-15  
**状态**: Draft → 待实现计划（`writing-plans`）  
**仓库上下文**: 绿field，以本规格为首次架构基线。

---

## 1. 背景与目标

企业需要可与业务系统集成的「数字员工」：**无头（Headless）、API 优先** 的后端，支持多轮对话、自动工具调用，并保留 MCP、多模型协议、RBAC、自进化与可观测扩展能力。

本规格 **锁定 MVP 范围**（见第 4 节），其余能力在架构上 **预留接口与扩展点**，不纳入 MVP 必交付。

---

## 2. 角色（全愿景 / MVP 相关度）

| 角色 | MVP |
|------|-----|
| 终端用户（经第三方聊天入口） | 通过集成方调用本服务；不直接暴露技能选择细节。 |
| 系统管理员 | MVP 无管理 UI；配置通过部署文件/环境变量完成。 |
| 集成方开发者 | 仅需按 **§3 集成方契约** 构造请求；**不需要**了解技能路由、工具、MCP 或模型编排细节。 |

---

## 3. 集成方契约（对外 API 边界）

### 3.1 设计原则

集成方将本服务视为 **黑盒对话引擎**：只传递 **用户自然语言** 与 **相关多媒体/文件**，并维护会话连续性。  
**不得要求**集成方传入 `skill_ids`、工具名、内部 `agent_profile` 等实现概念（调试覆盖见 §8.1）。

### 3.2 集成方必须提供

| 字段（逻辑名） | 说明 |
|----------------|------|
| **`session_id`** | **不透明**会话标识：由集成方生成并在同一聊天中复用；仅用于多轮关联，**不**暴露内部存储结构。 |
| **用户内容** | 至少包含 **一段主问题文本**（可为空串仅当法规/产品允许「纯附件提问」——默认建议非空），以及 **零个或多个附件**（图片、文件等）。具体 JSON / `multipart` 形态由实现计划在 OpenAPI 中固定。 |

### 3.3 多模态与附件（MVP）

服务端将集成方输入规范化为 **OpenAI 兼容** 的 `user` 消息（`content` 为 string 或 parts 数组），再进入编排与上下文模块。

| 类型 | MVP 行为 |
|------|-----------|
| **文本** | 直接进入 `user` 消息；作为 **SkillRouter 规则匹配** 的主输入（见 §8.2）。 |
| **图片** | `image_url`（公网可拉取）或 `image_url`/`image` + **base64**（由集成方提供）；要求部署侧选用 **支持视觉** 的模型；单图大小与数量设 **硬上限**（实现计划给出默认值）。 |
| **`text/*`、`application/json`** | 服务端读取正文，按大小上限 **内联** 为附加 `text` part（可带 `【附件: 文件名】` 前缀以便模型理解来源）。 |
| **其它二进制（如 PDF、Office）** | **MVP 不承诺**解析全文。默认策略：**仍接收**附件元数据（文件名、`mime_type`、可选体积），并向模型注入 **短说明**（英文系统模板由实现定义），提示模型可请用户粘贴关键信息或换可解析格式；**不**在 MVP 中静默伪造文件全文。后续可在 §13 引入解析管道与 OCR。 |

### 3.4 规则路由与多模态的衔接

- **SkillRouter** 的匹配输入取 **`user_primary_text`**：请求体中的主问题字符串。  
- 若主问题为空、仅附件：**MVP** 使用 **附件文件名（有序拼接，空格分隔）** 作为规则匹配输入，以便仍可走「关键词 → 技能」验收路径；若仍为空则走 `default_skill_ids`。

### 3.5 响应（集成方可见）

- **主路径**：模型对用户可见的 **自然语言回复**（及可选 `request_id` 便于排障）。  
- **不返回**：内部 `resolved_skill_ids`、工具调用明细（除非将来单独增加「调试模式」开关）；MVP 以 **最终答复** 为契约核心。

---

## 4. MVP 范围

### 4.1 纳入 MVP

- **标准 Chat**：统一 `POST /chat`（路径名可在实现阶段微调，规格以「单一主入口」为准）。
- **多轮会话**：集成方提供 **`session_id`**；服务端持久化消息序列。
- **集成方输入**：符合 **§3**（文本 + 图片 + 受限文件处理策略）。
- **上下文治理**：Token 计量近似 + **滑动窗口**；**单条 tool 结果硬上限 + 截断后缀**；**不做** 依赖额外 LLM 调用的自动摘要。
- **工具闭环**：模型返回 `tool_calls` 时，自动执行 **原生注册工具**，写回 `assistant` / `tool` 消息并继续循环，直至无工具调用或达到轮次上限。
- **MCP**：**抽象接口** + **一种参考实现**（transport 在实现计划中选定，如 stdio 子进程）。
- **技能（Skills）**：
  - **内部 `SkillPackage` 模型** + **`SkillProvider` 接口**；
  - **一个内置示例 Skill**（固定 id，用于验收）；
  - **技能选用**：**规则路由（配置驱动）**——根据 **§8.2** 输入文本匹配规则，解析出 `resolved_skill_ids`；
  - **不交付**：从磁盘加载完整 Claude Skill 目录（`SKILL.md` 解析器等）——仅在 §13 作为后续扩展说明。
- **模型协议**：**仅 OpenAI 兼容** `chat.completions`（含 tools / 多模态 `content`）；**Anthropic** 仅预留 **LLM 适配层接口**，无 MVP 实现。
- **技术栈**：**Python + FastAPI + SQLite**；异步 HTTP 客户端调用模型 API。
- **可调试性**：**`request_id`** + 结构化/常规应用日志；**不做** 业务指标表或完整 Trace 模型。

### 4.2 明确不纳入 MVP

- 鉴权（内网/开发假设；接口层 **预留** 鉴权挂载点）。
- RBAC、按用户动态工具过滤。
- 自进化：用户偏好记忆、失败纠正知识库。
- 可观测性落库与健康大盘数据表。
- 流式响应（SSE）：**默认 MVP 以非流式为主**以降低复杂度；若实现阶段提前完成，规格不禁止，但 **不作为 MVP 验收必要条件**。
- Claude 目录式 Skill 加载器、Skill 内任意代码执行沙箱。
- PDF/Office 等富格式 **全文提取**（见 §3.3 降级策略）。

---

## 5. 架构总览

**形态**：单体服务，模块边界清晰、进程内解耦。

```text
HTTP (/chat) → normalize integrator payload → Session/Message Store (SQLite)
            → SkillRouter (config rules → resolved_skill_ids)
            → SkillProvider.merge(system fragments)
            → ContextBuilder (token window + tool truncation)
            → Orchestrator loop → LLMClient (OpenAI-compatible)
                              → ToolRegistry / McpToolProvider
```

**原则**：编排引擎不持久化业务规则；规则与默认配置来自 **版本化配置文件**（或等价机制），由 **运维/我方** 维护；**集成方不感知**其内容。

---

## 6. 核心模块职责

| 模块 | 职责 |
|------|------|
| **HTTP/API** | 校验请求体（含附件大小与类型）；生成 `request_id`；错误映射；鉴权占位。 |
| **PayloadNormalizer** | 将集成方 JSON/multipart 转为内部 **OpenAI 风格 user 消息** + 提取 `user_primary_text` / 附件标签供 SkillRouter。 |
| **Session/Message 仓储** | `session_id` 维度追加与读取消息；建议含角色 `system|user|assistant|tool` 与 tool 元数据字段；`user` 多模态建议 **JSON 序列化**存储。 |
| **SkillRouter** | 输入：**§3.4** 定义的匹配字符串。输出：**有序、去重**的 `resolved_skill_ids`。完全 **配置驱动**。 |
| **SkillProvider** | 根据 id 返回 `SkillPackage`（片段、描述等）；内置示例 + 预留扩展。 |
| **ContextBuilder** | 组装：base system + skill fragments + 历史消息；应用 token 预算与 tool 结果截断策略。 |
| **Orchestrator** | `max_tool_rounds`、总请求超时；驱动「模型 → 工具 → 模型」循环。 |
| **LLMClient** | OpenAI 兼容适配；预留 `AnthropicLLMClient` 接口。 |
| **ToolRegistry** | 名字 → 可调用实现；对外暴露 OpenAI 格式 `tools` schema。 |
| **McpToolProvider** | 与 Registry 统一执行接口；MVP 一种 transport 的参考实现。 |

---

## 7. 数据流（单次请求）

1. 接收：**§3** 所定义的最小字段集（`session_id`、文本、附件列表等）；**不要求** `skill_ids`。
2. **PayloadNormalizer** 生成标准 `user` 消息与 SkillRouter 输入串。
3. 写入用户消息；读取历史。
4. **SkillRouter** 根据配置得到 `resolved_skill_ids`。
5. **SkillProvider** 合并 system 片段。
6. **ContextBuilder** 应用 token 窗口与 tool 截断。
7. **Orchestrator**：调用模型；处理 `tool_calls` 直至结束条件。
8. 返回 **面向用户的最终文本** + `request_id`；内部细节不进入默认响应体。

---

## 8. 技能与规则路由（MVP 定案）

### 8.1 决策来源

- **主路径**：系统 **内部** 通过 **规则路由** 决定技能集合，**不**要求集成方或终端用户传入 `skill_ids`。
- **调试覆盖（可选）**：仅开发/内网可通过配置开启「请求头或查询参数允许强制指定技能列表」，**生产默认关闭**。实现计划需写明开关与审计日志策略。

### 8.2 规则语义（MVP）

配置文件（如 YAML）定义 **有序规则列表**。每条规则至少包含：

- **匹配**：对 **§3.4** 定义的匹配字符串执行 **子串包含** 匹配（**MVP**）；**正则** 可作为实现计划中的可选增强（若实现正则，须在规格测试策略中增加用例）。
- **技能集**：匹配成功时贡献的一组 `skill_id`（有序）。

**合并策略（MVP）**：按配置顺序遍历规则，**将所有匹配规则的技能 id 依次合并，去重并保持首次出现顺序**；设 **`max_skills_per_request`** 上限（配置项，默认小整数如 3），超出则截断并打 WARN 日志。

若无任何规则匹配：使用 **`default_skill_ids`**（可为空或仅含内置示例，由部署决定）。

### 8.3 内置示例 Skill

- 固定 id（实现时命名，如 `builtin.example`），内容以简短 **英文** 说明为主（与代码注释语言策略一致），用于验证「规则命中 → 片段进入 system → 模型可见」全链路。

### 8.4 与 Claude Skill 的关系（扩展）

- 内部统一为 **`SkillPackage`**；未来通过 **`ClaudeSkillDirectoryLoader`** 将含 `SKILL.md` 的目录加载为多个 `SkillPackage`，并注册到 `SkillProvider`。
- **不承诺** MVP 内执行 Skill 附带任意代码；可执行能力需未来 **独立沙箱模块**。

---

## 9. 上下文与 Token

- **计量**：`tiktoken` 或等价，按模型名选择 encoding；未知模型采用保守默认。
- **滑动窗口**：在预算内从最新消息向旧消息保留。
- **Tool 消息**：单条内容 **token/字符硬上限**；超出 **截断 + 固定后缀**（如 `[truncated]`）。
- **多模态**：图片与内联文本共同参与 token 计量（按模型提供方规则近似）。
- **摘要**：不在 MVP；后续可单独成章引入「对最旧块单次摘要」等策略。

---

## 10. 工具与 MCP

- **原生工具**：Python 注册；schema 与 OpenAI `tools` 对齐生成。
- **MCP**：`McpToolProvider` 与原生工具共享执行路径；MVP **一种** reference transport。
- **权限**：MVP **无 RBAC**，会话可见 **全部** 已注册工具（含 MCP 暴露的工具名）。

---

## 11. 错误处理与边界

- **模型 HTTP 错误**：映射为 502/503；body 含 `request_id`、`error.code`；日志记录摘要。
- **工具失败**：错误文本作为 `tool` 角色内容返回模型；单工具超时可配置。
- **编排上限**：达到 `max_tool_rounds` 时返回明确状态（如 `finish_reason: tool_round_limit` 或等价自定义字段），由 API schema 固定。
- **附件过大或非法**：**413 / 422** + 明确 `error.code`（如 `attachment.too_large`、`attachment.invalid_encoding`）；**不**静默丢弃而不告知集成方。

---

## 12. 数据模型（逻辑）

最小表/集合建议（实现计划细化字段类型与索引）：

- **sessions**：`session_id`（主键或 UUID）、`created_at`、可选 `metadata`（JSON，MVP 可空）。
- **messages**：自增 id、`session_id`、角色、内容（**含多模态 JSON**）、`tool_calls` JSON（若有）、`tool_call_id`（tool 消息）、`created_at`。

**迁移**：初期 SQLite；通过仓储抽象保留迁 Postgres 可能。

---

## 13. 后续扩展（非 MVP）

- 鉴权：API Key / JWT / 网关透传身份。
- 多租户与 RBAC；按角色过滤工具列表。
- Anthropic Messages API 适配与原生 skill 字段映射（若需要）。
- 可观测：请求级指标落库、OpenTelemetry。
- 自进化：用户偏好、纠正知识库与检索。
- 流式输出、Redis 会话缓存、水平扩展。
- Skill 路由：由规则升级为 **轻量分类器或二次 LLM 路由**（可配置开关）。
- **富文档解析**：PDF/Office 文本化、OCR、病毒扫描与对象存储外链模式。

---

## 14. 测试策略（MVP）

- **单元**：SkillRouter（匹配、合并、上限）、ContextBuilder（窗口与截断）、**PayloadNormalizer**（文本 / 图片 / 文本文件 / 不支持的 PDF 元数据注入）、编排状态机（mock LLM）。
- **集成**：HTTP 层 + mock OpenAI 兼容服务端（覆盖无工具 / 单次工具 / 多轮工具 / **带图片 parts**）。
- **E2E**：依赖真实密钥的不进入默认 CI。

---

## 15. 风险与假设

- **规则路由**可能重叠或冲突：由 **有序合并 + max_skills** 约束；由 **运维** 维护规则，**非**集成方责任。
- **Token 计量**与上游模型实际计费可能不一致：仅服务本服务上下文裁剪，不声称计费精度。
- **无鉴权**：仅适用于可信网络；对外暴露前必须补鉴权与限流。
- **集成方仅传附件不传文**：规则命中依赖文件名，可能较弱；产品侧可引导集成方始终带一句用户话述。

---

## 16. 规格自检记录

- 无 `TBD` 占位；开放项已归入「实现计划」或 §13 扩展。
- 与已确认 MVP 决策一致，并补充 **§3 集成方契约**（黑盒、多模态、SkillRouter 输入衔接）。

---

## 17. 审批与下一步

- **设计评审**：技能主路径为 **§8 规则路由**；对外边界以 **§3** 为准。
- **下一步**：经需求方书面确认本文件后，使用 **`writing-plans`** 产出实现计划与任务拆分。
