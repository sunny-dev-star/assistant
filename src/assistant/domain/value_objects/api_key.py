"""
API Key 值对象
"""
import uuid
import secrets
import hashlib


class ApiKey:
    """API Key 值对象"""
    
    def __init__(self, value: str):
        self._value = value
        self._hash = hashlib.sha256(value.encode()).hexdigest()
    
    @property
    def value(self) -> str:
        return self._value
    
    @property
    def hash(self) -> str:
        return self._hash
    
    @classmethod
    def generate(cls) -> "ApiKey":
        """生成新的 API Key"""
        key = f"ak_{secrets.token_urlsafe(32)}"
        return cls(key)
    
    def verify(self, key: str) -> bool:
        """验证 API Key"""
        return self._value == key
    
    def __eq__(self, other) -> bool:
        if isinstance(other, ApiKey):
            return self._hash == other._hash
        return False
    
    def __hash__(self) -> int:
        return hash(self._hash)
    
    def __repr__(self) -> str:
        return f"ApiKey({self._value[:8]}...)"
