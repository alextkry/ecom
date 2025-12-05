from rest_framework import serializers
from apps.catalog.models import (
    Product,
    AttributeType,
    AttributeOption,
    Variant,
    VariantAttribute,
    VariantImage,
    VariantGroup,
    VariantGroupMembership,
    PriceHistory,
)


# =============================================================================
# Attribute Serializers
# =============================================================================

class AttributeOptionSerializer(serializers.ModelSerializer):
    attribute_type_name = serializers.CharField(
        source='attribute_type.name', read_only=True
    )
    attribute_type_slug = serializers.CharField(
        source='attribute_type.slug', read_only=True
    )
    
    class Meta:
        model = AttributeOption
        fields = [
            'id', 'attribute_type', 'attribute_type_name', 'attribute_type_slug',
            'value', 'display_value', 'color_hex', 'display_order'
        ]


class AttributeTypeSerializer(serializers.ModelSerializer):
    options = AttributeOptionSerializer(many=True, read_only=True)
    
    class Meta:
        model = AttributeType
        fields = ['id', 'name', 'slug', 'datatype', 'display_order', 'options']


# =============================================================================
# Variant Image Serializer
# =============================================================================

class VariantImageSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()
    thumbnail_small_url = serializers.SerializerMethodField()
    
    class Meta:
        model = VariantImage
        fields = [
            'id', 'image', 'thumbnail_url', 'thumbnail_small_url',
            'alt_text', 'display_order', 'is_primary'
        ]
    
    def get_thumbnail_url(self, obj):
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None
    
    def get_thumbnail_small_url(self, obj):
        if obj.thumbnail_small:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail_small.url)
            return obj.thumbnail_small.url
        return None


# =============================================================================
# Variant Serializers
# =============================================================================

class VariantAttributeSerializer(serializers.ModelSerializer):
    attribute_type = serializers.CharField(
        source='attribute_option.attribute_type.name', read_only=True
    )
    attribute_slug = serializers.CharField(
        source='attribute_option.attribute_type.slug', read_only=True
    )
    value = serializers.CharField(
        source='attribute_option.value', read_only=True
    )
    display_value = serializers.CharField(
        source='attribute_option.get_display_value', read_only=True
    )
    color_hex = serializers.CharField(
        source='attribute_option.color_hex', read_only=True
    )
    
    class Meta:
        model = VariantAttribute
        fields = [
            'id', 'attribute_option', 'attribute_type', 'attribute_slug',
            'value', 'display_value', 'color_hex'
        ]


class VariantSerializer(serializers.ModelSerializer):
    """Base variant serializer."""
    class Meta:
        model = Variant
        fields = [
            'id', 'product', 'sku', 'name', 'cost_price', 'sell_price',
            'compare_at_price', 'stock_quantity', 'track_inventory',
            'allow_backorder', 'low_stock_threshold', 'weight',
            'is_active', 'created_at', 'updated_at'
        ]


class VariantListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for variant lists."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()
    is_in_stock = serializers.BooleanField(read_only=True)
    is_on_sale = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Variant
        fields = [
            'id', 'sku', 'name', 'product', 'product_name',
            'sell_price', 'compare_at_price', 'stock_quantity',
            'is_active', 'is_in_stock', 'is_on_sale', 'discount_percentage',
            'primary_image', 'attributes'
        ]
    
    def get_primary_image(self, obj):
        img = obj.primary_image
        if img:
            request = self.context.get('request')
            if request and img.thumbnail:
                return request.build_absolute_uri(img.thumbnail.url)
            elif img.thumbnail:
                return img.thumbnail.url
        return None
    
    def get_attributes(self, obj):
        return obj.get_options_dict()


