"""
对话用例 - DeepSeek LLM + Tool Calling
支持本地技能工具 + MCP 协议工具
"""
from typing import Optional, List, Dict
import uuid
import json
import logging

from ...infrastructure.external_services.deepseek_client import DeepSeekClient
from ...infrastructure.skill_loader import SkillLoader

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是「小助手」，一个友好智能的万能客服。

## 你的能力
你可以回答各种问题，并且拥有以下工具可以调用：

1. **天气查询** - 查询任意城市的当前天气和天气预报
2. **快递查询** - 根据快递单号查询物流状态
3. **商品咨询** - 回答商品相关问题（价格、规格、推荐等）

## 商品数据
- iPhone 16 Pro Max 256GB - ¥9999
- MacBook Air M4 13英寸 - ¥8999
- AirPods Pro 3 - ¥1899
- 戴森 V15 无线吸尘器 - ¥4990
- Nike Air Zoom Pegasus 41 - ¥899
- 三顿半精品速溶咖啡 24颗 - ¥189

## 行为规范
1. 用户问到天气 → 调用天气查询工具
2. 用户问到快递/物流 → 调用快递查询工具
3. 用户问到商品 → 直接回答
4. 一个问题可能需要调用多个工具（比如"帮我查下北京天气和我的快递"）
5. 调用工具后，用自然语言总结工具返回的结果
6. 语气友好，适当使用 emoji
"""


class ChatUseCase:
    """对话用例 - 支持 Tool Calling（本地技能 + MCP）"""

    def __init__(
        self,
        deepseek_client: DeepSeekClient,
        skill_loader: SkillLoader,
        mcp_client=None,
    ):
        self.deepseek_client = deepseek_client
        self.skill_loader = skill_loader
        self.mcp_client = mcp_client
        self._histories: Dict[str, List[Dict[str, str]]] = {}

    def _get_all_tools(self) -> list:
        """合并本地技能工具 + MCP 工具"""
        tools = self.skill_loader.get_all_tools()
        if self.mcp_client:
            tools.extend(self.mcp_client.get_tools())
        return tools

    async def _execute_tool(self, tool_name: str, args: dict) -> str:
        """执行工具：优先本地技能，回退 MCP"""
        # 1. 尝试本地技能
        local_tools = {t["function"]["name"] for t in self.skill_loader.get_all_tools()}
        if tool_name in local_tools:
            return await self.skill_loader.execute_tool(tool_name, args)

        # 2. 尝试 MCP
        if self.mcp_client:
            mcp_tools = {t["function"]["name"] for t in self.mcp_client.get_tools()}
            if tool_name in mcp_tools:
                return await self.mcp_client.call_tool(tool_name, args)

        return json.dumps({"error": f"Unknown tool: {tool_name}"}, ensure_ascii=False)

    async def execute(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        channel: str = "web",
        metadata: Optional[Dict] = None
    ) -> dict:
        if not session_id:
            session_id = f"sess_{uuid.uuid4().hex[:12]}"

        history = self._histories.get(session_id, [])
        recent_history = history[-20:]

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(recent_history)
        messages.append({"role": "user", "content": message})

        tools = self._get_all_tools()
        total_tokens = 0
        max_rounds = 5

        for round_num in range(max_rounds):
            try:
                result = await self.deepseek_client.chat(
                    messages=messages,
                    tools=tools if tools else None,
                    tool_choice="auto",
                )
            except Exception as e:
                logger.error(f"DeepSeek API call failed: {e}")
                reply = "抱歉，我暂时无法回复，请稍后再试 😥"
                break

            total_tokens += result.get("usage", {}).get("total_tokens", 0)
            choice = result["choices"][0]
            assistant_msg = choice["message"]

            tool_calls = assistant_msg.get("tool_calls")

            if not tool_calls:
                reply = assistant_msg.get("content", "")
                break

            logger.info(f"Round {round_num + 1}: {len(tool_calls)} tool calls")
            messages.append(assistant_msg)

            for tc in tool_calls:
                tool_name = tc["function"]["name"]
                try:
                    tool_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    tool_args = {}

                logger.info(f"  Calling tool: {tool_name}({tool_args})")
                tool_result = await self._execute_tool(tool_name, tool_args)
                logger.info(f"  Tool result: {tool_result[:200]}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": tool_result,
                })
        else:
            reply = "处理超时，请简化你的问题再试一次 😅"

        if session_id not in self._histories:
            self._histories[session_id] = []
        self._histories[session_id].append({"role": "user", "content": message})
        self._histories[session_id].append({"role": "assistant", "content": reply})

        return {
            "session_id": session_id,
            "message_id": f"msg_{uuid.uuid4().hex[:8]}",
            "reply": reply,
            "tokens_used": total_tokens,
        }

    async def get_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        history = self._histories.get(session_id, [])
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in history[-limit:]
        ]
