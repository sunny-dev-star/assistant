# Agent Framework - 技能开发 SDK 文档

## 概述

技能（Skill）是 Agent Framework 的核心扩展单元。每个技能封装了特定行业或场景的能力，包含提示词、工具函数和知识库。

## 快速开始

### 1. 创建技能目录

```bash
mkdir skills/my_skill
cd skills/my_skill
```

### 2. 编写 skill.json

```json
{
  "id": "catering_service",
  "name": "餐饮服务",
  "version": "1.0.0",
  "description": "餐饮行业的智能客服和订座服务",
  "author": "your_name",
  "entry": "main.py",
  "config": {
    "llm_model": "deepseek-chat",
    "temperature": 0.7,
    "max_context": 10
  },
  "tools": [
    "query_menu",
    "make_reservation",
    "reply_review"
  ],
  "dependencies": [],
  "permissions": [
    "read:tenant_data",
    "write:conversation"
  ]
}
```

### 3. 编写主入口 main.py

```python
from agent_framework import Skill, Tool, Context

class CateringService(Skill):
    """餐饮服务技能"""
    
    def __init__(self, config):
        super().__init__(config)
        self.load_prompts()
        self.load_knowledge_base()
    
    @Tool(name="query_menu", description="查询菜单")
    def query_menu(self, ctx: Context, dish_type: str = None):
        """查询菜单信息"""
        menu = self.knowledge_base.get("menu", {})
        if dish_type:
            return menu.get(dish_type, [])
        return menu
    
    @Tool(name="make_reservation", description="预约订座")
    def make_reservation(self, ctx: Context, date: str, time: str, people: int, name: str, phone: str):
        """处理订座请求"""
        # 调用外部系统或记录到数据库
        reservation = {
            "date": date,
            "time": time,
            "people": people,
            "name": name,
            "phone": phone,
            "status": "confirmed"
        }
        # 保存到租户数据库
        ctx.db.reservations.insert(reservation)
        return f"已为您预约 {date} {time}，{people}人，姓名：{name}"
    
    @Tool(name="reply_review", description="回复评价")
    def reply_review(self, ctx: Context, review_content: str, rating: int):
        """自动生成评价回复"""
        if rating >= 4:
            return "感谢您的认可！我们会继续努力，期待您的再次光临！"
        else:
            return "非常抱歉给您带来不好的体验，我们会认真改进。请您联系我们，我们愿意为您提供补偿。"
    
    def handle(self, ctx: Context, message: str):
        """主处理函数"""
        # 使用 LLM 理解意图
        intent = self.classify_intent(message)
        
        if intent == "query_menu":
            return self.query_menu(ctx)
        elif intent == "reservation":
            # 提取实体
            entities = self.extract_entities(message)
            return self.make_reservation(ctx, **entities)
        elif intent == "review":
            return self.reply_review(ctx, message, 5)
        else:
            # 使用通用对话
            return self.chat(ctx, message)
    
    def classify_intent(self, message: str) -> str:
        """意图分类"""
        # 使用 LLM 或规则匹配
        keywords = {
            "query_menu": ["菜单", "有什么菜", "推荐", "价格"],
            "reservation": ["订座", "预约", "定位", "几个人"],
            "review": ["评价", "点评", "反馈"]
        }
        for intent, words in keywords.items():
            if any(w in message for w in words):
                return intent
        return "chat"
```

### 4. 编写提示词 prompts/system.txt

```
你是一位专业的餐饮客服助手，服务于 {restaurant_name}。

你的职责：
1. 回答客户关于菜单、价格、营业时间的问题
2. 帮助客户预约订座
3. 礼貌回复客户评价
4. 推荐招牌菜和优惠活动

规则：
- 语气亲切、热情
- 回答简洁，不超过 100 字
- 不知道的问题不要编造，说"我帮您问一下"
- 涉及退款/投诉时，立即转接人工

当前时间：{current_time}
餐厅信息：
{restaurant_info}
```

### 5. 编写知识库 knowledge/faq.json

