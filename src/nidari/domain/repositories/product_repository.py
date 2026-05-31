"""
商品仓储接口
"""
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Optional

from ..entities.product import Product, Order


class ProductRepository(ABC):
    """商品仓储"""
    
    @abstractmethod
    async def get_by_id(self, product_id: str) -> Optional[Product]:
        """根据 ID 获取商品"""
        pass
    
    @abstractmethod
    async def search(
        self,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        limit: int = 10
    ) -> List[Product]:
        """搜索商品"""
        pass
    
    @abstractmethod
    async def get_categories(self) -> List[str]:
        """获取所有分类"""
        pass
    
    @abstractmethod
    async def update(self, product: Product) -> None:
        """更新商品"""
        pass


class OrderRepository(ABC):
    """订单仓储"""
    
    @abstractmethod
    async def save(self, order: Order) -> None:
        """保存订单"""
        pass
    
    @abstractmethod
    async def get_by_id(self, order_id: str) -> Optional[Order]:
        """根据 ID 获取订单"""
        pass
    
    @abstractmethod
    async def get_by_user(self, user_id: str, limit: int = 10) -> List[Order]:
        """获取用户订单"""
        pass
