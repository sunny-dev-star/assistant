"""
JSON 工具
"""
import json
from datetime import datetime, date
from typing import Any


class JSONEncoder(json.JSONEncoder):
    """自定义 JSON 编码器"""
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


def to_json(obj: Any) -> str:
    """转换为 JSON 字符串"""
    return json.dumps(obj, cls=JSONEncoder, ensure_ascii=False)


def from_json(json_str: str) -> Any:
    """从 JSON 字符串解析"""
    return json.loads(json_str)
