from django.db import models as db_models
from django_filters import rest_framework as filters
from apps.catalog.models import Variant, VariantGroup


class VariantFilter(filters.FilterSet):
    """Filter for variants with support for dynamic attributes."""
    
    product = filters.CharFilter(field_name='product__slug')
    product_id = filters.NumberFilter(field_name='product__id')
    
    # Price filters
    min_price = filters.NumberFilter(field_name='sell_price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='sell_price', lookup_expr='lte')
    
    # Stock filters
    in_stock = filters.BooleanFilter(method='filter_in_stock')
    low_stock = filters.BooleanFilter(method='filter_low_stock')
    
    # Attribute filters
    attribute = filters.CharFilter(method='filter_by_attribute')
    
    class Meta:
        model = Variant
        fields = ['product', 'product_id', 'is_active', 'sku']
    
    def filter_in_stock(self, queryset, name, value):
        if value is True:
            return queryset.filter(stock_quantity__gt=0) | queryset.filter(
                track_inventory=False
            ) | queryset.filter(allow_backorder=True)
        elif value is False:
            return queryset.filter(
                stock_quantity__lte=0,
                track_inventory=True,
                allow_backorder=False
            )
        return queryset
    
    def filter_low_stock(self, queryset, name, value):
        if value is True:
            return queryset.filter(
                stock_quantity__gt=0,
                stock_quantity__lte=db_models.F('low_stock_threshold'),
                track_inventory=True
            )
        return queryset
    
    def filter_by_attribute(self, queryset, name, value):
        """
        Filter by attribute in format: attribute_slug:option_value
        Example: ?attribute=color:branco
        """
        if ':' not in value:
            return queryset
        
        attr_slug, option_value = value.split(':', 1)
        return queryset.filter(
            variantattribute__attribute_option__attribute_type__slug=attr_slug,
            variantattribute__attribute_option__value=option_value
        )


class VariantGroupFilter(filters.FilterSet):
    """Filter for variant groups."""
    
    product = filters.CharFilter(field_name='product__slug')
    product_id = filters.NumberFilter(field_name='product__id')
    
    class Meta:
        model = VariantGroup
        fields = ['product', 'product_id', 'is_active', 'is_featured']
