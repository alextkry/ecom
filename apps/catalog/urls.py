from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    # Bulk edit main view
    path('bulk-edit/', views.bulk_edit_view, name='bulk_edit'),
    
    # Products CRUD
    path('bulk-edit/products/data/', views.bulk_products_data, name='bulk_products_data'),
    path('bulk-edit/products/save/', views.bulk_products_save, name='bulk_products_save'),
    
    # Variants CRUD
    path('bulk-edit/variants/data/', views.bulk_variants_data, name='bulk_variants_data'),
    path('bulk-edit/variants/save/', views.bulk_variants_save, name='bulk_variants_save'),
    
    # Attribute Options CRUD
    path('bulk-edit/attr-options/data/', views.bulk_attr_options_data, name='bulk_attr_options_data'),
    path('bulk-edit/attr-options/save/', views.bulk_attr_options_save, name='bulk_attr_options_save'),
    
    # Create Attribute Type
    path('bulk-edit/attr-types/create/', views.bulk_create_attr_type, name='bulk_create_attr_type'),
    
    # Groups CRUD
    path('bulk-edit/groups/data/', views.bulk_groups_data, name='bulk_groups_data'),
    path('bulk-edit/groups/save/', views.bulk_groups_save, name='bulk_groups_save'),
    path('bulk-edit/add-to-group/', views.bulk_add_to_group, name='bulk_add_to_group'),
    path('bulk-edit/groups/create-with-variants/', views.bulk_create_group_with_variants, name='bulk_create_group_with_variants'),
    
    # Variant Images
    path('bulk-edit/variants/<int:variant_id>/images/', views.variant_images_list, name='variant_images_list'),
    path('bulk-edit/variants/<int:variant_id>/images/upload/', views.variant_image_upload, name='variant_image_upload'),
    path('bulk-edit/images/<int:image_id>/delete/', views.variant_image_delete, name='variant_image_delete'),
    path('bulk-edit/images/<int:image_id>/set-primary/', views.variant_image_set_primary, name='variant_image_set_primary'),
]
