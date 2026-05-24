"""
电商用例
"""
from decimal import Decimal
from typing import List, Optional, Dict

from ...domain.services.ecommerce_service import EcommerceService
from ...domain.entities.product import Product, Order
from ...infrastructure.persistence.memory_product_repository import (
    MemoryProductRepository, MemoryOrderRepository
)
from ..dtos.ecommerce_dto import (
    ProductSearchRequest, ProductSearchResponse,
    ProductDetailResponse, OrderCreateRequest, OrderCreateResponse,
    CategoryListResponse, ProductRecommendationResponse
)


class EcommerceUseCase:
    """电商用例"""
    
    def __init__(self):
        self.product_repo = MemoryProductRepository()
        self.order_repo = MemoryOrderRepository()
        self.ecommerce_service = EcommerceService(self.product_repo)
    
    async def search_products(self, request: ProductSearchRequest) -> ProductSearchResponse:
        """搜索商品"""
        products = await self.ecommerce_service.search_products(
            keyword=request.keyword,
            category=request.category,
            min_price=Decimal(request.min_price) if request.min_price else None,
            max_price=Decimal(request.max_price) if request.max_price else None,
            sort_by=request.sort_by,
            limit=request.limit
        )
        
        return ProductSearchResponse(
            total=len(products),
            products=[p.to_dict() for p in products]
        )
    
    async def get_product_detail(self, product_id: str) -> ProductDetailResponse:
        """获取商品详情"""
        product = await self.ecommerce_service.get_product_detail(product_id)
        return ProductDetailResponse(product=product.to_dict())
    
    async def get_categories(self) -> CategoryListResponse:
        """获取分类列表"""
        categories = await self.ecommerce_service.get_categories()
        return CategoryListResponse(categories=categories)
    
    async def create_order(self, request: OrderCreateRequest) -> OrderCreateResponse:
        """创建订单"""
        order = await self.ecommerce_service.create_order(
            user_id=request.user_id,
            items_data=request.items,
            shipping_address=request.shipping_address,
            contact_phone=request.contact_phone,
            contact_name=request.contact_name,
            remark=request.remark
        )
        
        await self.order_repo.save(order)
        
        return OrderCreateResponse(
            order_id=order.id,
            total_amount=str(order.total_amount),
            status=order.status,
            message="订单创建成功"
        )
    
    async def get_recommendations(
        self,
        user_id: str,
        category: Optional[str] = None,
        limit: int = 5
    ) -> ProductRecommendationResponse:
        """获取推荐"""
        products = await self.ecommerce_service.get_recommendations(
            user_id=user_id,
            category=category,
            limit=limit
        )
        
        return ProductRecommendationResponse(
            products=[p.to_dict() for p in products]
        )
    
    async def get_hot_products(self, limit: int = 10) -> ProductSearchResponse:
        """获取热销商品"""
        products = await self.ecommerce_service.get_hot_products(limit=limit)
        
        return ProductSearchResponse(
            total=len(products),
            products=[p.to_dict() for p in products]
        )
