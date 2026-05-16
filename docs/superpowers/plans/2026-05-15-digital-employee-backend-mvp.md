# Digital Employee Backend (MVP) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a greenfield headless chat backend under `src/` using DDD layers (`domain`, `app`, `ui`, `infra`), exposing a JSON-first `POST /chat` aligned to `docs/superpowers/specs/2026-05-15-digital-employee-backend-design.md`, with SQLite persistence, config-driven skill routing, OpenAI-compatible LLM calls, tool loop orchestration, and local structured logging only.

**Architecture:** `ui` hosts FastAPI HTTP adapters and request/response schemas; `app` contains use-case orchestration (one primary use case for a chat turn); `domain` holds entities/value objects, pure routing and context-shaping policies behind stable ports (protocols); `infra` implements SQLite repositories, YAML-loaded routing config, HTTP LLM client, tool registry, and the MVP MCP provider reference behind the same execution port as native tools. Multimedia and multipart ingestion are explicitly out of scope for this plan’s HTTP surface; `domain` normalization may still structure messages as “OpenAI-style user content” using plain string content only.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, Pydantic v2, HTTPX (async), stdlib `sqlite3` (sync) or `aiosqlite` (choose one in Task 1 and keep consistent), PyYAML, `tiktoken` (or documented fallback), pytest.

**Authoritative inputs:** `docs/superpowers/specs/2026-05-15-digital-employee-backend-design.md` plus session constraints: greenfield repo; code under `src/`; JSON-first API; audit logging deferred (stdout/local logger only).

---

## 1. Spec-to-plan coverage map

| Spec section | This plan |
|-------------|-----------|
| §3 black-box integrator contract | JSON body: `session_id`, `text`; response: assistant-visible `reply`, `request_id`, optional `finish_reason` when tool round limit hit |
| §3.3 multimodal | Deferred at HTTP layer; internal message model keeps extension points for parts later |
| §4.1 MVP modules | Mapped to layers in §3 below |
| §4.2 non-goals (auth, SSE, etc.) | Not implemented |
| §5 pipeline | Implemented as use case + ordered collaborators |
| §6 module table | Mapped to packages in §3 |
| §7 data flow | Reflected in use case steps in §6 |
| §8 skill routing | YAML config + pure `SkillRouter` in `domain` |
| §9 context/token | `ContextBuilder` in `domain` with truncation policy |
| §10 tools/MCP | `ToolRegistry` + `McpToolProvider` reference in `infra` behind `domain` ports |
| §11 errors | Mapped to HTTP status + stable `error.code` in `ui` error model |
| §12 data model | SQLite schema in `infra` matching logical tables |
| §14 tests | Unit + integration layout in §7 |

---

## 2. DDD layer mapping (`src/`)

| Layer | Responsibility | Must not |
|------|----------------|----------|
| `src/domain` | Entities (`Session`, `Message`), enums (`Role`), value types for tool calls, `SkillPackage`, routing input/value result types, pure `SkillRouter` + `ContextBuilder`, repository and LLM/tool **ports** (typing.Protocol), domain-specific exceptions | Import FastAPI, HTTPX, SQLite drivers, or YAML |
| `src/app` | Use cases (`HandleChatTurn`), application DTOs if distinct from UI models, transaction boundaries (unit of work pattern optional; minimum: clear repository call sequence), mapping between UI payloads and domain inputs | Contain SQL strings or raw HTTP |
| `src/infra` | SQLite DDL + repositories, YAML config loader for routing + skills manifest, `OpenAiChatCompletionsClient`, `ToolRegistry`, `McpToolProvider` reference, logging helpers | Define FastAPI routes |
| `src/ui` | FastAPI `APIRouter`, Pydantic request/response models, exception handlers to stable JSON errors, app factory wiring dependencies | Encode business rules beyond validation and HTTP mapping |

Cross-cutting: `src/__init__.py` may re-export version only; keep package imports shallow.

---

## 3. Target file tree (create as needed)

