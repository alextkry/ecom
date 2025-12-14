#!/usr/bin/env python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.catalog.models import Product, VariantAttribute

p = Product.objects.get(pk=2)
print(f'Product: {p.name}')

# Limpar atributos 
VariantAttribute.objects.filter(variant__product=p).delete()
p.metadata_attributes = None
p.metadata_variants = None
p.save()
print('Cleared all data')

# Simular salvamento com atributos E variantes
item = {
    'attributes_json': [
        {'atributo': 'Cor', 'valores': ['Azul', 'Branco', 'Preto']},
        {'atributo': 'Tamanho', 'valores': ['P', 'M', 'G']}
    ],
    'variants_json': [
        {'sku': 'CAM-AZU-G', 'nome': 'Camiseta Azul G', 'cor': 'Azul', 'tamanho': 'G', 'estoque': 10, 'preco_custo': 35, 'preco_venda': 79.9},
        {'sku': 'CAM-AZU-M', 'nome': 'Camiseta Azul M', 'cor': 'Azul', 'tamanho': 'M', 'estoque': 10, 'preco_custo': 35, 'preco_venda': 79.9},
        {'sku': 'CAM-BRA-G', 'nome': 'Camiseta Branco G', 'cor': 'Branco', 'tamanho': 'G', 'estoque': 10, 'preco_custo': 35, 'preco_venda': 79.9},
    ]
}

from apps.catalog.views import _process_product_json_data
_process_product_json_data(p, item)

for v in p.variants.all()[:3]:
    attrs = list(VariantAttribute.objects.filter(variant=v))
    print(f'{v.sku}: {len(attrs)} attrs')
    for va in attrs:
        print(f'  {va.attribute_option.attribute_type.name}: {va.attribute_option.value}')
