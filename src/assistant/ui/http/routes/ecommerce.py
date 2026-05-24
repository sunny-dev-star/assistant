"""
电商 API 路由
"""
from fastapi import APIRouter, HTTPException
from typing import Optional

from ....app.use_cases.ecommerce_use_case import EcommerceUseCase
from ....app.dtos.ecommerce_dto import (
    ProductSearchRequest, ProductSearchResponse,
    ProductDetailResponse, OrderCreateRequest, OrderCreateResponse,
    CategoryListResponse, ProductRecommendationResponse,
    ChatMessageRequest, ChatMessageResponse
)

router = APIRouter(prefix="/ecommerce", tags=["电商"])

# 初始化用例
ecommerce_use_case = EcommerceUseCase()


@router.get("/products", response_model=ProductSearchResponse)
async def search_products(
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[str] = None,
    max_price: Optional[str] = None,
    sort_by: str = "relevance",
    limit: int = 10
):
    """搜索商品"""
    request = ProductSearchRequest(
        keyword=keyword,
        category=category,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        limit=limit
    )
    return await ecommerce_use_case.search_products(request)


@router.get("/products/{product_id}", response_model=ProductDetailResponse)
async def get_product_detail(product_id: str):
    """获取商品详情"""
    try:
        return await ecommerce_use_case.get_product_detail(product_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/categories", response_model=CategoryListResponse)
async def get_categories():
    """获取分类列表"""
    return await ecommerce_use_case.get_categories()


@router.get("/products/hot", response_model=ProductSearchResponse)
async def get_hot_products(limit: int = 10):
    """获取热销商品"""
    return await ecommerce_use_case.get_hot_products(limit=limit)


@router.post("/orders", response_model=OrderCreateResponse)
async def create_order(request: OrderCreateRequest):
    """创建订单"""
    try:
        return await ecommerce_use_case.create_order(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/recommendations", response_model=ProductRecommendationResponse)
async def get_recommendations(
    user_id: str = "user_001",
    category: Optional[str] = None,
    limit: int = 5
):
    """获取推荐商品"""
    return await ecommerce_use_case.get_recommendations(
        user_id=user_id,
        category=category,
        limit=limit
    )


@router.post("/chat", response_model=ChatMessageResponse)
async def ecommerce_chat(request: ChatMessageRequest):
    """电商智能客服聊天"""
    message = request.message.lower()
    
    # 简单的意图识别
    if any(kw in message for kw in ["搜索", "找", "有没有", "推荐"]):
        # 提取关键词
        keyword = message.replace("搜索", "").replace("找", "").replace("有没有", "").replace("推荐", "").strip()
        if keyword:
            result = await ecommerce_use_case.search_products(
                ProductSearchRequest(keyword=keyword, limit=5)
            )
            products = result.products
            if products:
                reply = f"为您找到 {len(products)} 款商品：\n\n"
                for i, p in enumerate(products, 1):
                    reply += f"{i}. {p['name']} - ¥{p['price']}"
                    if p.get('is_on_sale'):
                        reply += f" (原价 ¥{p['original_price']}, 省 ¥{float(p['original_price']) - float(p['price']):.0f})"
                    reply += f"\n   {p['description'][:50]}...\n\n"
                
                return ChatMessageResponse(
                    reply=reply,
                    session_id=request.session_id or "session_001",
                    suggestions=["查看详情", "加入购物车", "看看其他"],
                    actions=[
                        {
                            "type": "show_products",
                            "products": [p['id'] for p in products]
                        }
                    ]
                )
            else:
                return ChatMessageResponse(
                    reply=f"抱歉，没有找到与 '{keyword}' 相关的商品。试试其他关键词？",
                    session_id=request.session_id or "session_001",
                    suggestions=["手机数码", "家用电器", "服饰鞋包", "美妆护肤"]
                )
    
    elif any(kw in message for kw in ["分类", "类别", "有什么"]):
        result = await ecommerce_use_case.get_categories()
        return ChatMessageResponse(
            reply=f"我们有以下分类：{', '.join(result.categories)}\n\n您想查看哪个分类？",
            session_id=request.session_id or "session_001",
            suggestions=result.categories
        )
    
    elif any(kw in message for kw in ["热销", "热门", "畅销", "排行榜"]):
        result = await ecommerce_use_case.get_hot_products(limit=5)
        products = result.products
        reply = "🔥 热销商品排行榜：\n\n"
        for i, p in enumerate(products, 1):
            reply += f"{i}. {p['name']} - ¥{p['price']} (已售 {p['sold_count']} 件)\n"
        
        return ChatMessageResponse(
            reply=reply,
            session_id=request.session_id or "session_001",
            suggestions=["查看详情", "我要买", "看看新品"]
        )
    
    elif any(kw in message for kw in ["下单", "购买", "买", "订单"]):
        return ChatMessageResponse(
            reply="好的，我来帮您下单。请告诉我：\n1. 商品名称或 ID\n2. 数量\n3. 收货地址\n4. 联系电话",
            session_id=request.session_id or "session_001",
            suggestions=["查看购物车", "我的订单", "继续购物"]
        )
    
    elif any(kw in message for kw in ["你好", "您好", "在吗", "hi", "hello"]):
        return ChatMessageResponse(
            reply="您好！我是您的智能购物助手 🛍️\n\n我可以帮您：\n• 搜索商品\n• 查看分类\n• 了解热销商品\n• 推荐好物\n\n请问您想做什么？",
            session_id=request.session_id or "session_001",
            suggestions=["搜索商品", "查看分类", "热销排行", "推荐好物"]
        )
    
    else:
        return ChatMessageResponse(
            reply="抱歉，我没太明白。您可以尝试：\n• '搜索 iPhone' - 查找商品\n• '有什么分类' - 查看分类\n• '热销商品' - 查看排行榜\n• '推荐好物' - 获取推荐",
            session_id=request.session_id or "session_001",
            suggestions=["搜索商品", "查看分类", "热销排行", "推荐好物"]
        )