```text
pyproject.toml
README.md (minimal run instructions only if you update it deliberately)
src/
  __init__.py
  domain/
    __init__.py
    errors.py
    models/
      __init__.py
      message.py
      session.py
      skill.py
    ports/
      __init__.py
      repositories.py
      llm.py
      tools.py
      skills.py
      clock.py
    services/
      __init__.py
      skill_router.py
      context_builder.py
  app/
    __init__.py
    use_cases/
      __init__.py
      handle_chat_turn.py
  infra/
    __init__.py
    config/
      __init__.py
      routing_config.py
    persistence/
      __init__.py
      sqlite_connection.py
      sqlite_schema.py
      sqlite_repositories.py
    llm/
      __init__.py
      openai_chat_client.py
    tools/
      __init__.py
      registry.py
      mcp_provider.py
    skills/
      __init__.py
      filesystem_provider.py
    logging/
      __init__.py
      configure.py
  ui/
    __init__.py
    main.py
    api/
      __init__.py
      chat.py
      errors.py
      dependencies.py
tests/
  conftest.py
  unit/
    domain/
      test_skill_router.py
      test_context_builder.py
    app/
      test_handle_chat_turn_mocked.py
  integration/
    test_chat_http_sqlite.py
```

Files may be split further if any module exceeds ~300 lines, but start with this layout.

---

## 4. Public JSON contract (MVP, JSON-only)

**Request (`POST /chat`) body fields**

| Field | Type | Required | Rules |
|------|------|----------|-------|
| `session_id` | string | yes | non-empty; opaque to server |
| `text` | string | yes | allow empty string only if you explicitly want spec’s “attachments-only” path later; for this plan’s JSON-only milestone, treat empty as valid but document that routing falls back per §8 |

**Response (200)**

| Field | Type | Notes |
|------|------|-------|
| `reply` | string | final assistant-visible natural language |
| `request_id` | string | generated per HTTP request |
| `finish_reason` | string or null | present when stopped by `tool_round_limit` or other orchestrator terminal reasons you define |

**Error response envelope** (non-2xx): include `request_id` (if allocated), `error.code` string, `message` human-readable. Align codes with §11 where applicable (`model.upstream_error`, `orchestrator.tool_round_limit`, `request.validation_error`).

---

## 5. Configuration and environment

| Name | Purpose |
|------|---------|
| `DATABASE_PATH` | SQLite file path |
| `OPENAI_BASE_URL` | Base URL for OpenAI-compatible API |
| `OPENAI_API_KEY` | Secret for model calls |
| `OPENAI_MODEL` | Model name passed to client |
| `SKILL_ROUTING_PATH` | YAML for ordered rules + `default_skill_ids` + `max_skills_per_request` |
| `SKILL_PACKAGES_PATH` | YAML or directory convention for built-in packages (minimum: builtin example id) |
| `MAX_TOOL_ROUNDS` | int |
| `REQUEST_TIMEOUT_S` | total budget for orchestrator |

**Debug override (§8.1):** optional header `X-Debug-Skill-Ids` (comma-separated) gated by `DEBUG_SKILL_OVERRIDE_ENABLED` default `false`. When enabled, bypass router output with parsed list (still cap with `max_skills_per_request`). Log at WARNING with request_id when used.

---

## 6. Core behavioral specifications (no code)

### 6.1 `HandleChatTurn` use case (`src/app/use_cases/handle_chat_turn.py`)

**Collaborators (constructor-injected):** `SessionRepository`, `MessageRepository`, `SkillRouter` (or config + factory), `SkillProvider`, `ContextBuilder`, `Orchestrator`, `IdGenerator` for message ids if needed, `Clock`.

**Steps (ordered):**

1. Allocate domain-side identifiers if repositories need them; persist incoming user message as `Role.USER` with string content.
2. Load prior messages for `session_id` ordered ascending by creation sequence.
3. Compute routing input string per spec §3.4: `user_primary_text = request.text` (JSON-only milestone).
4. Resolve `resolved_skill_ids` via `SkillRouter`.
5. Fetch `SkillPackage` fragments via `SkillProvider.merge(skill_ids)`.
6. Build model message list via `ContextBuilder.build(...)`.
7. Run `Orchestrator.run(...)` until completion or limits; persist assistant and tool messages as they are produced.
8. Return final assistant text + terminal reason.

