import json
from decimal import Decimal
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
from django.utils.text import slugify

from .models import (
    Product,
    Category,
    Variant,
    VariantGroup,
    VariantGroupMembership,
    AttributeType,
    AttributeOption,
    VariantAttribute,
    VariantImage,
)


@staff_member_required
def bulk_edit_view(request):
    """Render the bulk edit page with Handsontable."""
    products = Product.objects.filter(is_active=True).order_by('name')
    variant_groups = VariantGroup.objects.filter(is_active=True).select_related('product').order_by('product__name', 'name')
    attribute_types = AttributeType.objects.all().order_by('display_order', 'name')
    
    context = {
        'products': products,
        'variant_groups': variant_groups,
        'attribute_types': attribute_types,
        'title': 'Gerenciamento de Produtos e Variantes',
    }
    return render(request, 'catalog/bulk_edit.html', context)


# =============================================================================
# PRODUCTS
# =============================================================================

@staff_member_required
@require_http_methods(["GET"])
def bulk_products_data(request):
    """API endpoint to get products data."""
    from django.db.models import Min, Max, Avg, Sum
    
    products = Product.objects.prefetch_related(
        'variants__images',
        'variants__variantattribute_set__attribute_option__attribute_type',
        'variant_groups__variants',
        'categories',
    ).all().order_by('name')
    
    data = []
    for product in products:
        # Get attribute types count for this product
        attr_types_count = product.get_attribute_types().count()
        variant_count = product.variant_count
        
        # Build categories JSON data
        categories_json = []
        for cat in product.categories.select_related('parent').all():
            categories_json.append({
                'nome': cat.name,
                'slug': cat.slug,
                'full_path': cat.full_path,
                'pai': cat.parent.slug if cat.parent else None,
            })
        
        row = {
            'id': product.id,
            'name': product.name,
            'slug': product.slug,
            'description': product.description,
            'is_active': product.is_active,
            'variant_count': variant_count,
            'group_count': product.variant_groups.count(),
            'attr_types_count': attr_types_count,
            'thumbnail_url': product.get_thumbnail_url(),
            'created_at': product.created_at.strftime('%Y-%m-%d %H:%M') if product.created_at else '',
            # Variant fields (for products without variants or with single variant)
            'has_variants': variant_count > 1,
            'variant_id': None,
            'sku': '',
            'cost_price': None,
            'sell_price': None,
            'compare_at_price': None,
            'stock_quantity': 0,
            # Stats fields (for products with multiple variants)
            'price_stats': None,
            'stock_stats': None,
            # JSON data columns
            'attributes_json': None,
            'variants_json': None,
            'groups_json': None,
            'categories_json': categories_json if categories_json else None,
        }
        
        # Build attributes JSON - aggregate all attribute types and their values
        attributes_dict = {}
        for variant in product.variants.all():
            for va in variant.variantattribute_set.all():
                attr_name = va.attribute_option.attribute_type.name
                attr_value = va.attribute_option.value
                if attr_name not in attributes_dict:
                    attributes_dict[attr_name] = set()
                attributes_dict[attr_name].add(attr_value)
        
        if attributes_dict:
            row['attributes_json'] = [
                {'atributo': name, 'valores': sorted(list(values))}
                for name, values in sorted(attributes_dict.items())
            ]
        
        # Build variants JSON
        variants_list = []
        for variant in product.variants.all():
            v_data = {
                'sku': variant.sku,
                'nome': variant.name or variant.sku,
                'preco_custo': float(variant.cost_price) if variant.cost_price else None,
                'preco_venda': float(variant.sell_price) if variant.sell_price else None,
                'estoque': variant.stock_quantity,
            }
            # Add attributes
            for va in variant.variantattribute_set.all():
                v_data[va.attribute_option.attribute_type.slug] = va.attribute_option.value
            variants_list.append(v_data)
        
        if variants_list:
            row['variants_json'] = variants_list
        
        # Build groups JSON
        groups_list = []
        for group in product.variant_groups.all():
            g_data = {
                'nome': group.name,
                'slug': group.slug,
                'descricao': group.description or '',
                'variantes': [v.sku for v in group.variants.all()],
            }
            groups_list.append(g_data)
        
        if groups_list:
            row['groups_json'] = groups_list
        
        # If product has 0 or 1 variant, include variant data inline
        if variant_count <= 1:
            variant = product.variants.first()
            if variant:
                row['variant_id'] = variant.id
                row['sku'] = variant.sku
                row['cost_price'] = float(variant.cost_price) if variant.cost_price else None
                row['sell_price'] = float(variant.sell_price) if variant.sell_price else None
                row['compare_at_price'] = float(variant.compare_at_price) if variant.compare_at_price else None
                row['stock_quantity'] = variant.stock_quantity
        else:
            # Calculate statistics for products with multiple variants
            stats = product.variants.aggregate(
                sell_price_min=Min('sell_price'),
                sell_price_max=Max('sell_price'),
                sell_price_avg=Avg('sell_price'),
                cost_price_min=Min('cost_price'),
                cost_price_max=Max('cost_price'),
                cost_price_avg=Avg('cost_price'),
                stock_min=Min('stock_quantity'),
                stock_max=Max('stock_quantity'),
                stock_avg=Avg('stock_quantity'),
                stock_total=Sum('stock_quantity'),
            )
            
            row['price_stats'] = {
                'sell_min': float(stats['sell_price_min']) if stats['sell_price_min'] else None,
                'sell_max': float(stats['sell_price_max']) if stats['sell_price_max'] else None,
                'sell_avg': round(float(stats['sell_price_avg']), 2) if stats['sell_price_avg'] else None,
                'cost_min': float(stats['cost_price_min']) if stats['cost_price_min'] else None,
                'cost_max': float(stats['cost_price_max']) if stats['cost_price_max'] else None,
                'cost_avg': round(float(stats['cost_price_avg']), 2) if stats['cost_price_avg'] else None,
            }
            
            row['stock_stats'] = {
                'min': stats['stock_min'] or 0,
                'max': stats['stock_max'] or 0,
                'avg': round(float(stats['stock_avg']), 1) if stats['stock_avg'] else 0,
                'total': stats['stock_total'] or 0,
            }
        
        data.append(row)
    
    return JsonResponse({'data': data})


