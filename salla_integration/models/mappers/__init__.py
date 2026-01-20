# Entity mappers for Salla Integration

from salla_integration.models.mappers.product_mapper import ProductMapper
from salla_integration.models.mappers.category_mapper import CategoryMapper
from Trash.customer_mapper import CustomerMapper
from salla_integration.models.mappers.order_mapper import OrderMapper

__all__ = [
    "ProductMapper",
    "CategoryMapper",
    "CustomerMapper",
    "OrderMapper",
]