class VariantDetailSerializer(serializers.ModelSerializer):
    """Full variant serializer with all related data."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    images = VariantImageSerializer(many=True, read_only=True)
    variant_attributes = VariantAttributeSerializer(
        source='variantattribute_set', many=True, read_only=True
    )
    is_in_stock = serializers.BooleanField(read_only=True)
    is_on_sale = serializers.BooleanField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    profit_margin = serializers.FloatField(read_only=True)
    groups = serializers.SerializerMethodField()
    
    class Meta:
        model = Variant
        fields = [
            'id', 'product', 'product_name', 'product_slug',
            'sku', 'name', 'cost_price', 'sell_price', 'compare_at_price',
            'stock_quantity', 'track_inventory', 'allow_backorder',
            'low_stock_threshold', 'weight', 'is_active',
            'is_in_stock', 'is_on_sale', 'is_low_stock',
            'discount_percentage', 'profit_margin',
            'images', 'variant_attributes', 'groups',
            'created_at', 'updated_at'
        ]
    
    def get_groups(self, obj):
        return [
            {'id': g.id, 'name': g.name, 'slug': g.slug}
            for g in obj.groups.filter(is_active=True)
        ]


# =============================================================================
# Product Serializers
# =============================================================================

class ProductSerializer(serializers.ModelSerializer):
    """Base product serializer."""
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'is_active',
            'created_at', 'updated_at'
        ]


class ProductListSerializer(serializers.ModelSerializer):
    """Product list with counts."""
    variant_count = serializers.IntegerField(read_only=True)
    active_variant_count = serializers.IntegerField(read_only=True)
    min_price = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'is_active',
            'variant_count', 'active_variant_count',
            'min_price', 'primary_image'
        ]
    
    def get_min_price(self, obj):
        variant = obj.variants.filter(is_active=True).order_by('sell_price').first()
        return variant.sell_price if variant else None
    
    def get_primary_image(self, obj):
        variant = obj.variants.filter(is_active=True).prefetch_related('images').first()
        if variant and variant.primary_image:
            request = self.context.get('request')
            if request and variant.primary_image.thumbnail:
                return request.build_absolute_uri(variant.primary_image.thumbnail.url)
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full product detail with variants and attribute types."""
    variants = VariantListSerializer(many=True, read_only=True)
    attribute_types = serializers.SerializerMethodField()
    variant_groups = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'is_active',
            'variants', 'attribute_types', 'variant_groups',
            'created_at', 'updated_at'
        ]
    
    def get_attribute_types(self, obj):
        attr_types = obj.get_attribute_types()
        return AttributeTypeSerializer(attr_types, many=True).data
    
    def get_variant_groups(self, obj):
        groups = obj.variant_groups.filter(is_active=True)
        return [
            {'id': g.id, 'name': g.name, 'slug': g.slug, 'variant_count': g.variant_count}
            for g in groups
        ]


# =============================================================================
# Variant Group Serializers
# =============================================================================

class VariantGroupSerializer(serializers.ModelSerializer):
    """Base variant group serializer."""
    class Meta:
        model = VariantGroup
        fields = [
            'id', 'product', 'name', 'slug', 'description',
            'meta_title', 'meta_description', 'is_active', 'is_featured',
            'display_order', 'created_at', 'updated_at'
        ]


class VariantGroupListSerializer(serializers.ModelSerializer):
    """Variant group list serializer."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    variant_count = serializers.IntegerField(read_only=True)
    price_range = serializers.CharField(read_only=True)
    display_image = serializers.SerializerMethodField()
    
    class Meta:
        model = VariantGroup
        fields = [
            'id', 'name', 'slug', 'product', 'product_name',
            'is_active', 'is_featured', 'variant_count', 'price_range',
            'display_image'
        ]
    
    def get_display_image(self, obj):
        img = obj.display_image
        if img:
            request = self.context.get('request')
            if request and img.thumbnail:
                return request.build_absolute_uri(img.thumbnail.url)
        return None


class VariantGroupDetailSerializer(serializers.ModelSerializer):
    """Full variant group detail with variants and navigation data."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    variants = VariantListSerializer(many=True, read_only=True)
    available_attribute_options = serializers.SerializerMethodField()
    common_attribute_options = serializers.SerializerMethodField()
    related_groups = serializers.SerializerMethodField()
    price_range = serializers.CharField(read_only=True)
    total_stock = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = VariantGroup
        fields = [
            'id', 'product', 'product_name', 'product_slug',
            'name', 'slug', 'description',
            'meta_title', 'meta_description',
            'is_active', 'is_featured', 'display_order',
            'variants', 'price_range', 'total_stock',
            'available_attribute_options', 'common_attribute_options',
            'related_groups',
            'created_at', 'updated_at'
        ]
    
    def get_available_attribute_options(self, obj):
        options = obj.get_available_attribute_options()
        return AttributeOptionSerializer(options, many=True).data
    
    def get_common_attribute_options(self, obj):
        options = obj.get_common_attribute_options()
        return AttributeOptionSerializer(options, many=True).data
    
    def get_related_groups(self, obj):
        """Get other groups from the same product."""
        related = obj.product.variant_groups.filter(
            is_active=True
        ).exclude(pk=obj.pk)[:10]
        return [
            {'id': g.id, 'name': g.name, 'slug': g.slug}
            for g in related
        ]


# =============================================================================
# Price History Serializer
# =============================================================================

class PriceHistorySerializer(serializers.ModelSerializer):
    variant_sku = serializers.CharField(source='variant.sku', read_only=True)
    changed_by_username = serializers.CharField(
        source='changed_by.username', read_only=True
    )
    price_difference = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    percentage_change = serializers.FloatField(read_only=True)
    
    class Meta:
        model = PriceHistory
        fields = [
            'id', 'variant', 'variant_sku', 'change_type',
            'old_price', 'new_price', 'price_difference', 'percentage_change',
            'changed_by', 'changed_by_username', 'changed_at', 'notes'
        ]
