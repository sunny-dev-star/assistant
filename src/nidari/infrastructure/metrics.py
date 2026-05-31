"""
Prometheus metrics for monitoring
"""
from prometheus_client import Counter, Histogram, Gauge, Info

# =============================================
# Chat Metrics
# =============================================
chat_requests_total = Counter(
    "agent_chat_requests_total",
    "Total chat requests processed",
    ["tenant_id", "channel", "skill"],
)

chat_request_errors_total = Counter(
    "agent_chat_request_errors_total",
    "Total chat request errors",
    ["tenant_id", "channel", "error_type"],
)

chat_latency_seconds = Histogram(
    "agent_chat_latency_seconds",
    "Chat response latency in seconds",
    ["tenant_id"],
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0],
)

# =============================================
# LLM Metrics
# =============================================
llm_tokens_total = Counter(
    "agent_llm_tokens_total",
    "Total LLM tokens consumed",
    ["tenant_id", "model", "direction"],  # direction: input / output
)

llm_cost_usd_total = Counter(
    "agent_llm_cost_usd_total",
    "Total LLM cost in USD",
    ["tenant_id", "model"],
)

llm_call_latency_seconds = Histogram(
    "agent_llm_call_latency_seconds",
    "LLM API call latency",
    ["tenant_id", "model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

llm_calls_total = Counter(
    "agent_llm_calls_total",
    "Total LLM API calls",
    ["tenant_id", "model"],
)

# =============================================
# Tool Metrics
# =============================================
tool_calls_total = Counter(
    "agent_tool_calls_total",
    "Total tool calls",
    ["tenant_id", "skill", "tool_name"],
)

tool_call_errors_total = Counter(
    "agent_tool_call_errors_total",
    "Total tool call errors",
    ["skill", "tool_name"],
)

tool_latency_seconds = Histogram(
    "agent_tool_latency_seconds",
    "Tool execution latency",
    ["skill", "tool_name"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
)

# =============================================
# Tenant Metrics
# =============================================
active_tenants_gauge = Gauge(
    "agent_active_tenants",
    "Number of active tenants",
)

tenant_quota_usage_ratio = Gauge(
    "agent_tenant_quota_usage_ratio",
    "Tenant quota usage ratio (0-1)",
    ["tenant_id"],
)

# =============================================
# System Info
# =============================================
app_info = Info(
    "agent_app",
    "Application info",
)
