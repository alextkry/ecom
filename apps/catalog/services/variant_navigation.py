"""
Service for handling navigation between variant groups and products.
Dependencies are INFERRED from actual variant data, not configured manually.
"""

from django.db.models import Q, Count
from typing import Dict, List, Optional, Tuple, Any

from apps.catalog.models import (
    Product,
    AttributeType,
    AttributeOption,
    Variant,
    VariantGroup,
)


class VariantNavigationService:
    """
    Service to handle navigation between variant groups and products.
    Dependencies are INFERRED from actual variant data, not configured manually.
    """
    
    @staticmethod
    def get_available_options_for_selection(
        product: Product,
        current_selections: Dict[str, str],
        target_attribute_slug: str
    ) -> List[AttributeOption]:
        """
        Given current selections, return which options are available for target attribute.
        
        This is the KEY feature that handles implicit dependencies.
        
        Example:
            current_selections = {'number': '5'}
            target_attribute_slug = 'length'
            -> Returns only ['230m'] because Number 5 only exists with Length 230m
        
        Args:
            product: The product to search within
            current_selections: Dict of {attribute_slug: option_value}
            target_attribute_slug: The attribute to get available options for
        
        Returns:
            QuerySet of available AttributeOption objects
        """
        queryset = Variant.objects.filter(product=product, is_active=True)
        
        # Apply current selections as filters
        for attr_slug, value in current_selections.items():
            if attr_slug == target_attribute_slug:
                continue  # Skip the target attribute itself
            
            queryset = queryset.filter(
                variantattribute__attribute_option__attribute_type__slug=attr_slug,
                variantattribute__attribute_option__value=value
            )
        
        # Get distinct options for target attribute
        return AttributeOption.objects.filter(
            attribute_type__slug=target_attribute_slug,
            variants__in=queryset
        ).distinct().order_by('display_order', 'value')

    @staticmethod
    def get_all_available_options(
        product: Product,
        current_selections: Dict[str, str]
    ) -> Dict[str, List[Dict]]:
        """
        Get all available options for each attribute type, given current selections.
        
        Returns:
            Dict with attribute slugs as keys and lists of available options as values
        """
        attribute_types = AttributeType.objects.filter(
            options__variants__product=product
        ).distinct().order_by('display_order')
        
        result = {}
        
        for attr_type in attribute_types:
            # Get selections excluding this attribute type
            other_selections = {
                k: v for k, v in current_selections.items()
                if k != attr_type.slug
            }
            
            available = VariantNavigationService.get_available_options_for_selection(
                product,
                other_selections,
                attr_type.slug
            )
            
            # Mark which option is currently selected
            current_value = current_selections.get(attr_type.slug)
            
            result[attr_type.slug] = {
                'name': attr_type.name,
                'slug': attr_type.slug,
                'options': [
                    {
                        'id': opt.id,
                        'value': opt.value,
                        'display_value': opt.get_display_value(),
                        'color_hex': opt.color_hex,
                        'is_selected': opt.value == current_value,
                    }
                    for opt in available
                ]
            }
        
        return result

    @staticmethod
    def find_best_matching_group(
        product: Product,
        attribute_selections: Dict[str, str]
    ) -> Tuple[Optional[VariantGroup], int]:
        """
        Find the variant group that best matches the given attribute selections.
        
        Args:
            product: The product to search within
            attribute_selections: Dict of {attribute_slug: option_value}
        
        Returns:
            Tuple of (best matching group or None, match score)
        """
        groups = VariantGroup.objects.filter(
            product=product,
            is_active=True
        ).prefetch_related(
            'variants__variantattribute_set__attribute_option__attribute_type'
        )
        
        if not attribute_selections:
            # Return first featured group or first group
            featured = groups.filter(is_featured=True).first()
            return (featured or groups.first(), 0)
        
        best_match = None
        best_score = -1
        
        for group in groups:
            score = VariantNavigationService._calculate_group_match_score(
                group, attribute_selections
            )
            
            if score > best_score:
                best_score = score
                best_match = group
        
        return best_match, best_score

    @staticmethod
    def _calculate_group_match_score(
        group: VariantGroup,
        selections: Dict[str, str]
    ) -> int:
        """
        Calculate how well a group matches the given selections.
        
        Score is based on:
        - +2 for each attribute that ALL variants in the group share
        - +1 for each attribute that SOME variants in the group have
        """
        if not group.variants.exists():
            return -1
        
        variant_count = group.variants.count()
        score = 0
        
        for attr_slug, value in selections.items():
            # Count how many variants in this group have this attribute value
            matching_count = group.variants.filter(
                variantattribute__attribute_option__attribute_type__slug=attr_slug,
                variantattribute__attribute_option__value=value
            ).count()
            
            if matching_count == variant_count:
                # All variants match - strong match
                score += 2
            elif matching_count > 0:
                # Some variants match - partial match
                score += 1
        
        return score

    @staticmethod
    def find_best_matching_variant(
        product: Product,
        attribute_selections: Dict[str, str]
    ) -> Optional[Variant]:
        """
        Find the single variant that best matches the given selections.
        Fallback when no group matches or for direct variant access.
        
        Args:
            product: The product to search within
            attribute_selections: Dict of {attribute_slug: option_value}
        
        Returns:
            Best matching Variant or None
        """
        queryset = Variant.objects.filter(product=product, is_active=True)
        
        if not attribute_selections:
            return queryset.first()
        
        # Try exact match first - all attributes must match
        exact_match = queryset
        for attr_slug, value in attribute_selections.items():
            exact_match = exact_match.filter(
                variantattribute__attribute_option__attribute_type__slug=attr_slug,
                variantattribute__attribute_option__value=value
            )
        
        if exact_match.exists():
            return exact_match.first()
        
        # No exact match - find best partial match
        # Score each variant by how many attributes match
        best_variant = None
        best_score = 0
        
        for variant in queryset.prefetch_related(
            'variantattribute_set__attribute_option__attribute_type'
        ):
            variant_attrs = {
                va.attribute_option.attribute_type.slug: va.attribute_option.value
                for va in variant.variantattribute_set.all()
            }
            
            score = sum(
                1 for attr_slug, value in attribute_selections.items()
                if variant_attrs.get(attr_slug) == value
            )
            
            if score > best_score:
                best_score = score
                best_variant = variant
        
        return best_variant or queryset.first()

    @staticmethod
    def find_best_match(
        product: Product,
        selections: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Find the best matching group OR variant based on selections.
        
        Returns dict with:
        - type: 'group' or 'variant'
        - data: serialized group or variant info
        - match_score: how well it matches
        - available_options: what options are available for further navigation
        """
        # First try to find a matching group
        group, group_score = VariantNavigationService.find_best_matching_group(
            product, selections
        )
        
        # Also find the best matching variant
        variant = VariantNavigationService.find_best_matching_variant(
            product, selections
        )
        
        # Get available options for navigation
        available_options = VariantNavigationService.get_all_available_options(
            product, selections
        )
        
        if group and group_score >= len(selections):
            # Good group match
            return {
                'type': 'group',
                'id': group.id,
                'name': group.name,
                'slug': group.slug,
                'product_slug': product.slug,
                'match_score': group_score,
                'variant_count': group.variant_count,
                'price_range': group.price_range,
                'available_options': available_options,
            }
        elif variant:
            # Return variant
            return {
                'type': 'variant',
                'id': variant.id,
                'sku': variant.sku,
                'name': variant.name,
                'product_slug': product.slug,
                'sell_price': str(variant.sell_price),
                'is_in_stock': variant.is_in_stock,
                'match_score': len(selections),
                'available_options': available_options,
            }
        
        return {
            'type': 'none',
            'message': 'No matching group or variant found',
            'available_options': available_options,
        }

    @staticmethod
    def get_navigation_data(variant_group: VariantGroup) -> Dict[str, Any]:
        """
        Build navigation data for a variant group page.
        Returns structure for attribute selectors.
        
        This data allows users to navigate to related groups/variants
        by selecting different attribute options.
        """
        product = variant_group.product
        group_variants = variant_group.variants.filter(is_active=True)
        
        # Get all attribute types used by this product
        attribute_types = AttributeType.objects.filter(
            options__variants__product=product
        ).distinct().order_by('display_order')
        
        # Determine what attributes are "fixed" for this group
        # (common to ALL variants in the group)
        common_options = variant_group.get_common_attribute_options()
        common_attrs = {
            opt.attribute_type.slug: opt.value
            for opt in common_options
        }
        
        navigation = []
        
        for attr_type in attribute_types:
            # All options available for this product
            all_options = AttributeOption.objects.filter(
                attribute_type=attr_type,
                variants__product=product,
                variants__is_active=True
            ).distinct().order_by('display_order', 'value')
            
            # Options present in current group
            group_options_qs = AttributeOption.objects.filter(
                attribute_type=attr_type,
                variants__in=group_variants
            ).distinct()
            group_option_values = set(group_options_qs.values_list('value', flat=True))
            
            # Check if this attribute is "fixed" for the group
            is_fixed = attr_type.slug in common_attrs
            fixed_value = common_attrs.get(attr_type.slug)
            
            options_data = []
            for opt in all_options:
                options_data.append({
                    'id': opt.id,
                    'value': opt.value,
                    'display_value': opt.get_display_value(),
                    'color_hex': opt.color_hex,
                    'is_current': opt.value in group_option_values,
                    'is_fixed': is_fixed and opt.value == fixed_value,
                })
            
            navigation.append({
                'attribute_type': {
                    'id': attr_type.id,
                    'name': attr_type.name,
                    'slug': attr_type.slug,
                },
                'is_fixed': is_fixed,
                'fixed_value': fixed_value,
                'options': options_data,
            })
        
        # Also return related groups for easy navigation
        related_groups = product.variant_groups.filter(
            is_active=True
        ).exclude(pk=variant_group.pk).order_by('display_order')[:10]
        
        return {
            'current_group': {
                'id': variant_group.id,
                'name': variant_group.name,
                'slug': variant_group.slug,
            },
            'product': {
                'id': product.id,
                'name': product.name,
                'slug': product.slug,
            },
            'common_attributes': common_attrs,
            'attribute_navigation': navigation,
            'related_groups': [
                {
                    'id': g.id,
                    'name': g.name,
                    'slug': g.slug,
                    'variant_count': g.variant_count,
                }
                for g in related_groups
            ],
        }
