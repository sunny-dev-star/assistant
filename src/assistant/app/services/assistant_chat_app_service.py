"""
通用对话应用服务
"""
import uuid
import logging
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
        """
        执行一轮对话
        """
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
            # 构建上下文
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
                # 简化：假设 arguments 已是 dict 或是可 parse 的 string
                import json
                try:
                    args = json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]
                except:
                    args = {}
                    
                logger.info(f"Executing tool: {tool_name} with {args}")
                try:
                    tool_result_content = await self.tool_gateway.call_tool(context, tool_name, args)
                except Exception as e:
                    logger.error(f"Tool {tool_name} failed: {e}")
                    tool_result_content = json.dumps({"error": str(e)}, ensure_ascii=False)
                
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
            
        # TODO: 在此处更新租户 Token / 计费等
        
        # 找到最后一条没有 tool_calls 的 assistant 消息
        reply_content = "抱歉，处理您的请求时出现问题。"
        for msg in reversed(history):
            if msg.role == "assistant" and not msg.tool_calls:
                reply_content = msg.content
                break
                
        return {
            "session_id": context.session_id,
            "reply": reply_content,
            "tokens_used": total_tokens,
            "cost_usd": total_cost
        }
