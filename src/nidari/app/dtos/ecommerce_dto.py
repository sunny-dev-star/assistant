"""
电商 DTO
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ProductSearchRequest(BaseModel):
    """商品搜索请求"""
    keyword: Optional[str] = None
    category: Optional[str] = None
    min_price: Optional[str] = None
    max_price: Optional[str] = None
    sort_by: str = "relevance"  # relevance, price_asc, price_desc, sales
    limit: int = 10


class ProductSearchResponse(BaseModel):
    """商品搜索响应"""
    total: int
    products: List[Dict[str, Any]]


class ProductDetailResponse(BaseModel):
    """商品详情响应"""
    product: Dict[str, Any]


class OrderItemRequest(BaseModel):
    """订单项请求"""
    product_id: str
    quantity: int = 1


class OrderCreateRequest(BaseModel):
    """创建订单请求"""
    user_id: str
    items: List[Dict[str, Any]]
    shipping_address: str
    contact_phone: str
    contact_name: str
    remark: str = ""


class OrderCreateResponse(BaseModel):
    """创建订单响应"""
    order_id: str
    total_amount: str
    status: str
    message: str


class CategoryListResponse(BaseModel):
    """分类列表响应"""
    categories: List[str]


class ProductRecommendationResponse(BaseModel):
    """商品推荐响应"""
    products: List[Dict[str, Any]]


class ChatMessageRequest(BaseModel):
    """聊天消息请求"""
    message: str
    user_id: str = "user_001"
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatMessageResponse(BaseModel):
    """聊天消息响应"""
    reply: str
    session_id: str
    actions: Optional[List[Dict[str, Any]]] = None
    suggestions: Optional[List[str]] = None
