from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ProductViewSet,
    AttributeTypeViewSet,
    AttributeOptionViewSet,
    VariantViewSet,
    VariantGroupViewSet,
    PriceHistoryViewSet,
)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'attribute-types', AttributeTypeViewSet, basename='attribute-type')
router.register(r'attribute-options', AttributeOptionViewSet, basename='attribute-option')
router.register(r'variants', VariantViewSet, basename='variant')
router.register(r'variant-groups', VariantGroupViewSet, basename='variant-group')
router.register(r'price-history', PriceHistoryViewSet, basename='price-history')

urlpatterns = [
    path('', include(router.urls)),
]