def _process_categories_json(product, categories_json):
    """
    Process categories JSON data for a product.
    Creates new categories if needed, then assigns them to the product.
    
    Expected format:
    [
        {"nome": "Category Name", "slug": "category-slug", "pai": "parent-slug"},
        {"nome": "Another Category", "slug": "another-category", "pai": null}
    ]
    """
    if not categories_json:
        # Clear all categories if empty list
        product.categories.clear()
        return
    
    category_ids = []
    
    for cat_data in categories_json:
        nome = cat_data.get('nome', '').strip()
        if not nome:
            continue
        
        cat_slug = cat_data.get('slug', '').strip() or slugify(nome)
        parent_slug = cat_data.get('pai')
        
        # Get parent category if specified
        parent = None
        if parent_slug:
            parent = Category.objects.filter(slug=parent_slug).first()
        
        # Get or create the category
        category, created = Category.objects.get_or_create(
            slug=cat_slug,
            defaults={
                'name': nome,
                'parent': parent,
                'is_active': True,
            }
        )
        
        if created:
            print(f"  - Created new category: {category.full_path}")
        
        category_ids.append(category.id)
    
    # Update product's categories
    product.categories.set(category_ids)
    print(f"  - Assigned {len(category_ids)} categories to product")


def _json_changed(old_json, new_json):
    """Compare two JSON values to detect changes."""
    import json
    # Normalize to JSON strings for comparison
    old_str = json.dumps(old_json, sort_keys=True) if old_json else None
    new_str = json.dumps(new_json, sort_keys=True) if new_json else None
    return old_str != new_str


