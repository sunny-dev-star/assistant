"""
ID 生成器
"""
import uuid
import secrets
import string


class IDGenerator:
    """ID 生成器"""
    
    @staticmethod
    def tenant_id() -> str:
        """生成租户 ID"""
        return f"tnt_{uuid.uuid4().hex[:12]}"
    
    @staticmethod
    def conversation_id() -> str:
        """生成会话 ID"""
        return f"conv_{uuid.uuid4().hex[:12]}"
    
    @staticmethod
    def message_id() -> str:
        """生成消息 ID"""
        return f"msg_{uuid.uuid4().hex[:12]}"
    
    @staticmethod
    def session_id() -> str:
        """生成会话 ID"""
        return f"sess_{uuid.uuid4().hex[:12]}"
    
    @staticmethod
    def api_key() -> str:
        """生成 API Key"""
        return f"ak_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def skill_id() -> str:
        """生成技能 ID"""
        return f"skl_{uuid.uuid4().hex[:12]}"
    
    @staticmethod
    def random_string(length: int = 16) -> str:
        """生成随机字符串"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_id(prefix: str = "id") -> str:
    """生成带前缀的 ID"""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"
