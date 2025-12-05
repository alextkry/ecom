"""
Script to create sample data for testing the bulk edit interface.
Run with: docker-compose exec web python manage.py shell < create_sample_data.py
"""
from apps.catalog.models import (
    Product,
    Variant,
    AttributeType,
    AttributeOption,
    VariantAttribute,
    VariantGroup,
    VariantGroupMembership,
)
from decimal import Decimal

# Create Attribute Types
print("Creating attribute types...")

color, _ = AttributeType.objects.get_or_create(
    slug='color',
    defaults={'name': 'Cor', 'datatype': 'text', 'display_order': 1}
)

size, _ = AttributeType.objects.get_or_create(
    slug='size',
    defaults={'name': 'Tamanho', 'datatype': 'text', 'display_order': 2}
)

length, _ = AttributeType.objects.get_or_create(
    slug='length',
    defaults={'name': 'Comprimento', 'datatype': 'number', 'display_order': 3}
)

# Create Attribute Options
print("Creating attribute options...")

colors = ['Preto', 'Branco', 'Azul', 'Vermelho', 'Verde']
color_hexes = ['#000000', '#FFFFFF', '#0000FF', '#FF0000', '#00FF00']

for i, (c, h) in enumerate(zip(colors, color_hexes)):
    AttributeOption.objects.get_or_create(
        attribute_type=color,
        value=c,
        defaults={'display_value': c, 'color_hex': h, 'display_order': i}
    )

sizes = ['P', 'M', 'G', 'GG', 'XGG']
for i, s in enumerate(sizes):
    AttributeOption.objects.get_or_create(
        attribute_type=size,
        value=s,
        defaults={'display_value': s, 'display_order': i}
    )

lengths = ['30cm', '50cm', '70cm', '100cm']
for i, l in enumerate(lengths):
    AttributeOption.objects.get_or_create(
        attribute_type=length,
        value=l,
        defaults={'display_value': l, 'display_order': i}
    )

# Create Products
print("Creating products...")

product1, _ = Product.objects.get_or_create(
    slug='camiseta-basica',
    defaults={'name': 'Camiseta Básica', 'description': 'Camiseta de algodão confortável', 'is_active': True}
)

product2, _ = Product.objects.get_or_create(
    slug='calca-jeans',
    defaults={'name': 'Calça Jeans', 'description': 'Calça jeans clássica', 'is_active': True}
)

product3, _ = Product.objects.get_or_create(
    slug='extensao-cabelo',
    defaults={'name': 'Extensão de Cabelo', 'description': 'Extensão de cabelo natural', 'is_active': True}
)

# Create some variants for product1
print("Creating variants...")

sku_counter = 1
for color_opt in AttributeOption.objects.filter(attribute_type=color)[:3]:
    for size_opt in AttributeOption.objects.filter(attribute_type=size)[:3]:
        sku = f'CAM-{color_opt.value[:3].upper()}-{size_opt.value}'
        variant, created = Variant.objects.get_or_create(
            sku=sku,
            defaults={
                'product': product1,
                'name': f'Camiseta {color_opt.value} {size_opt.value}',
                'cost_price': Decimal('35.00'),
                'sell_price': Decimal('79.90'),
                'stock_quantity': 10,
                'is_active': True
            }
        )
        if created:
            VariantAttribute.objects.create(variant=variant, attribute_option=color_opt)
            VariantAttribute.objects.create(variant=variant, attribute_option=size_opt)

# Create variants for product3 (with length)
for color_opt in AttributeOption.objects.filter(attribute_type=color)[:2]:
    for length_opt in AttributeOption.objects.filter(attribute_type=length):
        sku = f'EXT-{color_opt.value[:3].upper()}-{length_opt.value}'
        variant, created = Variant.objects.get_or_create(
            sku=sku,
            defaults={
                'product': product3,
                'name': f'Extensão {color_opt.value} {length_opt.value}',
                'cost_price': Decimal('150.00'),
                'sell_price': Decimal('349.90'),
                'stock_quantity': 5,
                'is_active': True
            }
        )
        if created:
            VariantAttribute.objects.create(variant=variant, attribute_option=color_opt)
            VariantAttribute.objects.create(variant=variant, attribute_option=length_opt)

# Create Variant Groups
print("Creating variant groups...")

group1, _ = VariantGroup.objects.get_or_create(
    product=product1,
    name='Camisetas Pretas',
    defaults={'is_active': True}
)

# Add variants to group
black_variants = Variant.objects.filter(
    product=product1,
    variantattribute__attribute_option__value='Preto'
)
for var in black_variants:
    VariantGroupMembership.objects.get_or_create(
        variant_group=group1,
        variant=var
    )

print("\n✅ Sample data created successfully!")
print(f"   - {Product.objects.count()} products")
print(f"   - {Variant.objects.count()} variants")
print(f"   - {AttributeType.objects.count()} attribute types")
print(f"   - {AttributeOption.objects.count()} attribute options")
print(f"   - {VariantGroup.objects.count()} variant groups")
print("\nAccess the bulk edit interface at: http://localhost:8000/catalog/bulk-edit/")
