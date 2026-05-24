"""
通用对话应用服务 (with Prometheus metrics)
"""
import uuid
import logging
import time
import json
from typing import Dict, Any, List

from ...domain.models.context import TenantContext
from ...domain.entities.message import Message
from ...domain.services.conversation_context_service import ConversationContextService
from ...domain.ports.llm_port import ILLMChatPort
from ...domain.ports.tool_port import IToolGateway
from ...domain.repositories.message_repository import IMessageRepository

logger = logging.getLogger(__name__)


class AssistantChatAppService:
    """处理通用对话流程的应用服务"""

    def __init__(
        self,
        llm_port: ILLMChatPort,
        tool_gateway: IToolGateway,
        message_repo: IMessageRepository,
        context_service: ConversationContextService
    ):
        self.llm_port = llm_port
        self.tool_gateway = tool_gateway
        self.message_repo = message_repo
        self.context_service = context_service

    async def execute(
        self,
        context: TenantContext,
        user_message_content: str,
        user_name: str = None
    ) -> Dict[str, Any]:
        """执行一轮对话"""
        start_time = time.time()
        skill_used = None

        try:
            # 1. 加载历史消息
            history = await self.message_repo.list_by_conversation(
                conversation_id=context.session_id,
                limit=50
            )

            # 2. 持久化并追加当前用户消息
            user_msg = self.context_service.append_user_message(
                context=context,
                history=history,
                content=user_message_content,
                user_name=user_name
            )
            await self.message_repo.create(user_msg)

            # 3. 准备工具列表
            tools = await self.tool_gateway.list_tools(context)

            system_prompt = "你是「小助手」，一个友好智能的客服。"

            max_rounds = 5
            total_tokens = 0
            total_cost = 0.0

            # 4. 思考循环 (Orchestrator Loop)
            for round_num in range(max_rounds):
                messages = self.context_service.build_context_messages(
                    context=context,
                    history=history,
                    system_prompt=system_prompt
                )

                logger.info(f"LLM Call [{round_num+1}/{max_rounds}] for session: {context.session_id}")

                response = await self.llm_port.chat(
                    context=context,
                    messages=messages,
                    tools=tools if tools else None,
                    tool_choice="auto"
                )

                total_tokens += response.total_tokens
                total_cost += response.cost_usd

                # --- Metrics: LLM call ---
                try:
                    from ...infrastructure.metrics import (
                        llm_tokens_total, llm_cost_usd_total, llm_calls_total
                    )
                    model = context.llm_config.model
                    llm_calls_total.labels(
                        tenant_id=context.tenant_id, model=model
                    ).inc()
                    llm_tokens_total.labels(
                        tenant_id=context.tenant_id, model=model, direction="input"
                    ).inc(response.prompt_tokens)
                    llm_tokens_total.labels(
                        tenant_id=context.tenant_id, model=model, direction="output"
                    ).inc(response.completion_tokens)
                    llm_cost_usd_total.labels(
                        tenant_id=context.tenant_id, model=model
                    ).inc(response.cost_usd)
                except Exception:
                    pass

                # 创建 assistant 消息
                assistant_msg = Message.create_assistant_message(
                    conversation_id=context.session_id,
                    tenant_id=context.tenant_id,
                    content=response.content,
                    tool_calls=response.tool_calls,
                    tokens_used=response.total_tokens
                )
                history.append(assistant_msg)
                await self.message_repo.create(assistant_msg)

                if not response.tool_calls:
                    break

                # 执行工具调用
                for tc in response.tool_calls:
                    tool_name = tc["function"]["name"]
                    try:
                        args = json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]
                    except Exception:
                        args = {}

                    logger.info(f"Executing tool: {tool_name} with {args}")
                    tool_start = time.time()
                    try:
                        tool_result_content = await self.tool_gateway.call_tool(context, tool_name, args)
                        skill_used = tool_name.split("_")[0] if "_" in tool_name else tool_name
                    except Exception as e:
                        logger.error(f"Tool {tool_name} failed: {e}")
                        tool_result_content = json.dumps({"error": str(e)}, ensure_ascii=False)
                        # --- Metrics: tool error ---
                        try:
                            from ...infrastructure.metrics import tool_call_errors_total
                            tool_call_errors_total.labels(
                                skill="unknown", tool_name=tool_name
                            ).inc()
                        except Exception:
                            pass
                    finally:
                        # --- Metrics: tool latency ---
                        try:
                            from ...infrastructure.metrics import tool_latency_seconds, tool_calls_total
                            tool_latency_seconds.labels(
                                skill=skill_used or "unknown", tool_name=tool_name
                            ).observe(time.time() - tool_start)
                            tool_calls_total.labels(
                                tenant_id=context.tenant_id, skill=skill_used or "unknown", tool_name=tool_name
                            ).inc()
                        except Exception:
                            pass

                    tool_msg = Message.create_tool_message(
                        conversation_id=context.session_id,
                        tenant_id=context.tenant_id,
                        tool_call_id=tc["id"],
                        content=tool_result_content,
                        name=tool_name
                    )
                    history.append(tool_msg)
                    await self.message_repo.create(tool_msg)

            else:
                logger.warning(f"Session {context.session_id} reached max rounds")

            # 找到最后一条没有 tool_calls 的 assistant 消息
            reply_content = "抱歉，处理您的请求时出现问题。"
            for msg in reversed(history):
                if msg.role == "assistant" and not msg.tool_calls:
                    reply_content = msg.content
                    break

            # --- Record API usage for billing ---
            try:
                from ...infrastructure.persistence.database import async_session_factory
                from ...infrastructure.persistence.models import ApiUsageModel
                import uuid
                async with async_session_factory() as session:
                    usage = ApiUsageModel(
                        id=f"usage_{uuid.uuid4().hex[:12]}",
                        tenant_id=context.tenant_id,
                        conversation_id=context.session_id,
                        model=context.llm_config.model,
                        prompt_tokens=0,  # Aggregate from LLM responses
                        completion_tokens=0,
                        total_tokens=total_tokens,
                        cost_usd=int(total_cost * 1_000_000),  # micro-dollars
                        skill_name=skill_used,
                        channel=str(context.channel),
                    )
                    session.add(usage)
                    await session.commit()
            except Exception as e:
                logger.debug(f"Usage recording skipped: {e}")

            return {
                "session_id": context.session_id,
                "reply": reply_content,
                "tokens_used": total_tokens,
                "cost_usd": total_cost,
            }

        except Exception as e:
            # --- Metrics: error ---
            try:
                from ...infrastructure.metrics import chat_request_errors_total
                chat_request_errors_total.labels(
                    tenant_id=context.tenant_id,
                    channel=str(context.channel),
                    error_type=type(e).__name__,
                ).inc()
            except Exception:
                pass
            raise

        finally:
            # --- Metrics: latency + request count ---
            try:
                from ...infrastructure.metrics import chat_requests_total, chat_latency_seconds
                chat_latency_seconds.labels(tenant_id=context.tenant_id).observe(
                    time.time() - start_time
                )
                chat_requests_total.labels(
                    tenant_id=context.tenant_id,
                    channel=str(context.channel),
                    skill=skill_used or "none",
                ).inc()
            except Exception:
                pass