### 6.2 `SkillRouter` (`src/domain/services/skill_router.py`)

**Inputs:** routing string, `RoutingConfig` (rules list, defaults, max skills).

**Rule match:** substring containment on routing string, case sensitivity policy: **case-sensitive** unless config adds a flag later (document in YAML comments).

**Merge:** concatenate matched rule skill ids in rule order, dedupe preserving first occurrence, then truncate to `max_skills_per_request` with WARN log when truncation occurs.

### 6.3 `ContextBuilder` (`src/domain/services/context_builder.py`)

**Inputs:** base system prompt (config constant), merged skill system fragments, historical messages, tool schemas optional.

**Policies:** approximate token counting; sliding window from newest backward; tool message truncation with fixed suffix token `[truncated]` (ASCII) per §9.

### 6.4 `Orchestrator` (location: `src/app/use_cases/handle_chat_turn.py` as private collaborator class **or** `src/domain/services/orchestrator.py` if kept pure; either way, **domain must not import httpx**)

**Responsibilities:** loop up to `MAX_TOOL_ROUNDS`; call `LLMClient.complete(messages, tools)`; if tool calls: execute via `ToolExecutor` port; append `assistant` with `tool_calls` and `tool` messages; on empty tool calls return assistant content.

**Timeouts:** enforce per-orchestrator total timeout; on timeout map to 503 with `error.code`.

### 6.5 `OpenAiChatCompletionsClient` (`src/infra/llm/openai_chat_client.py`)

**Implements:** `domain.ports.llm.LLMClient` with method `complete(...) -> LLMResult` where `LLMResult` contains either message content and/or normalized tool calls.

**HTTP errors:** raise `domain.errors.UpstreamModelError` carrying status for UI mapping.

### 6.6 Persistence (`src/infra/persistence`)

**Schema:** tables `sessions`, `messages` per spec §12; indices on `messages(session_id, created_at)`; store multimodal-ready JSON in `content` column even if MVP only stores string-shaped JSON.

**Repositories:** implement `domain.ports.repositories` protocols with methods at minimum: `ensure_session`, `append_message`, `list_messages_for_session`.

### 6.7 Tools (`src/infra/tools`)

**Native tool registration:** name → async callable + JSON schema dict.

**MVP tool:** implement a harmless tool (example: `get_server_time`) returning ISO timestamp string, registered always.

**MCP reference:** `McpToolProvider` implements `ToolExecutor` extension or merges into registry at startup; one transport only (stdio subprocess) behind feature flag `MCP_ENABLED` default `false` for initial milestone if subprocess complicates CI—**plan decision:** implement interface + **no-op** or fake remote in tests; enable stdio transport in integration test only if stable in CI. *Adjustment for consistency:* Task checklist below requires **either** working stdio MCP with a tiny mock server script **or** stub provider behind port until stdio lands; pick one in Task 1 note to avoid half-implemented MCP.

**Plan decision (locked):** Implement `McpToolProvider` with **stdio** transport and a **fixture MCP server** under `tests/fixtures/mcp_echo_server.py` (minimal JSON-RPC loop) so integration proves one tool end-to-end; CI runs only if runtime allows subprocess (document in README).

### 6.8 Skill packages (`src/infra/skills`)

Provide filesystem-backed `SkillProvider` returning `SkillPackage` for `builtin.example` plus any ids referenced by routing YAML.

---

## 7. Testing strategy

**Unit tests**

- `tests/unit/domain/test_skill_router.py`: ordering, dedupe, max skills truncation, default path, empty routing string behavior.
- `tests/unit/domain/test_context_builder.py`: windowing drops oldest first; tool truncation suffix; deterministic fixture tokenizer hook (inject fake token counter interface from `domain.ports` if needed).
- `tests/unit/app/test_handle_chat_turn_mocked.py`: fake repositories + fake LLM returning: (a) direct answer, (b) single tool call then final answer, (c) max rounds exhaustion.

**Integration tests**

- `tests/integration/test_chat_http_sqlite.py`: `TestClient` against FastAPI app with temp SQLite file; swap LLM for ASGI-level dependency override using a fake client returning scripted sequences.

