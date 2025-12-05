from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('bulk-edit/', views.bulk_edit_view, name='bulk_edit'),
    path('bulk-edit/data/', views.bulk_edit_data, name='bulk_edit_data'),
    path('bulk-edit/save/', views.bulk_edit_save, name='bulk_edit_save'),
    path('bulk-edit/add-to-group/', views.bulk_add_to_group, name='bulk_add_to_group'),
]
