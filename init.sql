-- Agent Framework Database Schema
-- Auto-loaded by docker-entrypoint-initdb.d

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

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

-- ============================================
-- Conversations
-- ============================================
CREATE TABLE IF NOT EXISTS conversations (
    id          VARCHAR(50) PRIMARY KEY,
    tenant_id   VARCHAR(50) NOT NULL REFERENCES tenants(id),
    user_id     VARCHAR(50) NOT NULL,
    channel     VARCHAR(20) DEFAULT 'web',
    status      VARCHAR(20) DEFAULT 'active',
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW(),
    closed_at   TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversations_tenant ON conversations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);

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
    metadata        JSONB DEFAULT '{}',
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
    '{"window_size": 10, "default_model": "deepseek/deepseek-chat", "enabled_skills": ["weather_query", "express_query"]}'
) ON CONFLICT (id) DO NOTHING;