**E2E with real keys:** excluded from default CI per spec §14.

**Commands**

- `pytest -q` for full suite.
- During development: targeted `pytest tests/unit/domain/test_skill_router.py -q`.

---

## 8. Logging

Use stdlib `logging` with JSON or key=value structured formatter optional; at minimum include `request_id`, `session_id`, `resolved_skill_ids` at INFO after routing, WARN on router truncation and debug override usage. No persistence tables for audit in this plan.

---

## 9. Task checklist (implementation-sized)

### Task 1: Repository bootstrap

**Files:** `pyproject.toml`, `src/__init__.py`, `tests/conftest.py`

- [ ] **Step 1:** Add `pyproject.toml` with runtime deps (FastAPI, Uvicorn, HTTPX, Pydantic, PyYAML) and dev deps (`pytest`, `ruff` optional).
- [ ] **Step 2:** Create `src` package skeleton with empty `__init__.py` files per tree.
- [ ] **Step 3:** Add `pytest` discovery config for `tests/`.
- [ ] **Step 4:** Run `pytest -q` (expects zero tests collected or all passing).

### Task 2: Domain models and errors

**Files:** `src/domain/models/message.py`, `session.py`, `skill.py`, `src/domain/errors.py`

- [ ] **Step 1:** Define `Role` enum, `Message` dataclass/model with fields aligned to persistence needs (`tool_calls`, `tool_call_id` optional).
- [ ] **Step 2:** Define `SkillPackage` and `SkillRoutingResult` types.
- [ ] **Step 3:** Define domain exceptions: `ValidationError`, `UpstreamModelError`, `OrchestratorLimitReached`.

### Task 3: Domain ports

**Files:** `src/domain/ports/repositories.py`, `llm.py`, `tools.py`, `skills.py`, `clock.py`

- [ ] **Step 1:** Protocols for repositories, `LLMClient`, `ToolExecutor`/`ToolRegistryPort`, `SkillProvider`, `Clock`, `IdGenerator` if used.

### Task 4: SkillRouter unit implementation + tests

**Files:** `src/domain/services/skill_router.py`, `src/infra/config/routing_config.py`, `tests/unit/domain/test_skill_router.py`

- [ ] **Step 1:** Implement pure router + YAML loader DTO mapping.
- [ ] **Step 2:** Write unit tests covering §8.2 behaviors.

### Task 5: ContextBuilder + tests

**Files:** `src/domain/services/context_builder.py`, `tests/unit/domain/test_context_builder.py`

- [ ] **Step 1:** Implement token window + tool truncation with injectable tokenizer port.

### Task 6: SQLite infra

**Files:** `src/infra/persistence/sqlite_connection.py`, `sqlite_schema.py`, `sqlite_repositories.py`

- [ ] **Step 1:** Apply schema on startup (idempotent `CREATE TABLE IF NOT EXISTS`).
- [ ] **Step 2:** Implement repositories satisfying ports.

### Task 7: LLM client infra

**Files:** `src/infra/llm/openai_chat_client.py`

- [ ] **Step 1:** Map domain messages to OpenAI chat payload; parse assistant message and `tool_calls`.
- [ ] **Step 2:** Map HTTP failures to `UpstreamModelError`.

### Task 8: Tools + MCP reference

**Files:** `src/infra/tools/registry.py`, `mcp_provider.py`, `tests/fixtures/mcp_echo_server.py`

- [ ] **Step 1:** Implement registry execution returning string content for model consumption.
- [ ] **Step 2:** Implement stdio MCP client sufficient for one tool `echo`.
- [ ] **Step 3:** Unit-test registry with fake tool.

### Task 9: SkillProvider filesystem

**Files:** `src/infra/skills/filesystem_provider.py`, `config/skills.example.yaml` (repo root config samples optional under `docs/` or `deploy/`—pick `deploy/skills.example.yaml` to avoid cluttering `src`)

- [ ] **Step 1:** Load builtin example package content from YAML.

### Task 10: Orchestrator + use case + mocked tests

**Files:** `src/app/use_cases/handle_chat_turn.py`, `tests/unit/app/test_handle_chat_turn_mocked.py`

