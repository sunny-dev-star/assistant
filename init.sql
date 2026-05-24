-- Agent Framework Database Schema
-- Auto-loaded by docker-entrypoint-initdb.d
-- Requires: pgvector/pgvector:pg15 image

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================
-- Auto-update updated_at trigger function
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Tenants
-- ============================================
CREATE TABLE IF NOT EXISTS tenants (
    id          VARCHAR(50) PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    industry    VARCHAR(50),
    contact     VARCHAR(100),
    plan        VARCHAR(20) DEFAULT 'basic',
    status      VARCHAR(20) DEFAULT 'active',
    api_key     VARCHAR(200) UNIQUE NOT NULL,
    quota_used  INTEGER DEFAULT 0,
    quota_limit INTEGER DEFAULT 100000,
    config      JSONB DEFAULT '{}',
    window_size INTEGER DEFAULT 10,
    default_model VARCHAR(50) DEFAULT 'deepseek/deepseek-chat',
    enabled_skills JSONB DEFAULT '[]',
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tenants_api_key ON tenants(api_key);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);

CREATE TRIGGER trg_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================
-- Conversations
-- ============================================
CREATE TABLE IF NOT EXISTS conversations (
    id          VARCHAR(50) PRIMARY KEY,
    tenant_id   VARCHAR(50) NOT NULL REFERENCES tenants(id),
    user_id     VARCHAR(50) NOT NULL,
    channel     VARCHAR(20) DEFAULT 'web',
    status      VARCHAR(20) DEFAULT 'active',
    extra_data  JSONB DEFAULT '{}',
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW(),
    closed_at   TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversations_tenant ON conversations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);

CREATE TRIGGER trg_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================
-- Messages
-- ============================================
CREATE TABLE IF NOT EXISTS messages (
    id              VARCHAR(50) PRIMARY KEY,
    conversation_id VARCHAR(50) NOT NULL REFERENCES conversations(id),
    tenant_id       VARCHAR(50) NOT NULL REFERENCES tenants(id),
    role            VARCHAR(20) NOT NULL,
    name            VARCHAR(100),
    content         TEXT DEFAULT '',
    content_type    VARCHAR(20) DEFAULT 'text',
    tool_calls      JSONB,
    tool_call_id    VARCHAR(100),
    tokens_used     INTEGER DEFAULT 0,
    skill_used      VARCHAR(50),
    meta_data       JSONB DEFAULT '{}',
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_tenant ON messages(tenant_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);

-- ============================================
-- API Usage (for billing)
-- ============================================
CREATE TABLE IF NOT EXISTS api_usage (
    id                VARCHAR(50) PRIMARY KEY,
    tenant_id         VARCHAR(50) NOT NULL REFERENCES tenants(id),
    conversation_id   VARCHAR(50),
    model             VARCHAR(50) NOT NULL,
    prompt_tokens     INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens      INTEGER DEFAULT 0,
    cost_usd          BIGINT DEFAULT 0,  -- micro-dollars (multiply by 1e6)
    skill_name        VARCHAR(50),
    channel           VARCHAR(20) DEFAULT 'web',
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_usage_tenant ON api_usage(tenant_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_created ON api_usage(created_at);

-- ============================================
-- Knowledge Embeddings (vector search for RAG)
-- ============================================
CREATE TABLE IF NOT EXISTS knowledge_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL REFERENCES tenants(id),
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_tenant ON knowledge_embeddings(tenant_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding ON knowledge_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================
-- Seed: default tenant for development
-- ============================================
INSERT INTO tenants (id, name, api_key, plan, status, quota_limit, config)
VALUES (
    'tnt_default',
    'Default Tenant (Dev)',
    'ak_dev_test_key_12345',
    'professional',
    'active',
    1000000,
    '{"window_size": 10, "default_model": "deepseek/deepseek-chat", "enabled_skills": ["weather_query", "express_query", "elder_care"]}'
) ON CONFLICT (id) DO NOTHING;
-- Scheduled Tasks (persistent, multi-tenant)
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id VARCHAR(50) PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL REFERENCES tenants(id),
    user_id VARCHAR(50) NOT NULL,
    channel VARCHAR(20) NOT NULL DEFAULT 'wechat',
    task_type VARCHAR(50) NOT NULL,
    display_name TEXT,
    cron_expr VARCHAR(100),
    run_once_at TIMESTAMP,
    timezone VARCHAR(50) NOT NULL DEFAULT 'Asia/Shanghai',
    execution_type VARCHAR(20) NOT NULL DEFAULT 'message',
    message TEXT,
    skill_name VARCHAR(50),
    tool_name VARCHAR(50),
    tool_args JSONB DEFAULT '{}',
    steps JSONB DEFAULT '[]',
    mission_prompt TEXT,
    mission_skills JSONB DEFAULT '[]',
    context_as_input BOOLEAN DEFAULT FALSE,
    result_as_message BOOLEAN DEFAULT TRUE,
    skill_disabled_action VARCHAR(20) DEFAULT 'notify_admin',
    is_active BOOLEAN DEFAULT TRUE,
    last_run_at TIMESTAMP,
    last_result TEXT,
    run_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    next_run_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tasks_next_run ON scheduled_tasks(next_run_at, is_active);
CREATE INDEX IF NOT EXISTS idx_tasks_tenant ON scheduled_tasks(tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_active ON scheduled_tasks(is_active, cron_expr) WHERE is_active = TRUE;

CREATE TRIGGER trg_tasks_updated_at
    BEFORE UPDATE ON scheduled_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Task Execution Logs
CREATE TABLE IF NOT EXISTS task_execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id VARCHAR(50) NOT NULL REFERENCES scheduled_tasks(id),
    tenant_id VARCHAR(50) NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    result TEXT,
    error_detail TEXT,
    steps_log JSONB DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_exec_logs_task ON task_execution_logs(task_id, started_at DESC);
