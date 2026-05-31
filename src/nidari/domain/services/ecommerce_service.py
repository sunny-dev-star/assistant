"""
电商领域服务
处理商品查询、订单创建等业务逻辑
"""
from decimal import Decimal
from typing import List, Optional, Dict
from datetime import datetime

from ..entities.product import Product, Order, OrderItem
from ..repositories.product_repository import ProductRepository
from ...shared.exceptions.domain_exceptions import NotFoundError, ValidationError


class EcommerceService:
    """电商服务"""
    
    def __init__(self, product_repo: ProductRepository):
        self.product_repo = product_repo
    
    async def search_products(
        self,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        sort_by: str = "relevance",
        limit: int = 10
    ) -> List[Product]:
        """搜索商品"""
        products = await self.product_repo.search(
            keyword=keyword,
            category=category,
            min_price=min_price,
            max_price=max_price,
            limit=limit
        )
        
        # 排序
        if sort_by == "price_asc":
            products.sort(key=lambda p: p.price)
        elif sort_by == "price_desc":
            products.sort(key=lambda p: p.price, reverse=True)
        elif sort_by == "sales":
            products.sort(key=lambda p: p.sold_count, reverse=True)
        
        return products
    
    async def get_product_detail(self, product_id: str) -> Product:
        """获取商品详情"""
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError(f"商品不存在: {product_id}")
        return product
    
    async def get_categories(self) -> List[str]:
        """获取所有分类"""
        return await self.product_repo.get_categories()
    
    async def create_order(
        self,
        user_id: str,
        items_data: List[Dict],
        shipping_address: str,
        contact_phone: str,
        contact_name: str,
        remark: str = ""
    ) -> Order:
        """创建订单"""
        if not items_data:
            raise ValidationError("订单商品不能为空")
        
        order = Order(
            user_id=user_id,
            shipping_address=shipping_address,
            contact_phone=contact_phone,
            contact_name=contact_name,
            remark=remark
        )
        
        # 验证商品并创建订单项
        for item_data in items_data:
            product_id = item_data.get("product_id")
            quantity = item_data.get("quantity", 1)
            
            product = await self.product_repo.get_by_id(product_id)
            if not product:
                raise NotFoundError(f"商品不存在: {product_id}")
            
            if product.stock < quantity:
                raise ValidationError(
                    f"商品 '{product.name}' 库存不足，当前库存: {product.stock}"
                )
            
            order.items.append(OrderItem(
                product_id=product.id,
                product_name=product.name,
                quantity=quantity,
                unit_price=product.price
            ))
            
            # 扣减库存
            product.stock -= quantity
            product.sold_count += quantity
            await self.product_repo.update(product)
        
        order.calculate_total()
        return order
    
    async def get_recommendations(
        self,
        user_id: str,
        category: Optional[str] = None,
        limit: int = 5
    ) -> List[Product]:
        """获取推荐商品"""
        # 简单实现：返回销量最高的商品
        products = await self.product_repo.search(
            category=category,
            limit=limit * 2
        )
        products.sort(key=lambda p: p.sold_count, reverse=True)
        return products[:limit]
    
    async def get_hot_products(self, limit: int = 10) -> List[Product]:
        """获取热销商品"""
        products = await self.product_repo.search(limit=limit * 2)
        products.sort(key=lambda p: p.sold_count, reverse=True)
        return products[:limit]