def _process_product_json_data(product, item):
    """
    Process JSON data for attributes, variants, groups, and categories.
    Creates/updates related entities based on the JSON data.
    Only processes if there are changes compared to stored metadata.
    """
    attributes_json = item.get('attributes_json')
    variants_json = item.get('variants_json')
    groups_json = item.get('groups_json')
    categories_json = item.get('categories_json')
    
    print(f"[JSON PROCESS] Product {product.id} ({product.name})")
    print(f"  - attributes_json: {attributes_json}")
    print(f"  - variants_json: {variants_json}")
    print(f"  - groups_json: {groups_json}")
    print(f"  - categories_json: {categories_json}")
    
    # Check what changed
    categories_changed = _json_changed(product.metadata_categories, categories_json)
    attributes_changed = _json_changed(product.metadata_attributes, attributes_json)
    variants_changed = _json_changed(product.metadata_variants, variants_json)
    groups_changed = _json_changed(product.metadata_groups, groups_json)
    
    print(f"  - Changes: categories={categories_changed}, attributes={attributes_changed}, variants={variants_changed}, groups={groups_changed}")
    
    # Skip if nothing changed
    if not any([categories_changed, attributes_changed, variants_changed, groups_changed]):
        print("  - No changes detected, skipping")
        return
    
    print("  - Processing changed JSON data...")
    
    # Process categories - create if needed, then assign to product
    if categories_changed and categories_json is not None:
        _process_categories_json(product, categories_json)
        product.metadata_categories = categories_json
    
    # Process attributes - create AttributeTypes and AttributeOptions
    attr_type_map = {}  # {attr_name: {value: AttributeOption}}
    
    if attributes_changed and attributes_json:
        for attr_data in attributes_json:
            attr_name = attr_data.get('atributo', '').strip()
            valores = attr_data.get('valores', [])
            
            if not attr_name or not valores:
                continue
            
            # Get or create AttributeType
            attr_slug = slugify(attr_name)
            attr_type, _ = AttributeType.objects.get_or_create(
                slug=attr_slug,
                defaults={'name': attr_name, 'datatype': 'text'}
            )
            
            attr_type_map[attr_name.lower()] = {}
            
            # Get or create AttributeOptions
            for valor in valores:
                valor = str(valor).strip()
                if valor:
                    option, _ = AttributeOption.objects.get_or_create(
                        attribute_type=attr_type,
                        value=valor,
                        defaults={'display_value': valor}
                    )
                    attr_type_map[attr_name.lower()][valor.lower()] = option
        
        product.metadata_attributes = attributes_json
    
    # Process variants - create/update Variants with their attributes
    if variants_changed and variants_json:
        existing_skus = set(product.variants.values_list('sku', flat=True))
        new_skus = set()
        
        for var_data in variants_json:
            sku = var_data.get('sku', '').strip()
            if not sku:
                continue
            
            new_skus.add(sku)
            
            # Get or create variant
            variant, created = Variant.objects.get_or_create(
                product=product,
                sku=sku,
                defaults={
                    'name': var_data.get('nome', sku),
                    'cost_price': Decimal(str(var_data['preco_custo'])) if var_data.get('preco_custo') else None,
                    'sell_price': Decimal(str(var_data['preco_venda'])) if var_data.get('preco_venda') else Decimal('0'),
                    'stock_quantity': var_data.get('estoque', 0),
                    'is_active': True,
                }
            )
            
            if not created:
                # Update existing variant
                variant.name = var_data.get('nome', variant.name)
                if var_data.get('preco_custo') is not None:
                    variant.cost_price = Decimal(str(var_data['preco_custo']))
                if var_data.get('preco_venda') is not None:
                    variant.sell_price = Decimal(str(var_data['preco_venda']))
                if var_data.get('estoque') is not None:
                    variant.stock_quantity = var_data['estoque']
                variant.save()
            
            # Process variant attributes
            # Clear existing attributes for this variant
            VariantAttribute.objects.filter(variant=variant).delete()
            
            # Add new attributes from JSON
            for attr_name, options_map in attr_type_map.items():
                # Look for attribute value in variant data using slugified key
                attr_slug = attr_name.replace(' ', '_')
                attr_value = var_data.get(attr_slug, '')
                
                if attr_value:
                    option = options_map.get(str(attr_value).lower())
                    if option:
                        VariantAttribute.objects.create(
                            variant=variant,
                            attribute_option=option
                        )
        
        # Delete variants that are no longer in the JSON
        # Only if variants_json was provided and has data
        if new_skus:
            skus_to_delete = existing_skus - new_skus
            if skus_to_delete:
                Variant.objects.filter(product=product, sku__in=skus_to_delete).delete()
        
        product.metadata_variants = variants_json
    
    # Process groups - create/update VariantGroups
    if groups_changed and groups_json:
        existing_group_slugs = set(product.variant_groups.values_list('slug', flat=True))
        new_group_slugs = set()
        
        for grp_data in groups_json:
            nome = grp_data.get('nome', '').strip()
            if not nome:
                continue
            
            grp_slug = grp_data.get('slug', '').strip() or slugify(nome)
            new_group_slugs.add(grp_slug)
            
            # Get or create group
            group, created = VariantGroup.objects.get_or_create(
                product=product,
                slug=grp_slug,
                defaults={
                    'name': nome,
                    'description': grp_data.get('descricao', ''),
                    'is_active': True,
                }
            )
            
            if not created:
                group.name = nome
                group.description = grp_data.get('descricao', '')
                group.save()
            
            # Update group members
            variant_skus = grp_data.get('variantes', [])
            if variant_skus:
                # Clear existing members
                VariantGroupMembership.objects.filter(variant_group=group).delete()
                
                # Add new members
                for sku in variant_skus:
                    sku = sku.strip()
                    try:
                        variant = Variant.objects.get(product=product, sku=sku)
                        VariantGroupMembership.objects.create(
                            variant_group=group,
                            variant=variant
                        )
                    except Variant.DoesNotExist:
                        pass
        
        # Delete groups that are no longer in the JSON
        if new_group_slugs:
            slugs_to_delete = existing_group_slugs - new_group_slugs
            if slugs_to_delete:
                VariantGroup.objects.filter(product=product, slug__in=slugs_to_delete).delete()
        
        product.metadata_groups = groups_json
    
    # Save product metadata if any changes were made
    if any([categories_changed, attributes_changed, variants_changed, groups_changed]):
        product.save(update_fields=[
            'metadata_categories', 'metadata_attributes', 
            'metadata_variants', 'metadata_groups'
        ])
        print(f"  - Saved metadata for product {product.id}")


