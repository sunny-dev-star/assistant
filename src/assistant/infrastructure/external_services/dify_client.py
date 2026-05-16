"""
Dify 客户端
封装 Dify API 调用
"""
import httpx
from typing import Dict, Any, Optional


class DifyClient:
    """Dify API 客户端"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:5001",
        api_key: str = ""
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=30.0
        )
    
    async def chat(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        user_id: str = "anonymous",
        inputs: Dict[str, Any] = None,
        response_mode: str = "blocking"
    ) -> Dict[str, Any]:
        """
        发送对话请求
        
        Args:
            query: 用户消息
            conversation_id: 会话 ID（为空则创建新会话）
            user_id: 用户 ID
            inputs: 输入参数
            response_mode: 响应模式（blocking / streaming）
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": inputs or {},
            "query": query,
            "response_mode": response_mode,
            "conversation_id": conversation_id,
            "user": user_id
        }
        
        response = await self.client.post(
            "/v1/chat-messages",
            headers=headers,
            json=payload
        )
        
        response.raise_for_status()
        return response.json()
    
    async def get_conversations(
        self,
        user_id: str = "",
        last_id: str = "",
        limit: int = 20
    ) -> Dict[str, Any]:
        """获取会话列表"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        params = {
            "user": user_id,
            "last_id": last_id,
            "limit": limit
        }
        
        response = await self.client.get(
            "/v1/conversations",
            headers=headers,
            params=params
        )
        
        response.raise_for_status()
        return response.json()
    
    async def get_messages(
        self,
        conversation_id: str,
        user_id: str = "",
        first_id: str = "",
        limit: int = 20
    ) -> Dict[str, Any]:
        """获取消息列表"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        params = {
            "user": user_id,
            "first_id": first_id,
            "limit": limit
        }
        
        response = await self.client.get(
            f"/v1/messages",
            headers=headers,
            params={**params, "conversation_id": conversation_id}
        )
        
        response.raise_for_status()
        return response.json()
    
    async def upload_file(self, file_path: str, user_id: str = "") -> Dict[str, Any]:
        """上传文件"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"user": user_id}
            
            response = await self.client.post(
                "/v1/files/upload",
                headers=headers,
                files=files,
                data=data
            )
        
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