- [ ] **Step 1:** Implement orchestration loop with injected LLM and tools.
- [ ] **Step 2:** Mocked tests for tool loop and limit.

### Task 11: UI FastAPI surface

**Files:** `src/ui/main.py`, `src/ui/api/chat.py`, `src/ui/api/errors.py`, `src/ui/api/dependencies.py`, `src/infra/logging/configure.py`

- [ ] **Step 1:** Build app factory wiring repositories from env.
- [ ] **Step 2:** Implement `POST /chat` calling use case.
- [ ] **Step 3:** Map domain errors to HTTP status codes per §11.
- [ ] **Step 4:** Configure logging on startup.

### Task 12: HTTP integration test

**Files:** `tests/integration/test_chat_http_sqlite.py`

- [ ] **Step 1:** Full stack with temp DB and fake LLM client override.
- [ ] **Step 2:** Assert `request_id` present and message persisted.

---

## 10. RIPER-5 实施清单（原子顺序）

实施清单：

1. 新增 `pyproject.toml` 并声明运行时与开发依赖，确定 SQLite 访问方式为 **同步 `sqlite3` + 线程池** 或 **全链路 async + `aiosqlite`**，全仓库统一一种风格。
2. 创建 `src/` 下 `domain` / `app` / `infra` / `ui` 包骨架与空 `__init__.py`。
3. 在 `src/domain/errors.py` 定义领域异常类型。
4. 在 `src/domain/models/` 定义 `Role`、`Message`、`Session`（若需要）与 `SkillPackage` 等模型。
5. 在 `src/domain/ports/` 定义仓储、LLM、工具执行、技能提供、时钟等 Protocol。
6. 实现 `src/domain/services/skill_router.py` 与 `src/infra/config/routing_config.py` 的 YAML 映射数据结构。
7. 编写并跑通 `tests/unit/domain/test_skill_router.py`。
8. 实现 `src/domain/services/context_builder.py` 与 `tests/unit/domain/test_context_builder.py`。
9. 实现 `src/infra/persistence/sqlite_schema.py` 与迁移/初始化逻辑、`sqlite_repositories.py`。
10. 实现 `src/infra/llm/openai_chat_client.py` 对接 OpenAI 兼容 `chat.completions`。
11. 实现 `src/infra/tools/registry.py` 与至少一个示例工具；实现 `mcp_provider.py` 与 `tests/fixtures/mcp_echo_server.py`。
12. 实现 `src/infra/skills/filesystem_provider.py` 与内置 `builtin.example` 内容来源（YAML）。
13. 实现编排循环与 `src/app/use_cases/handle_chat_turn.py`；完成 `tests/unit/app/test_handle_chat_turn_mocked.py`。
14. 实现 `src/ui/api/chat.py`、`errors.py`、`dependencies.py` 与 `src/ui/main.py` 应用工厂。
15. 实现 `src/infra/logging/configure.py` 并在 `main` 启动时配置本地日志字段。
16. 编写 `tests/integration/test_chat_http_sqlite.py` 覆盖 HTTP + SQLite + 假 LLM。
17. 更新根 `README.md`：运行方式、环境变量、示例 `curl`（不写审计落库承诺）。

---

## 11. Self-review notes

**Spec coverage:** §3–§12 mapped in §1; deferred multimodal HTTP explicitly stated in Architecture.

**Placeholder scan:** No `TBD` tokens introduced; MCP ambiguity resolved in §6.7 with stdio + fixture server decision.

**Type consistency:** Public names use `session_id`, `request_id`, `resolved_skill_ids` internally; HTTP JSON uses `text` / `reply`—document mapping in `ui` layer only.

---

## 12. Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-15-digital-employee-backend-mvp.md`.

**Execution options:**

1. **Subagent-Driven (recommended):** dispatch a fresh subagent per task, review between tasks.
2. **Inline Execution:** execute tasks in this session using `superpowers:executing-plans`, batching with checkpoints.

Per RIPER-5, code changes require an explicit **`ENTER EXECUTE MODE`** after you approve this plan (and choose 1 or 2).

Which approach?