@staff_member_required
@require_http_methods(["POST"])
@csrf_protect
def bulk_products_save(request):
    """API endpoint to create/update products."""
    try:
        payload = json.loads(request.body)
        print(f"[BULK SAVE] Received payload: create={len(payload.get('create', []))}, update={len(payload.get('update', []))}")
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    
    to_create = payload.get('create', [])
    to_update = payload.get('update', [])
    
    created_count = 0
    updated_count = 0
    errors = []
    
    with transaction.atomic():
        # Create new products
        for item in to_create:
            try:
                slug = item.get('slug') or slugify(item['name'])
                # Ensure unique slug
                base_slug = slug
                counter = 1
                while Product.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                
                Product.objects.create(
                    name=item['name'],
                    slug=slug,
                    description=item.get('description', ''),
                    is_active=item.get('is_active', True)
                )
                
                product = Product.objects.get(slug=slug)
                
                # Process JSON data if provided
                _process_product_json_data(product, item)
                
                # If SKU is provided for new product (and no variants_json), create inline variant
                sku = item.get('sku', '').strip()
                if sku and not item.get('variants_json') and not Variant.objects.filter(sku=sku).exists():
                    Variant.objects.create(
                        product=product,
                        sku=sku,
                        name=item['name'],
                        cost_price=Decimal(str(item['cost_price'])) if item.get('cost_price') else None,
                        sell_price=Decimal(str(item['sell_price'])) if item.get('sell_price') else Decimal('0'),
                        compare_at_price=Decimal(str(item['compare_at_price'])) if item.get('compare_at_price') else None,
                        stock_quantity=item.get('stock_quantity', 0),
                        is_active=True
                    )
                
                created_count += 1
            except Exception as e:
                errors.append(f"Erro ao criar '{item.get('name', '?')}': {str(e)}")
        
        # Update existing products
        for item in to_update:
            try:
                product = Product.objects.get(pk=item['id'])
                product.name = item['name']
                if item.get('slug'):
                    product.slug = item['slug']
                product.description = item.get('description', '')
                product.is_active = item.get('is_active', True)
                product.save()
                
                # Process JSON data if provided
                _process_product_json_data(product, item)
                
                # Handle inline variant data for products without multiple variants
                # Skip if variants_json was provided (those take precedence)
                if not item.get('has_variants', False) and not item.get('variants_json'):
                    variant_id = item.get('variant_id')
                    sku = item.get('sku', '').strip()
                    
                    if sku:
                        if variant_id:
                            # Update existing variant
                            try:
                                variant = Variant.objects.get(pk=variant_id, product=product)
                                variant.sku = sku
                                variant.cost_price = Decimal(str(item['cost_price'])) if item.get('cost_price') else None
                                variant.sell_price = Decimal(str(item['sell_price'])) if item.get('sell_price') else Decimal('0')
                                variant.compare_at_price = Decimal(str(item['compare_at_price'])) if item.get('compare_at_price') else None
                                variant.stock_quantity = item.get('stock_quantity', 0)
                                variant.save()
                            except Variant.DoesNotExist:
                                pass
                        else:
                            # Create new variant for this product
                            if not Variant.objects.filter(sku=sku).exists():
                                Variant.objects.create(
                                    product=product,
                                    sku=sku,
                                    name=product.name,
                                    cost_price=Decimal(str(item['cost_price'])) if item.get('cost_price') else None,
                                    sell_price=Decimal(str(item['sell_price'])) if item.get('sell_price') else Decimal('0'),
                                    compare_at_price=Decimal(str(item['compare_at_price'])) if item.get('compare_at_price') else None,
                                    stock_quantity=item.get('stock_quantity', 0),
                                    is_active=True
                                )
                
                updated_count += 1
            except Product.DoesNotExist:
                errors.append(f"Produto ID {item.get('id')} não encontrado")
            except Exception as e:
                import traceback
                errors.append(f"Erro ao atualizar ID {item.get('id')}: {str(e)} - {traceback.format_exc()}")
    
    return JsonResponse({
        'status': 'ok',
        'created': created_count,
        'updated': updated_count,
        'errors': errors,
    })


# =============================================================================
# VARIANTS
# =============================================================================

@staff_member_required
@require_http_methods(["GET"])
def bulk_variants_data(request):
    """API endpoint to get variants data for a product."""
    product_id = request.GET.get('product_id')
    
    if not product_id:
        return JsonResponse({'data': [], 'attribute_columns': []})
    
    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'data': [], 'attribute_columns': []})
    
    # Get attribute types for this product
    attr_types = list(AttributeType.objects.filter(
        options__variants__product=product
    ).distinct().order_by('display_order'))
    
    # If no variants yet, get all attribute types
    if not attr_types:
        attr_types = list(AttributeType.objects.all().order_by('display_order'))
    
    # Build attribute columns config
    attribute_columns = []
    for attr_type in attr_types:
        options = list(attr_type.options.values_list('value', flat=True).order_by('display_order'))
        attribute_columns.append({
            'id': attr_type.id,
            'name': attr_type.name,
            'slug': attr_type.slug,
            'options': options,
        })
    
    # Get variants
    variants = Variant.objects.filter(product=product).prefetch_related(
        'variantattribute_set__attribute_option__attribute_type',
        'images'
    ).order_by('sku')
    
    data = []
    for variant in variants:
        # Get thumbnail URL from primary image
        thumbnail_url = None
        primary_image = variant.primary_image
        if primary_image:
            try:
                thumbnail_url = primary_image.thumbnail_small.url
            except Exception:
                thumbnail_url = primary_image.image.url
        
        row = {
            'id': variant.id,
            'sku': variant.sku,
            'name': variant.name,
            'thumbnail_url': thumbnail_url,
            'image_count': variant.images.count(),
            'cost_price': float(variant.cost_price) if variant.cost_price else None,
            'sell_price': float(variant.sell_price) if variant.sell_price else None,
            'compare_at_price': float(variant.compare_at_price) if variant.compare_at_price else None,
            'stock_quantity': variant.stock_quantity,
            'is_active': variant.is_active,
        }
        
        # Add attribute values
        for va in variant.variantattribute_set.all():
            row[f'attr_{va.attribute_option.attribute_type.slug}'] = va.attribute_option.value
        
        data.append(row)
    
    return JsonResponse({
        'data': data,
        'attribute_columns': attribute_columns,
    })


