import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_protect
from django.db import transaction

from .models import (
    Product,
    Variant,
    VariantGroup,
    VariantGroupMembership,
    AttributeType,
)


@staff_member_required
def bulk_edit_view(request):
    """Render the bulk edit page with Handsontable."""
    products = Product.objects.filter(is_active=True).order_by('name')
    variant_groups = VariantGroup.objects.filter(is_active=True).order_by('product__name', 'name')
    
    context = {
        'products': products,
        'variant_groups': variant_groups,
        'title': 'Edição em Massa de Variantes',
    }
    return render(request, 'catalog/bulk_edit.html', context)


@staff_member_required
@require_http_methods(["GET"])
def bulk_edit_data(request):
    """API endpoint to get variant data for Handsontable."""
    product_id = request.GET.get('product_id')
    group_id = request.GET.get('group_id')
    
    variants = Variant.objects.select_related('product').prefetch_related(
        'variantattribute_set__attribute_option__attribute_type',
        'groups'
    )
    
    if product_id:
        variants = variants.filter(product_id=product_id)
    elif group_id:
        variants = variants.filter(groups__id=group_id)
    else:
        variants = variants[:100]  # Limit if no filter
    
    # Get attribute types for this product
    if product_id:
        product = Product.objects.get(pk=product_id)
        attr_types = product.get_attribute_types()
    else:
        attr_types = AttributeType.objects.all()[:5]  # Limit
    
    # Build data rows
    data = []
    for variant in variants:
        row = {
            'id': variant.id,
            'sku': variant.sku,
            'name': variant.name,
            'product_name': variant.product.name,
            'cost_price': float(variant.cost_price) if variant.cost_price else None,
            'sell_price': float(variant.sell_price),
            'compare_at_price': float(variant.compare_at_price) if variant.compare_at_price else None,
            'stock_quantity': variant.stock_quantity,
            'is_active': variant.is_active,
            'groups': ', '.join([g.name for g in variant.groups.all()]),
        }
        
        # Add attribute values
        variant_attrs = {
            va.attribute_option.attribute_type.slug: va.attribute_option.value
            for va in variant.variantattribute_set.all()
        }
        for attr_type in attr_types:
            row[f'attr_{attr_type.slug}'] = variant_attrs.get(attr_type.slug, '')
        
        data.append(row)
    
    # Build columns config
    columns = [
        {'data': 'id', 'title': 'ID', 'readOnly': True, 'width': 50},
        {'data': 'sku', 'title': 'SKU', 'width': 120},
        {'data': 'name', 'title': 'Nome', 'width': 200},
        {'data': 'product_name', 'title': 'Produto', 'readOnly': True, 'width': 150},
    ]
    
    # Add attribute columns
    for attr_type in attr_types:
        columns.append({
            'data': f'attr_{attr_type.slug}',
            'title': attr_type.name,
            'readOnly': True,
            'width': 100,
        })
    
    columns.extend([
        {'data': 'cost_price', 'title': 'Preço Custo', 'type': 'numeric', 'numericFormat': {'pattern': '0.00'}, 'width': 100},
        {'data': 'sell_price', 'title': 'Preço Venda', 'type': 'numeric', 'numericFormat': {'pattern': '0.00'}, 'width': 100},
        {'data': 'compare_at_price', 'title': 'Preço Comp.', 'type': 'numeric', 'numericFormat': {'pattern': '0.00'}, 'width': 100},
        {'data': 'stock_quantity', 'title': 'Estoque', 'type': 'numeric', 'width': 80},
        {'data': 'is_active', 'title': 'Ativo', 'type': 'checkbox', 'width': 60},
        {'data': 'groups', 'title': 'Grupos', 'readOnly': True, 'width': 200},
    ])
    
    return JsonResponse({
        'data': data,
        'columns': columns,
    })


@staff_member_required
@require_http_methods(["POST"])
@csrf_protect
def bulk_edit_save(request):
    """API endpoint to save bulk changes."""
    try:
        changes = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    
    updated_count = 0
    errors = []
    
    # Map of field names to model fields
    editable_fields = {
        'sku': 'sku',
        'name': 'name',
        'cost_price': 'cost_price',
        'sell_price': 'sell_price',
        'compare_at_price': 'compare_at_price',
        'stock_quantity': 'stock_quantity',
        'is_active': 'is_active',
    }
    
    with transaction.atomic():
        for change in changes:
            variant_id = change.get('id')
            field = change.get('field')
            value = change.get('value')
            
            if not variant_id or field not in editable_fields:
                continue
            
            try:
                variant = Variant.objects.get(pk=variant_id)
                model_field = editable_fields[field]
                
                # Handle None/empty values for decimal fields
                if field in ['cost_price', 'compare_at_price'] and (value == '' or value is None):
                    value = None
                
                setattr(variant, model_field, value)
                variant.save()
                updated_count += 1
            except Variant.DoesNotExist:
                errors.append(f"Variante {variant_id} não encontrada")
            except Exception as e:
                errors.append(f"Erro ao atualizar variante {variant_id}: {str(e)}")
    
    return JsonResponse({
        'status': 'ok',
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
