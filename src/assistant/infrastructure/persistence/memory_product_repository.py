"""
内存商品仓储实现（Demo 用）
"""
from decimal import Decimal
from typing import List, Optional, Dict

from ...domain.entities.product import Product, Order
from ...domain.repositories.product_repository import ProductRepository, OrderRepository


class MemoryProductRepository(ProductRepository):
    """内存商品仓储"""
    
    def __init__(self):
        self._products: Dict[str, Product] = {}
        self._init_sample_data()
    
    def _init_sample_data(self):
        """初始化示例数据"""
        sample_products = [
            Product(
                id="prod_001",
                name="iPhone 16 Pro",
                description="苹果最新旗舰手机，A18 Pro芯片，钛金属机身",
                price=Decimal("7999.00"),
                original_price=Decimal("8999.00"),
                category="手机数码",
                tags=["苹果", "旗舰", "5G"],
                images=["https://example.com/iphone16.jpg"],
                stock=100,
                sold_count=523,
                merchant_id="merchant_001"
            ),
            Product(
                id="prod_002",
                name="MacBook Pro 14",
                description="M4 Pro芯片，14英寸Liquid Retina XDR显示屏",
                price=Decimal("14999.00"),
                original_price=Decimal("16999.00"),
                category="电脑办公",
                tags=["苹果", "笔记本", "M4"],
                images=["https://example.com/macbook14.jpg"],
                stock=50,
                sold_count=234,
                merchant_id="merchant_001"
            ),
            Product(
                id="prod_003",
                name="AirPods Pro 2",
                description="主动降噪，通透模式，空间音频",
                price=Decimal("1899.00"),
                category="手机数码",
                tags=["苹果", "耳机", "降噪"],
                images=["https://example.com/airpods.jpg"],
                stock=200,
                sold_count=1024,
                merchant_id="merchant_001"
            ),
            Product(
                id="prod_004",
                name="戴森吸尘器 V15",
                description="激光探测，智能调速，60分钟续航",
                price=Decimal("4999.00"),
                original_price=Decimal("5999.00"),
                category="家用电器",
                tags=["戴森", "吸尘器", "智能"],
                images=["https://example.com/dyson.jpg"],
                stock=30,
                sold_count=89,
                merchant_id="merchant_002"
            ),
            Product(
                id="prod_005",
                name="索尼 WH-1000XM5",
                description="行业领先降噪，30小时续航",
                price=Decimal("2499.00"),
                category="手机数码",
                tags=["索尼", "耳机", "降噪"],
                images=["https://example.com/sony.jpg"],
                stock=80,
                sold_count=456,
                merchant_id="merchant_003"
            ),
            Product(
                id="prod_006",
                name="小米空气净化器 4 Pro",
                description="除甲醛，除菌，智能控制",
                price=Decimal("1299.00"),
                original_price=Decimal("1499.00"),
                category="家用电器",
                tags=["小米", "净化器", "智能"],
                images=["https://example.com/mi-purifier.jpg"],
                stock=150,
                sold_count=678,
                merchant_id="merchant_004"
            ),
            Product(
                id="prod_007",
                name="Nike Air Force 1",
                description="经典百搭，舒适耐穿",
                price=Decimal("749.00"),
                category="服饰鞋包",
                tags=["Nike", "运动鞋", "经典"],
                images=["https://example.com/nike-af1.jpg"],
                stock=300,
                sold_count=2345,
                merchant_id="merchant_005"
            ),
            Product(
                id="prod_008",
                name="SK-II 神仙水 230ml",
                description="PITERA精华，改善肤质",
                price=Decimal("1540.00"),
                original_price=Decimal("1690.00"),
                category="美妆护肤",
                tags=["SK-II", "精华", "护肤"],
                images=["https://example.com/sk2.jpg"],
                stock=60,
                sold_count=345,
                merchant_id="merchant_006"
            ),
        ]
        
        for product in sample_products:
            self._products[product.id] = product
    
    async def get_by_id(self, product_id: str) -> Optional[Product]:
        return self._products.get(product_id)
    
    async def search(
        self,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        limit: int = 10
    ) -> List[Product]:
        results = list(self._products.values())
        
        if keyword:
            keyword = keyword.lower()
            results = [
                p for p in results
                if keyword in p.name.lower()
                or keyword in p.description.lower()
                or any(keyword in tag.lower() for tag in p.tags)
            ]
        
        if category:
            results = [p for p in results if p.category == category]
        
        if min_price is not None:
            results = [p for p in results if p.price >= min_price]
        
        if max_price is not None:
            results = [p for p in results if p.price <= max_price]
        
        return results[:limit]
    
    async def get_categories(self) -> List[str]:
        categories = set(p.category for p in self._products.values())
        return sorted(list(categories))
    
    async def update(self, product: Product) -> None:
        self._products[product.id] = product


class MemoryOrderRepository(OrderRepository):
    """内存订单仓储"""
    
    def __init__(self):
        self._orders: Dict[str, Order] = {}
    
    async def save(self, order: Order) -> None:
        self._orders[order.id] = order
    
    async def get_by_id(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)
    
    async def get_by_user(self, user_id: str, limit: int = 10) -> List[Order]:
        orders = [
            o for o in self._orders.values()
            if o.user_id == user_id
        ]
        orders.sort(key=lambda o: o.created_at, reverse=True)
        return orders[:limit]