@staff_member_required
@require_http_methods(["POST"])
@csrf_protect
def bulk_variants_save(request):
    """API endpoint to create/update variants."""
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    
    to_create = payload.get('create', [])
    to_update = payload.get('update', [])
    
    created_count = 0
    updated_count = 0
    errors = []
    
    with transaction.atomic():
        # Create new variants
        for item in to_create:
            try:
                product = Product.objects.get(pk=item['product_id'])
                
                # Check if SKU already exists
                if Variant.objects.filter(sku=item['sku']).exists():
                    errors.append(f"SKU '{item['sku']}' já existe")
                    continue
                
                variant = Variant.objects.create(
                    product=product,
                    sku=item['sku'],
                    name=item.get('name', ''),
                    cost_price=Decimal(str(item['cost_price'])) if item.get('cost_price') else None,
                    sell_price=Decimal(str(item['sell_price'])) if item.get('sell_price') else Decimal('0'),
                    compare_at_price=Decimal(str(item['compare_at_price'])) if item.get('compare_at_price') else None,
                    stock_quantity=item.get('stock_quantity', 0),
                    is_active=item.get('is_active', True)
                )
                
                # Set attributes
                attributes = item.get('attributes', {})
                for attr_slug, value in attributes.items():
                    try:
                        attr_option = AttributeOption.objects.get(
                            attribute_type__slug=attr_slug,
                            value=value
                        )
                        VariantAttribute.objects.create(
                            variant=variant,
                            attribute_option=attr_option
                        )
                    except AttributeOption.DoesNotExist:
                        pass  # Skip if option doesn't exist
                
                created_count += 1
            except Exception as e:
                errors.append(f"Erro ao criar SKU '{item.get('sku', '?')}': {str(e)}")
        
        # Update existing variants
        for item in to_update:
            try:
                variant = Variant.objects.get(pk=item['id'])
                
                # Check if SKU changed and already exists
                if item['sku'] != variant.sku and Variant.objects.filter(sku=item['sku']).exists():
                    errors.append(f"SKU '{item['sku']}' já existe")
                    continue
                
                variant.sku = item['sku']
                variant.name = item.get('name', '')
                variant.cost_price = Decimal(str(item['cost_price'])) if item.get('cost_price') else None
                variant.sell_price = Decimal(str(item['sell_price'])) if item.get('sell_price') else variant.sell_price
                variant.compare_at_price = Decimal(str(item['compare_at_price'])) if item.get('compare_at_price') else None
                variant.stock_quantity = item.get('stock_quantity', 0)
                variant.is_active = item.get('is_active', True)
                variant.save()
                
                # Update attributes
                attributes = item.get('attributes', {})
                for attr_slug, value in attributes.items():
                    try:
                        attr_option = AttributeOption.objects.get(
                            attribute_type__slug=attr_slug,
                            value=value
                        )
                        # Remove existing attribute of this type
                        VariantAttribute.objects.filter(
                            variant=variant,
                            attribute_option__attribute_type__slug=attr_slug
                        ).delete()
                        # Add new
                        VariantAttribute.objects.create(
                            variant=variant,
                            attribute_option=attr_option
                        )
                    except AttributeOption.DoesNotExist:
                        pass
                
                updated_count += 1
            except Variant.DoesNotExist:
                errors.append(f"Variante ID {item.get('id')} não encontrada")
            except Exception as e:
                errors.append(f"Erro ao atualizar SKU '{item.get('sku', '?')}': {str(e)}")
    
    return JsonResponse({
        'status': 'ok',
        'created': created_count,
        'updated': updated_count,
        'errors': errors,
    })


# =============================================================================
# ATTRIBUTE OPTIONS
# =============================================================================

@staff_member_required
@require_http_methods(["GET"])
def bulk_attr_options_data(request):
    """API endpoint to get attribute options."""
    attr_type_id = request.GET.get('attribute_type_id')
    
    if not attr_type_id:
        return JsonResponse({'data': []})
    
    options = AttributeOption.objects.filter(
        attribute_type_id=attr_type_id
    ).order_by('display_order', 'value')
    
    data = []
    for opt in options:
        data.append({
            'id': opt.id,
            'value': opt.value,
            'display_value': opt.display_value,
            'color_hex': opt.color_hex,
            'display_order': opt.display_order,
        })
    
    return JsonResponse({'data': data})


@staff_member_required
@require_http_methods(["POST"])
@csrf_protect
def bulk_attr_options_save(request):
    """API endpoint to create/update attribute options."""
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    
    to_create = payload.get('create', [])
    to_update = payload.get('update', [])
    
    created_count = 0
    updated_count = 0
    errors = []
    
    with transaction.atomic():
        # Create new options
        for item in to_create:
            try:
                attr_type = AttributeType.objects.get(pk=item['attribute_type_id'])
                
                # Check if already exists
                if AttributeOption.objects.filter(
                    attribute_type=attr_type,
                    value=item['value']
                ).exists():
                    errors.append(f"Opção '{item['value']}' já existe")
                    continue
                
                AttributeOption.objects.create(
                    attribute_type=attr_type,
                    value=item['value'],
                    display_value=item.get('display_value', ''),
                    color_hex=item.get('color_hex', ''),
                    display_order=item.get('display_order', 0)
                )
                created_count += 1
            except Exception as e:
                errors.append(f"Erro ao criar '{item.get('value', '?')}': {str(e)}")
        
        # Update existing options
        for item in to_update:
            try:
                opt = AttributeOption.objects.get(pk=item['id'])
                opt.value = item['value']
                opt.display_value = item.get('display_value', '')
                opt.color_hex = item.get('color_hex', '')
                opt.display_order = item.get('display_order', 0)
                opt.save()
                updated_count += 1
            except AttributeOption.DoesNotExist:
                errors.append(f"Opção ID {item.get('id')} não encontrada")
            except Exception as e:
                errors.append(f"Erro ao atualizar ID {item.get('id')}: {str(e)}")
    
    return JsonResponse({
        'status': 'ok',
        'created': created_count,
        'updated': updated_count,
        'errors': errors,
    })


