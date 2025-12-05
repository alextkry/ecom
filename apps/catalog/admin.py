from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import redirect
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget
from adminsortable2.admin import SortableAdminMixin, SortableAdminBase, SortableInlineAdminMixin
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    Product,
    AttributeType,
    AttributeOption,
    Variant,
    VariantAttribute,
    VariantImage,
    VariantGroup,
    VariantGroupMembership,
    PriceHistory,
)


# =============================================================================
# Import/Export Resources
# =============================================================================

class VariantResource(resources.ModelResource):
    """Resource for importing/exporting variants."""
    
    product_name = fields.Field(
        column_name='product_name',
        attribute='product',
        widget=ForeignKeyWidget(Product, 'name')
    )
    
    class Meta:
        model = Variant
        import_id_fields = ['sku']
        fields = (
            'sku', 'product_name', 'name', 'cost_price', 'sell_price',
            'compare_at_price', 'stock_quantity', 'track_inventory',
            'allow_backorder', 'weight', 'is_active'
        )
        export_order = fields


class AttributeOptionResource(resources.ModelResource):
    """Resource for importing/exporting attribute options."""
    
    attribute_type_name = fields.Field(
        column_name='attribute_type',
        attribute='attribute_type',
        widget=ForeignKeyWidget(AttributeType, 'name')
    )
    
    class Meta:
        model = AttributeOption
        import_id_fields = ['attribute_type', 'value']
        fields = (
            'attribute_type_name', 'value', 'display_value',
            'color_hex', 'display_order'
        )


# =============================================================================
# Inlines
# =============================================================================

class AttributeOptionInline(SortableInlineAdminMixin, admin.TabularInline):
    model = AttributeOption
    extra = 1
    fields = ['value', 'display_value', 'color_hex', 'display_order']


class VariantAttributeInline(admin.TabularInline):
    model = VariantAttribute
    extra = 1
    autocomplete_fields = ['attribute_option']


class VariantImageInline(SortableInlineAdminMixin, admin.TabularInline):
    model = VariantImage
    extra = 1
    fields = ['image', 'alt_text', 'is_primary', 'display_order', 'image_preview']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 100px;" />',
                obj.thumbnail_small.url if obj.thumbnail_small else obj.image.url
            )
        return '-'
    image_preview.short_description = 'Preview'


class VariantGroupMembershipInline(SortableInlineAdminMixin, admin.TabularInline):
    model = VariantGroupMembership
    extra = 1
    autocomplete_fields = ['variant']
    fields = ['variant', 'display_order']


class VariantInline(admin.TabularInline):
    model = Variant
    extra = 0
    fields = ['sku', 'name', 'sell_price', 'stock_quantity', 'is_active']
    readonly_fields = ['sku', 'name']
    show_change_link = True
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


# =============================================================================
# Model Admins
# =============================================================================

