"""
技能实体 (Skill Entity)
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid


@dataclass
class Skill:
    """技能实体"""
    
    id: str = field(default_factory=lambda: f"skl_{uuid.uuid4().hex[:12]}")
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    
    entry_point: str = ""  # 入口文件
    class_name: str = "Skill"
    
    config: Dict[str, Any] = field(default_factory=dict)
    tools: List[Dict[str, Any]] = field(default_factory=list)
    
    status: str = "active"  # active / inactive / error
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_active(self) -> bool:
        """检查技能是否可用"""
        return self.status == "active"
    
    def update_config(self, config: Dict[str, Any]):
        """更新配置"""
        self.config.update(config)
        self.updated_at = datetime.utcnow()
    
    def add_tool(self, tool: Dict[str, Any]):
        """添加工具"""
        self.tools.append(tool)
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "entry_point": self.entry_point,
            "class_name": self.class_name,
            "config": self.config,
            "tools": self.tools,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