@staff_member_required
@require_http_methods(["POST"])
@csrf_protect
def bulk_create_attr_type(request):
    """API endpoint to create a new attribute type."""
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    
    name = payload.get('name')
    slug = payload.get('slug')
    datatype = payload.get('datatype', 'text')
    
    if not name or not slug:
        return JsonResponse({'status': 'error', 'message': 'Nome e slug são obrigatórios'}, status=400)
    
    if AttributeType.objects.filter(slug=slug).exists():
        return JsonResponse({'status': 'error', 'message': f"Slug '{slug}' já existe"}, status=400)
    
    try:
        attr_type = AttributeType.objects.create(
            name=name,
            slug=slug,
            datatype=datatype
        )
        return JsonResponse({
            'status': 'ok',
            'id': attr_type.id,
            'name': attr_type.name,
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# =============================================================================
# GROUPS
# =============================================================================

@staff_member_required
@require_http_methods(["GET"])
def bulk_groups_data(request):
    """API endpoint to get groups data for a product."""
    product_id = request.GET.get('product_id')
    
    if not product_id:
        return JsonResponse({'data': []})
    
    groups = VariantGroup.objects.filter(product_id=product_id).order_by('name')
    
    data = []
    for group in groups:
        data.append({
            'id': group.id,
            'name': group.name,
            'slug': group.slug,
            'description': group.description,
            'is_active': group.is_active,
            'variant_count': group.variants.count(),
        })
    
    return JsonResponse({'data': data})


@staff_member_required
@require_http_methods(["POST"])
@csrf_protect
def bulk_groups_save(request):
    """API endpoint to create/update groups."""
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    
    to_create = payload.get('create', [])
    to_update = payload.get('update', [])
    
    created_count = 0
    updated_count = 0
    errors = []
    
    with transaction.atomic():
        # Create new groups
        for item in to_create:
            try:
                product = Product.objects.get(pk=item['product_id'])
                slug = item.get('slug') or slugify(item['name'])
                
                # Ensure unique slug for this product
                base_slug = slug
                counter = 1
                while VariantGroup.objects.filter(product=product, slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                
                VariantGroup.objects.create(
                    product=product,
                    name=item['name'],
                    slug=slug,
                    description=item.get('description', ''),
                    is_active=item.get('is_active', True)
                )
                created_count += 1
            except Exception as e:
                errors.append(f"Erro ao criar '{item.get('name', '?')}': {str(e)}")
        
        # Update existing groups
        for item in to_update:
            try:
                group = VariantGroup.objects.get(pk=item['id'])
                group.name = item['name']
                if item.get('slug'):
                    group.slug = item['slug']
                group.description = item.get('description', '')
                group.is_active = item.get('is_active', True)
                group.save()
                updated_count += 1
            except VariantGroup.DoesNotExist:
                errors.append(f"Grupo ID {item.get('id')} não encontrado")
            except Exception as e:
                errors.append(f"Erro ao atualizar ID {item.get('id')}: {str(e)}")
    
    return JsonResponse({
        'status': 'ok',
        'created': created_count,
        'updated': updated_count,
        'errors': errors,
    })


@staff_member_required
@require_http_methods(["POST"])
@csrf_protect
def bulk_add_to_group(request):
    """Add selected variants to a group."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    
    group_id = data.get('group_id')
    variant_ids = data.get('variant_ids', [])
    
    if not group_id or not variant_ids:
        return JsonResponse({
            'status': 'error',
            'message': 'group_id e variant_ids são obrigatórios'
        }, status=400)
    
    try:
        group = VariantGroup.objects.get(pk=group_id)
    except VariantGroup.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Grupo não encontrado'
        }, status=404)
    
    added = 0
    for variant_id in variant_ids:
        try:
            variant = Variant.objects.get(pk=variant_id)
            # Only add if variant belongs to the same product as the group
            if variant.product_id == group.product_id:
                _, created = VariantGroupMembership.objects.get_or_create(
                    variant_group=group,
                    variant=variant
                )
                if created:
                    added += 1
        except Variant.DoesNotExist:
            pass
    
    return JsonResponse({
        'status': 'ok',
        'added': added,
    })


@staff_member_required
@require_http_methods(["POST"])
@csrf_protect
def bulk_create_group_with_variants(request):
    """Create a new group and add variants to it."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    
    product_id = data.get('product_id')
    name = data.get('name')
    slug = data.get('slug')
    description = data.get('description', '')
    variant_ids = data.get('variant_ids', [])
    
    if not product_id or not name:
        return JsonResponse({
            'status': 'error',
            'message': 'product_id e name são obrigatórios'
        }, status=400)
    
    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Produto não encontrado'
        }, status=404)
    
    # Generate slug if not provided
    if not slug:
        slug = slugify(name)
    
    # Ensure unique slug for this product
    base_slug = slug
    counter = 1
    while VariantGroup.objects.filter(product=product, slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    with transaction.atomic():
        # Create the group
        group = VariantGroup.objects.create(
            product=product,
            name=name,
            slug=slug,
            description=description,
            is_active=True
        )
        
        # Add variants
        added = 0
        first_variant_with_image = None
        
        for variant_id in variant_ids:
            try:
                variant = Variant.objects.get(pk=variant_id)
                if variant.product_id == product.id:
                    VariantGroupMembership.objects.create(
                        variant_group=group,
                        variant=variant
                    )
                    added += 1
                    
                    # Track first variant with image for featured_image
                    if first_variant_with_image is None:
                        primary_img = variant.primary_image
                        if primary_img:
                            first_variant_with_image = primary_img
            except Variant.DoesNotExist:
                pass
        
        # Set featured image from first variant
        if first_variant_with_image:
            group.featured_image = first_variant_with_image
            group.save()
    
    return JsonResponse({
        'status': 'ok',
        'group_id': group.id,
        'group_name': group.name,
        'variants_added': added,
    })


# =============================================================================
# IMAGE UPLOAD
# =============================================================================

@staff_member_required
@require_http_methods(["GET"])
def variant_images_list(request, variant_id):
    """Get list of images for a variant."""
    try:
        variant = Variant.objects.get(pk=variant_id)
    except Variant.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Variante não encontrada'}, status=404)
    
    images = []
    for img in variant.images.all():
        try:
            thumbnail_url = img.thumbnail_small.url
        except Exception:
            thumbnail_url = img.image.url
        
        images.append({
            'id': img.id,
            'thumbnail_url': thumbnail_url,
            'full_url': img.image.url,
            'alt_text': img.alt_text,
            'is_primary': img.is_primary,
            'display_order': img.display_order,
        })
    
    return JsonResponse({
        'status': 'ok',
        'variant_id': variant.id,
        'variant_sku': variant.sku,
        'images': images,
    })


@staff_member_required
@require_http_methods(["POST"])
def variant_image_upload(request, variant_id):
    """Upload image(s) for a variant."""
    try:
        variant = Variant.objects.get(pk=variant_id)
    except Variant.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Variante não encontrada'}, status=404)
    
    files = request.FILES.getlist('images')
    if not files:
        return JsonResponse({'status': 'error', 'message': 'Nenhuma imagem enviada'}, status=400)
    
    uploaded = []
    for i, file in enumerate(files):
        # Check if it's an image
        if not file.content_type.startswith('image/'):
            continue
        
        # Create the image
        is_primary = not variant.images.exists() and i == 0
        img = VariantImage.objects.create(
            variant=variant,
            image=file,
            is_primary=is_primary,
            display_order=variant.images.count()
        )
        
        try:
            thumbnail_url = img.thumbnail_small.url
        except Exception:
            thumbnail_url = img.image.url
        
        uploaded.append({
            'id': img.id,
            'thumbnail_url': thumbnail_url,
            'is_primary': img.is_primary,
        })
    
    return JsonResponse({
        'status': 'ok',
        'uploaded': len(uploaded),
        'images': uploaded,
    })


@staff_member_required
@require_http_methods(["POST"])
@csrf_protect
def variant_image_delete(request, image_id):
    """Delete a variant image."""
    try:
        img = VariantImage.objects.get(pk=image_id)
    except VariantImage.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Imagem não encontrada'}, status=404)
    
    variant_id = img.variant_id
    was_primary = img.is_primary
    img.delete()
    
    # If was primary, set another image as primary
    if was_primary:
        next_img = VariantImage.objects.filter(variant_id=variant_id).first()
        if next_img:
            next_img.is_primary = True
            next_img.save()
    
    return JsonResponse({'status': 'ok'})


@staff_member_required
@require_http_methods(["POST"])
@csrf_protect
def variant_image_set_primary(request, image_id):
    """Set an image as primary."""
    try:
        img = VariantImage.objects.get(pk=image_id)
    except VariantImage.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Imagem não encontrada'}, status=404)
    
    img.is_primary = True
    img.save()  # save() method handles unsetting other primaries
    
    return JsonResponse({'status': 'ok'})


# =============================================================================
# CATEGORIES
# =============================================================================

@staff_member_required
@require_http_methods(["GET"])
def categories_search(request):
    """
    Search/list categories with hierarchy info.
    Query params:
    - q: search query (optional)
    """
    query = request.GET.get('q', '').strip()
    
    categories = Category.objects.filter(is_active=True).select_related('parent')
    
    if query:
        # Search in name and full path
        categories = categories.filter(name__icontains=query)
    
    categories = categories.order_by('parent__name', 'display_order', 'name')[:100]
    
    data = []
    for cat in categories:
        data.append({
            'id': cat.id,
            'name': cat.name,
            'slug': cat.slug,
            'full_path': cat.full_path,
            'parent_id': cat.parent_id,
            'parent_name': cat.parent.name if cat.parent else None,
            'parent_slug': cat.parent.slug if cat.parent else None,
            'level': len(cat.get_ancestors()),
        })
    
    return JsonResponse({'categories': data})


@staff_member_required
@require_http_methods(["POST"])
@csrf_protect
def product_categories_update(request, product_id):
    """Update categories for a product."""
    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Produto não encontrado'}, status=404)
    
    try:
        body = json.loads(request.body)
        category_ids = body.get('category_ids', [])
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'status': 'error', 'message': 'Dados inválidos'}, status=400)
    
    # Validate category IDs
    valid_categories = Category.objects.filter(id__in=category_ids, is_active=True)
    
    # Update product categories
    product.categories.set(valid_categories)
    
    # Return updated categories
    categories_data = [
        {
            'id': cat.id,
            'name': cat.name,
            'full_path': cat.full_path,
        }
        for cat in product.categories.all()
    ]
    
    return JsonResponse({
        'status': 'ok',
        'categories': categories_data,
    })


