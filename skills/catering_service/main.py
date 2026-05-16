"""
餐饮服务技能
"""
from agent_framework import Skill, Tool, Context


class CateringService(Skill):
    """餐饮服务技能"""
    
    def __init__(self, config):
        super().__init__(config)
    
    @Tool(name="query_menu", description="查询菜单")
    def query_menu(self, ctx: Context, dish_type: str = None):
        """查询菜单信息"""
        menu = self.knowledge_base.get("menu", {})
        
        if dish_type:
            dishes = menu.get(dish_type, [])
            if not dishes:
                return f"抱歉，暂时没有{dish_type}的分类，我们有的分类有：{', '.join(menu.keys())}"
            
            result = f"【{dish_type}】\n"
            for dish in dishes:
                result += f"• {dish['name']} - ¥{dish['price']}"
                if "description" in dish:
                    result += f" ({dish['description']})"
                result += "\n"
            return result
        
        # 返回全部分类
        result = "我们的菜单：\n"
        for category, dishes in menu.items():
            result += f"\n【{category}】\n"
            for dish in dishes[:3]:  # 每类只显示前3个
                result += f"• {dish['name']} - ¥{dish['price']}\n"
            if len(dishes) > 3:
                result += f"  ... 还有 {len(dishes) - 3} 道菜\n"
        
        return result
    
    @Tool(name="make_reservation", description="预约订座")
    def make_reservation(self, ctx: Context, date: str = None, time: str = None, people: int = None, name: str = None, phone: str = None):
        """处理订座请求"""
        # 检查必要信息
        missing = []
        if not date:
            missing.append("日期")
        if not time:
            missing.append("时间")
        if not people:
            missing.append("人数")
        if not name:
            missing.append("姓名")
        if not phone:
            missing.append("电话")
        
        if missing:
            return f"预约需要以下信息：{', '.join(missing)}。请告诉我您的{missing[0]}。"
        
        # 保存预约
        reservation = {
            "date": date,
            "time": time,
            "people": people,
            "name": name,
            "phone": phone,
            "status": "confirmed",
            "tenant_id": ctx.tenant_id
        }
        
        # TODO: 保存到数据库
        # ctx.db.reservations.insert(reservation)
        
        return f"✅ 预约成功！\n日期：{date}\n时间：{time}\n人数：{people}人\n姓名：{name}\n电话：{phone}\n\n我们已为您预留座位，期待您的光临！"
    
    @Tool(name="reply_review", description="回复评价")
    def reply_review(self, ctx: Context, review_content: str = None, rating: int = None):
        """自动生成评价回复"""
        if not rating:
            return "请问这位顾客的评分是多少呢？（1-5星）"
        
        if rating >= 4:
            return "感谢您的认可！我们会继续努力，期待您的再次光临！🌟"
        elif rating == 3:
            return "感谢您的反馈，我们会认真听取您的建议，持续改进服务质量。"
        else:
            return "非常抱歉给您带来不好的体验，我们会认真改进。请您联系我们，我们愿意为您提供补偿。🙏"
    
    @Tool(name="check_business_hours", description="查询营业时间")
    def check_business_hours(self, ctx: Context):
        """查询营业时间"""
        hours = self.knowledge_base.get("business_hours", "10:00-22:00")
        return f"我们的营业时间是：{hours}\n全年无休，欢迎随时光临！"
    
    def handle(self, ctx: Context, message: str) -> str:
        """主处理函数"""
        # 意图分类
        intent = self.classify_intent(message)
        
        if intent == "query_menu":
            # 提取菜品类型
            dish_types = list(self.knowledge_base.get("menu", {}).keys())
            for dt in dish_types:
                if dt in message:
                    return self.query_menu(ctx, dt)
            return self.query_menu(ctx)
        
        elif intent == "reservation":
            # 提取预约信息
            entities = self.extract_reservation_info(message)
            return self.make_reservation(ctx, **entities)
        
        elif intent == "business_hours":
            return self.check_business_hours(ctx)
        
        elif intent == "review":
            # 尝试提取评分
            rating = None
            for i in range(5, 0, -1):
                if f"{i}星" in message or f"{i}分" in message:
                    rating = i
                    break
            return self.reply_review(ctx, message, rating)
        
        else:
            # 通用对话
            system_prompt = self.prompts.get("system", "你是一位专业的餐饮客服。")
            return self.chat(ctx, message, system_prompt)
    
    def classify_intent(self, message: str) -> str:
        """意图分类"""
        keywords = {
            "query_menu": ["菜单", "有什么菜", "推荐", "价格", "多少钱", "吃什么"],
            "reservation": ["订座", "预约", "定位", "订位", "几个人", "包厢"],
            "business_hours": ["营业", "几点开", "几点关", "关门", "开门"],
            "review": ["评价", "点评", "反馈", "差评", "好评", "投诉"]
        }
        
        for intent, words in keywords.items():
            if any(w in message for w in words):
                return intent
        
        return "chat"
    
    def extract_reservation_info(self, message: str) -> dict:
        """提取预约信息"""
        import re
        
        entities = {
            "date": None,
            "time": None,
            "people": None,
            "name": None,
            "phone": None
        }
        
        # 提取人数
        people_match = re.search(r'(\d+)\s*个人', message)
        if people_match:
            entities["people"] = int(people_match.group(1))
        
        # 提取时间（简化处理）
        time_match = re.search(r'(\d{1,2})[:\：]?(\d{2})', message)
        if time_match:
            entities["time"] = f"{time_match.group(1)}:{time_match.group(2)}"
        
        # 提取日期（简化处理）
        if "今天" in message:
            from datetime import datetime
            entities["date"] = datetime.now().strftime("%Y-%m-%d")
        elif "明天" in message:
            from datetime import datetime, timedelta
            entities["date"] = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        return entities
