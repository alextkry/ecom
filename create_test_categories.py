#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Category

if not Category.objects.exists():
    # Root categories
    pintura = Category.objects.create(name='Pintura', slug='pintura')
    tecidos = Category.objects.create(name='Tecidos', slug='tecidos')
    acessorios = Category.objects.create(name='Acessórios', slug='acessorios')
    
    # Subcategories under Pintura
    tintas = Category.objects.create(name='Tintas', slug='tintas', parent=pintura)
    pinceis = Category.objects.create(name='Pincéis', slug='pinceis', parent=pintura)
    
    # Subcategories under Tintas
    tinta_tecido = Category.objects.create(name='Tinta para Tecido', slug='tinta-tecido', parent=tintas)
    tinta_acrilica = Category.objects.create(name='Tinta Acrílica', slug='tinta-acrilica', parent=tintas)
    tinta_metal = Category.objects.create(name='Tinta para Metal', slug='tinta-metal', parent=tintas)
    
    # More subcategories
    agulhas = Category.objects.create(name='Agulhas', slug='agulhas', parent=acessorios)
    tesouras = Category.objects.create(name='Tesouras', slug='tesouras', parent=acessorios)
    linhas = Category.objects.create(name='Linhas', slug='linhas', parent=acessorios)
    
    # Tecidos subcategories
    algodao = Category.objects.create(name='Algodão', slug='algodao', parent=tecidos)
    seda = Category.objects.create(name='Seda', slug='seda', parent=tecidos)
    sintetico = Category.objects.create(name='Sintético', slug='sintetico', parent=tecidos)
    
    print('Categorias criadas com sucesso!')
    print(f'Total: {Category.objects.count()} categorias')
else:
    print(f'Já existem {Category.objects.count()} categorias')

for cat in Category.objects.all():
    print(f'  - {cat.full_path}')