@staff_member_required
@require_http_methods(["GET"])
def bulk_categories_data(request):
    """API endpoint to get categories data for the grid."""
    from django.db.models import Count
    
    categories = Category.objects.select_related('parent').annotate(
        product_count=Count('products')
    ).order_by('parent__name', 'display_order', 'name')
    
    data = []
    for cat in categories:
        data.append({
            'id': cat.id,
            'name': cat.name,
            'slug': cat.slug,
            'parent_id': cat.parent_id,
            'parent_name': cat.parent.name if cat.parent else None,
            'parent_slug': cat.parent.slug if cat.parent else None,
            'full_path': cat.full_path,
            'description': cat.description or '',
            'is_active': cat.is_active,
            'display_order': cat.display_order,
            'product_count': cat.product_count,
            'level': len(cat.get_ancestors()),
        })
    
    return JsonResponse({'data': data})


@staff_member_required
@require_http_methods(["POST"])
@csrf_protect
def bulk_categories_save(request):
    """API endpoint to create/update categories."""
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    
    to_create = payload.get('create', [])
    to_update = payload.get('update', [])
    
    created_count = 0
    updated_count = 0
    errors = []
    
    with transaction.atomic():
        # Create new categories
        for item in to_create:
            try:
                name = item.get('name', '').strip()
                if not name:
                    continue
                
                slug = item.get('slug', '').strip() or slugify(name)
                
                # Ensure unique slug
                base_slug = slug
                counter = 1
                while Category.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                
                # Get parent if specified
                parent = None
                parent_slug = item.get('parent_slug', '').strip()
                if parent_slug:
                    parent = Category.objects.filter(slug=parent_slug).first()
                
                Category.objects.create(
                    name=name,
                    slug=slug,
                    parent=parent,
                    description=item.get('description', ''),
                    is_active=item.get('is_active', True),
                    display_order=item.get('display_order', 0),
                )
                created_count += 1
            except Exception as e:
                errors.append(f"Erro ao criar '{item.get('name', '?')}': {str(e)}")
        
        # Update existing categories
        for item in to_update:
            try:
                cat = Category.objects.get(pk=item['id'])
                cat.name = item.get('name', cat.name)
                if item.get('slug'):
                    cat.slug = item['slug']
                cat.description = item.get('description', '')
                cat.is_active = item.get('is_active', True)
                cat.display_order = item.get('display_order', 0)
                
                # Update parent
                parent_slug = item.get('parent_slug', '').strip() if item.get('parent_slug') else None
                if parent_slug:
                    cat.parent = Category.objects.filter(slug=parent_slug).first()
                else:
                    cat.parent = None
                
                cat.save()
                updated_count += 1
            except Category.DoesNotExist:
                errors.append(f"Categoria ID {item.get('id')} não encontrada")
            except Exception as e:
                errors.append(f"Erro ao atualizar ID {item.get('id')}: {str(e)}")
    
    return JsonResponse({
        'status': 'ok',
        'created': created_count,
        'updated': updated_count,
        'errors': errors,
    })