@admin.register(Product)
class ProductAdmin(SimpleHistoryAdmin):
    list_display = ['name', 'slug', 'variant_count', 'active_variant_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['variant_count', 'active_variant_count', 'created_at', 'updated_at']
    inlines = [VariantInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'is_active')
        }),
        ('Informações', {
            'fields': ('variant_count', 'active_variant_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AttributeType)
class AttributeTypeAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'slug', 'datatype', 'option_count', 'display_order']
    list_editable = ['display_order']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [AttributeOptionInline]
    
    def option_count(self, obj):
        return obj.options.count()
    option_count.short_description = 'Opções'


@admin.register(AttributeOption)
class AttributeOptionAdmin(ImportExportModelAdmin):
    resource_class = AttributeOptionResource
    list_display = ['value', 'display_value', 'attribute_type', 'color_swatch', 'display_order']
    list_filter = ['attribute_type']
    list_editable = ['display_order']
    search_fields = ['value', 'display_value', 'attribute_type__name']
    autocomplete_fields = ['attribute_type']
    
    def color_swatch(self, obj):
        if obj.color_hex:
            return format_html(
                '<div style="width: 20px; height: 20px; background-color: {}; '
                'border: 1px solid #ccc; border-radius: 3px;"></div>',
                obj.color_hex
            )
        return '-'
    color_swatch.short_description = 'Cor'


@admin.register(Variant)
class VariantAdmin(SortableAdminBase, ImportExportModelAdmin, SimpleHistoryAdmin):
    resource_class = VariantResource
    list_display = [
        'sku', 'name', 'product', 'sell_price', 'cost_price',
        'stock_quantity', 'stock_status', 'is_active', 'primary_image_preview'
    ]
    list_filter = ['product', 'is_active', 'track_inventory']
    list_editable = ['sell_price', 'stock_quantity', 'is_active']
    search_fields = ['sku', 'name', 'product__name']
    autocomplete_fields = ['product']
    readonly_fields = [
        'created_at', 'updated_at', 'is_on_sale', 'discount_percentage',
        'is_in_stock', 'is_low_stock', 'profit_margin'
    ]
    inlines = [VariantAttributeInline, VariantImageInline]
    list_per_page = 50
    
    fieldsets = (
        (None, {
            'fields': ('product', 'sku', 'name', 'is_active')
        }),
        ('Preços', {
            'fields': ('cost_price', 'sell_price', 'compare_at_price', 'profit_margin')
        }),
        ('Estoque', {
            'fields': (
                'stock_quantity', 'track_inventory', 'allow_backorder',
                'low_stock_threshold', 'is_in_stock', 'is_low_stock'
            )
        }),
        ('Físico', {
            'fields': ('weight',),
            'classes': ('collapse',)
        }),
        ('Informações', {
            'fields': ('is_on_sale', 'discount_percentage', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'activate_variants', 'deactivate_variants',
        'mark_in_stock', 'mark_out_of_stock'
    ]
    
    def stock_status(self, obj):
        if not obj.track_inventory:
            return format_html('<span style="color: blue;">Não rastreado</span>')
        if obj.stock_quantity <= 0:
            if obj.allow_backorder:
                return format_html('<span style="color: orange;">Sob encomenda</span>')
            return format_html('<span style="color: red;">Sem estoque</span>')
        if obj.is_low_stock:
            return format_html('<span style="color: orange;">Estoque baixo</span>')
        return format_html('<span style="color: green;">Em estoque</span>')
    stock_status.short_description = 'Status Estoque'
    
    def primary_image_preview(self, obj):
        img = obj.primary_image
        if img:
            return format_html(
                '<img src="{}" style="max-height: 40px; max-width: 60px;" />',
                img.thumbnail_small.url if img.thumbnail_small else img.image.url
            )
        return '-'
    primary_image_preview.short_description = 'Imagem'
    
    @admin.action(description='Ativar variantes selecionadas')
    def activate_variants(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} variantes ativadas.')

    @admin.action(description='Desativar variantes selecionadas')
    def deactivate_variants(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} variantes desativadas.')

    @admin.action(description='Marcar como em estoque (10 unidades)')
    def mark_in_stock(self, request, queryset):
        count = queryset.update(stock_quantity=10)
        self.message_user(request, f'{count} variantes atualizadas.')

    @admin.action(description='Marcar como sem estoque')
    def mark_out_of_stock(self, request, queryset):
        count = queryset.update(stock_quantity=0)
        self.message_user(request, f'{count} variantes atualizadas.')


@admin.register(VariantGroup)
class VariantGroupAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = [
        'name', 'product', 'variant_count', 'price_range',
        'is_active', 'is_featured', 'display_order'
    ]
    list_filter = ['product', 'is_active', 'is_featured']
    list_editable = ['is_active', 'is_featured', 'display_order']
    search_fields = ['name', 'product__name', 'description']
    autocomplete_fields = ['product']
    raw_id_fields = ['featured_image']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [VariantGroupMembershipInline]
    
    fieldsets = (
        (None, {
            'fields': ('product', 'name', 'slug', 'description')
        }),
        ('Display', {
            'fields': ('is_active', 'is_featured', 'display_order', 'featured_image')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['add_all_product_variants']
    
    @admin.action(description='Adicionar todas as variantes do produto')
    def add_all_product_variants(self, request, queryset):
        for group in queryset:
            variants = Variant.objects.filter(product=group.product, is_active=True)
            for variant in variants:
                VariantGroupMembership.objects.get_or_create(
                    variant_group=group,
                    variant=variant
                )
        self.message_user(request, 'Variantes adicionadas aos grupos selecionados.')


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'variant', 'change_type', 'old_price', 'new_price',
        'price_diff_display', 'changed_by', 'changed_at'
    ]
    list_filter = ['change_type', 'changed_at', 'variant__product']
    search_fields = ['variant__sku', 'variant__name']
    readonly_fields = [
        'variant', 'change_type', 'old_price', 'new_price',
        'changed_by', 'changed_at', 'price_difference', 'percentage_change'
    ]
    date_hierarchy = 'changed_at'
    
    def price_diff_display(self, obj):
        diff = obj.price_difference
        if diff is None:
            return '-'
        if diff > 0:
            return format_html('<span style="color: green;">+R$ {:.2f}</span>', diff)
        elif diff < 0:
            return format_html('<span style="color: red;">R$ {:.2f}</span>', diff)
        return 'R$ 0.00'
    price_diff_display.short_description = 'Diferença'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


# =============================================================================
# Admin Site Configuration
# =============================================================================

admin.site.site_header = 'Ecommerce Admin'
admin.site.site_title = 'Ecommerce'
admin.site.index_title = 'Painel de Administração'
