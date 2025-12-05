from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch

from apps.catalog.models import (
    Product,
    AttributeType,
    AttributeOption,
    Variant,
    VariantImage,
    VariantGroup,
    PriceHistory,
)
from apps.catalog.services import VariantNavigationService
from .serializers import (
    ProductSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    AttributeTypeSerializer,
    AttributeOptionSerializer,
    VariantSerializer,
    VariantListSerializer,
    VariantDetailSerializer,
    VariantGroupSerializer,
    VariantGroupListSerializer,
    VariantGroupDetailSerializer,
    PriceHistorySerializer,
)
from .filters import VariantFilter, VariantGroupFilter


class ProductViewSet(viewsets.ModelViewSet):
    """
    API endpoint for products.
    
    list: List all products
    retrieve: Get product detail with variants
    create: Create a new product
    update: Update a product
    delete: Delete a product
    """
    queryset = Product.objects.all()
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        elif self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related(
                Prefetch(
                    'variants',
                    queryset=Variant.objects.filter(is_active=True).prefetch_related(
                        'images', 'variantattribute_set__attribute_option__attribute_type'
                    )
                ),
                'variant_groups'
            )
        return queryset


class AttributeTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for attribute types (Color, Length, Number, etc).
    """
    queryset = AttributeType.objects.prefetch_related('options')
    serializer_class = AttributeTypeSerializer
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering = ['display_order', 'name']


class AttributeOptionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for attribute options.
    """
    queryset = AttributeOption.objects.select_related('attribute_type')
    serializer_class = AttributeOptionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['attribute_type', 'attribute_type__slug']
    search_fields = ['value', 'display_value']


class VariantViewSet(viewsets.ModelViewSet):
    """
    API endpoint for variants.
    
    Supports filtering by product, attributes, price range, stock status.
    """
    queryset = Variant.objects.select_related('product').prefetch_related(
        'images', 'variantattribute_set__attribute_option__attribute_type'
    )
    filterset_class = VariantFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['sku', 'name', 'product__name']
    ordering_fields = ['sku', 'sell_price', 'stock_quantity', 'created_at']
    ordering = ['sku']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return VariantListSerializer
        elif self.action == 'retrieve':
            return VariantDetailSerializer
        return VariantSerializer
    
    @action(detail=True, methods=['get'])
    def price_history(self, request, pk=None):
        """Get price history for a variant."""
        variant = self.get_object()
        history = PriceHistory.objects.filter(variant=variant).select_related('changed_by')
        serializer = PriceHistorySerializer(history, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_update_prices(self, request):
        """
        Bulk update variant prices.
        
        Expected payload:
        {
            "updates": [
                {"id": 1, "sell_price": 99.99, "cost_price": 50.00},
                {"id": 2, "sell_price": 149.99}
            ]
        }
        """
        updates = request.data.get('updates', [])
        updated_count = 0
        errors = []
        
        for update in updates:
            variant_id = update.get('id')
            if not variant_id:
                continue
            
            try:
                variant = Variant.objects.get(pk=variant_id)
                
                if 'sell_price' in update:
                    variant.sell_price = update['sell_price']
                if 'cost_price' in update:
                    variant.cost_price = update['cost_price']
                if 'compare_at_price' in update:
                    variant.compare_at_price = update['compare_at_price']
                
                variant.save()
                updated_count += 1
            except Variant.DoesNotExist:
                errors.append(f"Variant {variant_id} not found")
            except Exception as e:
                errors.append(f"Error updating variant {variant_id}: {str(e)}")
        
        return Response({
            'updated': updated_count,
            'errors': errors
        })
    
    @action(detail=False, methods=['post'])
    def bulk_update_stock(self, request):
        """
        Bulk update variant stock quantities.
        
        Expected payload:
        {
            "updates": [
                {"id": 1, "stock_quantity": 100},
                {"id": 2, "stock_quantity": 50}
            ]
        }
        """
        updates = request.data.get('updates', [])
        updated_ids = []
        
        for update in updates:
            variant_id = update.get('id')
            stock = update.get('stock_quantity')
            
            if variant_id and stock is not None:
                Variant.objects.filter(pk=variant_id).update(stock_quantity=stock)
                updated_ids.append(variant_id)
        
        return Response({'updated': len(updated_ids), 'ids': updated_ids})


class VariantGroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint for variant groups.
    """
    queryset = VariantGroup.objects.select_related('product').prefetch_related(
        'variants__images'
    )
    filterset_class = VariantGroupFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'product__name']
    ordering_fields = ['name', 'display_order', 'created_at']
    ordering = ['display_order', 'name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return VariantGroupListSerializer
        elif self.action == 'retrieve':
            return VariantGroupDetailSerializer
        return VariantGroupSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related(
                Prefetch(
                    'variants',
                    queryset=Variant.objects.filter(is_active=True).prefetch_related(
                        'images', 'variantattribute_set__attribute_option__attribute_type'
                    )
                )
            )
        return queryset
    
    @action(detail=True, methods=['get'])
    def navigation(self, request, pk=None):
        """
        Get navigation data for this variant group.
        Returns available attribute options for navigation between groups/variants.
        """
        group = self.get_object()
        navigation_data = VariantNavigationService.get_navigation_data(group)
        return Response(navigation_data)
    
    @action(detail=False, methods=['get'])
    def find_best_match(self, request):
        """
        Find the best matching group or variant based on attribute selections.
        
        Query params:
        - product_slug: Required
        - Any attribute_slug=value pairs (e.g., ?color=branco&number=5)
        """
        product_slug = request.query_params.get('product_slug')
        if not product_slug:
            return Response(
                {'error': 'product_slug is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product = Product.objects.get(slug=product_slug)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Build attribute selections from query params
        exclude_params = ['product_slug', 'format']
        selections = {
            k: v for k, v in request.query_params.items()
            if k not in exclude_params
        }
        
        result = VariantNavigationService.find_best_match(product, selections)
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def add_variants(self, request):
        """
        Add variants to a group.
        
        Expected payload:
        {
            "group_id": 1,
            "variant_ids": [1, 2, 3, 4]
        }
        """
        group_id = request.data.get('group_id')
        variant_ids = request.data.get('variant_ids', [])
        
        try:
            group = VariantGroup.objects.get(pk=group_id)
        except VariantGroup.DoesNotExist:
            return Response(
                {'error': 'Group not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        added = 0
        for variant_id in variant_ids:
            try:
                variant = Variant.objects.get(pk=variant_id, product=group.product)
                _, created = group.variants.through.objects.get_or_create(
                    variant_group=group,
                    variant=variant
                )
                if created:
                    added += 1
            except Variant.DoesNotExist:
                pass
        
        return Response({'added': added})
    
    @action(detail=False, methods=['post'])
    def remove_variants(self, request):
        """
        Remove variants from a group.
        
        Expected payload:
        {
            "group_id": 1,
            "variant_ids": [1, 2]
        }
        """
        group_id = request.data.get('group_id')
        variant_ids = request.data.get('variant_ids', [])
        
        try:
            group = VariantGroup.objects.get(pk=group_id)
        except VariantGroup.DoesNotExist:
            return Response(
                {'error': 'Group not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        deleted, _ = group.variants.through.objects.filter(
            variant_group=group,
            variant_id__in=variant_ids
        ).delete()
        
        return Response({'removed': deleted})


class PriceHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for price history (read-only).
    """
    queryset = PriceHistory.objects.select_related('variant', 'changed_by')
    serializer_class = PriceHistorySerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['variant', 'change_type']
    ordering = ['-changed_at']