@staff_member_required
@require_http_methods(["GET"])
def category_products_list(request, category_id):
    """Get all products with their category membership status."""
    try:
        category = Category.objects.get(pk=category_id)
    except Category.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Categoria não encontrada'}, status=404)
    
    # Get all products
    all_products = Product.objects.filter(is_active=True).order_by('name')
    
    # Get products in this category
    category_product_ids = list(category.products.values_list('id', flat=True))
    
    products = []
    for product in all_products:
        products.append({
            'id': product.id,
            'name': product.name,
            'sku': product.slug,
        })
    
    return JsonResponse({
        'category': {
            'id': category.id,
            'name': category.name,
            'full_path': category.full_path,
        },
        'all_products': products,
        'category_product_ids': category_product_ids,
    })


@staff_member_required
@require_http_methods(["POST"])
@csrf_protect
def category_products_update(request, category_id):
    """Update products in a category (add/remove)."""
    try:
        category = Category.objects.get(pk=category_id)
    except Category.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Categoria não encontrada'}, status=404)
    
    try:
        body = json.loads(request.body)
        add_product_ids = body.get('add_product_ids', [])
        remove_product_ids = body.get('remove_product_ids', [])
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'status': 'error', 'message': 'Dados inválidos'}, status=400)
    
    added = 0
    removed = 0
    
    # Add products
    if add_product_ids:
        products_to_add = Product.objects.filter(id__in=add_product_ids, is_active=True)
        for product in products_to_add:
            category.products.add(product)
            added += 1
    
    # Remove products
    if remove_product_ids:
        products_to_remove = Product.objects.filter(id__in=remove_product_ids)
        for product in products_to_remove:
            category.products.remove(product)
            removed += 1
    
    return JsonResponse({
        'status': 'ok',
        'added': added,
        'removed': removed,
        'product_count': category.products.count(),
    })