```json
{
  "menu": {
    "招牌菜": [
      {"name": "红烧肉", "price": 68, "description": "秘制酱料，肥而不腻"},
      {"name": "清蒸鲈鱼", "price": 88, "description": "新鲜活鱼，现点现做"}
    ],
    "主食": [
      {"name": "扬州炒饭", "price": 28},
      {"name": "牛肉面", "price": 32}
    ]
  },
  "business_hours": "10:00-22:00",
  "phone": "010-12345678",
  "address": "北京市朝阳区xxx路xxx号"
}
```

## 技能注册与加载

### 自动发现

框架启动时自动扫描 `skills/` 目录：

```python
# agent_framework/loader.py
import os
import json
from pathlib import Path

class SkillLoader:
    def __init__(self, skills_dir="skills"):
        self.skills_dir = Path(skills_dir)
        self.skills = {}
    
    def load_all(self):
        """加载所有技能"""
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir():
                self.load_skill(skill_dir)
    
    def load_skill(self, skill_dir: Path):
        """加载单个技能"""
        config_file = skill_dir / "skill.json"
        if not config_file.exists():
            return
        
        with open(config_file) as f:
            config = json.load(f)
        
        skill_id = config["id"]
        entry_file = skill_dir / config["entry"]
        
        # 动态导入
        import importlib.util
        spec = importlib.util.spec_from_file_location(skill_id, entry_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 实例化技能
        skill_class = getattr(module, config.get("class", "Skill"))
        self.skills[skill_id] = skill_class(config)
    
    def reload_skill(self, skill_id: str):
        """热重载技能"""
        if skill_id in self.skills:
            del self.skills[skill_id]
        skill_dir = self.skills_dir / skill_id
        self.load_skill(skill_dir)
    
    def get_skill(self, skill_id: str):
        return self.skills.get(skill_id)
```

### 手动注册

```python
from agent_framework import SkillRegistry

registry = SkillRegistry()
registry.register("catering_service", CateringService)
```

## 上下文对象 Context

```python
class Context:
    """技能运行时的上下文"""
    
    def __init__(self, tenant_id: str, session_id: str, user_id: str):
        self.tenant_id = tenant_id
        self.session_id = session_id
        self.user_id = user_id
        self.db = TenantDatabase(tenant_id)  # 租户隔离的数据库
        self.cache = RedisCache(tenant_id)   # 租户隔离的缓存
        self.config = TenantConfig(tenant_id) # 租户配置
    
    def get_history(self, limit: int = 10):
        """获取对话历史"""
        return self.db.conversations.find(
            {"session_id": self.session_id},
            limit=limit
        )
    
    def save_message(self, role: str, content: str):
        """保存消息"""
        self.db.conversations.insert({
            "session_id": self.session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.now()
        })
```

## 工具装饰器

```python
from agent_framework import Tool

class MySkill(Skill):
    
    @Tool(
        name="send_sms",
        description="发送短信通知",
        parameters={
            "phone": {"type": "string", "required": True},
            "content": {"type": "string", "required": True}
        }
    )
    def send_sms(self, ctx: Context, phone: str, content: str):
        """发送短信"""
        # 调用短信 API
        result = sms_api.send(phone, content)
        return {"success": result.success, "message_id": result.id}
```

## 调试技能

```python
# test_skill.py
from agent_framework import TestRunner

runner = TestRunner()
runner.load_skill("catering_service")

# 运行测试用例
test_cases = [
    {"input": "你们有什么好吃的？", "expected_intent": "query_menu"},
    {"input": "我想订座，今晚7点，4个人", "expected_intent": "reservation"},
]

for case in test_cases:
    result = runner.run(case["input"])
    print(f"输入: {case['input']}")
    print(f"意图: {result.intent}")
    print(f"回复: {result.reply}")
    print("---")
```

## 最佳实践

1. **保持技能单一职责**：一个技能解决一个行业的一个核心问题
2. **配置化**：硬编码越少越好，通过 config 和知识库动态调整
3. **错误处理**：所有工具函数都要处理异常情况
4. **日志记录**：关键操作要记录日志，便于排查问题
5. **测试覆盖**：每个技能至少要有 5 个测试用例
