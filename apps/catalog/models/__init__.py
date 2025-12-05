"""
Catalog models for ecommerce with dynamic product variants.

Model Hierarchy:
- Product: Base product (e.g., "Linha Modelo_X")
- AttributeType: Dynamic attribute types (Color, Length, Number)
- AttributeOption: Values for each attribute type (branco, 230m, 5)
- Variant: Individual SKU with price, stock, images
- VariantGroup: Groups of variants for display purposes
"""

from .product import Product
from .attribute import AttributeType, AttributeOption
from .variant import Variant, VariantAttribute, VariantImage
from .variant_group import VariantGroup, VariantGroupMembership
from .price_history import PriceHistory

__all__ = [
    'Product',
    'AttributeType',
    'AttributeOption',
    'Variant',
    'VariantAttribute',
    'VariantImage',
    'VariantGroup',
    'VariantGroupMembership',
    'PriceHistory',
]
