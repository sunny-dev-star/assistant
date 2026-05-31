"""
商品实体
电商场景核心实体
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from ...shared.utils.id_generator import generate_id


@dataclass
class Product:
    """商品"""
    id: str = field(default_factory=lambda: generate_id("prod"))
    name: str = ""
    description: str = ""
    price: Decimal = Decimal("0.00")
    original_price: Optional[Decimal] = None
    category: str = ""
    tags: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    stock: int = 0
    sold_count: int = 0
    status: str = "active"  # active, inactive, sold_out
    merchant_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def discount_rate(self) -> Optional[float]:
        """折扣率"""
        if self.original_price and self.original_price > 0:
            return float(self.price / self.original_price)
        return None
    
    @property
    def is_on_sale(self) -> bool:
        """是否在促销"""
        return self.original_price is not None and self.price < self.original_price
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": str(self.price),
            "original_price": str(self.original_price) if self.original_price else None,
            "discount_rate": self.discount_rate,
            "is_on_sale": self.is_on_sale,
            "category": self.category,
            "tags": self.tags,
            "images": self.images,
            "stock": self.stock,
            "sold_count": self.sold_count,
            "status": self.status,
            "merchant_id": self.merchant_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class OrderItem:
    """订单项"""
    product_id: str = ""
    product_name: str = ""
    quantity: int = 1
    unit_price: Decimal = Decimal("0.00")
    
    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass
class Order:
    """订单"""
    id: str = field(default_factory=lambda: generate_id("ord"))
    user_id: str = ""
    items: List[OrderItem] = field(default_factory=list)
    status: str = "pending"  # pending, paid, shipped, completed, cancelled
    total_amount: Decimal = Decimal("0.00")
    shipping_address: str = ""
    contact_phone: str = ""
    contact_name: str = ""
    remark: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def calculate_total(self) -> Decimal:
        """计算订单总额"""
        self.total_amount = sum(item.subtotal for item in self.items)
        return self.total_amount
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "items": [
                {
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "unit_price": str(item.unit_price),
                    "subtotal": str(item.subtotal),
                }
                for item in self.items
            ],
            "status": self.status,
            "total_amount": str(self.total_amount),
            "shipping_address": self.shipping_address,
            "contact_phone": self.contact_phone,
            "contact_name": self.contact_name,
            "remark": self.remark,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
