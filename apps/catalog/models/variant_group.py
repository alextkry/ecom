from django.db import models
from django.utils.text import slugify


class VariantGroup(models.Model):
    """
    Groups of variants for display purposes.
    Example: "Linha Modelo_X colorida (número 5) (230m)"
    
    Allows grouping variants by similar characteristics for easier navigation
    and display in the storefront.
    """
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='variant_groups',
        verbose_name='Produto'
    )
    name = models.CharField(
        max_length=255,
        verbose_name='Nome'
    )
    slug = models.SlugField(
        max_length=255,
        verbose_name='Slug'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Descrição'
    )
    
    # SEO
    meta_title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Título SEO'
    )
    meta_description = models.TextField(
        max_length=500,
        blank=True,
        verbose_name='Descrição SEO'
    )
    
    # Variants in this group
    variants = models.ManyToManyField(
        'catalog.Variant',
        through='VariantGroupMembership',
        related_name='groups',
        verbose_name='Variantes'
    )
    
    # Display settings
    is_active = models.BooleanField(
        default=True,
        verbose_name='Ativo'
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name='Destaque'
    )
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name='Ordem de exibição'
    )
    
    # Featured image (optional, can fallback to first variant's image)
    featured_image = models.ForeignKey(
        'catalog.VariantImage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Imagem destaque'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criado em'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Atualizado em'
    )

    class Meta:
        ordering = ['display_order', 'name']
        unique_together = ['product', 'slug']
        verbose_name = 'Grupo de Variantes'
        verbose_name_plural = 'Grupos de Variantes'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def variant_count(self):
        return self.variants.count()

    @property
    def min_price(self):
        """Get minimum price among group variants."""
        result = self.variants.filter(is_active=True).aggregate(
            min_price=models.Min('sell_price')
        )
        return result['min_price']

    @property
    def max_price(self):
        """Get maximum price among group variants."""
        result = self.variants.filter(is_active=True).aggregate(
            max_price=models.Max('sell_price')
        )
        return result['max_price']

    @property
    def price_range(self):
        """Return price range string."""
        min_p, max_p = self.min_price, self.max_price
        if min_p == max_p:
            return f"R$ {min_p:.2f}"
        return f"R$ {min_p:.2f} - R$ {max_p:.2f}"

    @property
    def total_stock(self):
        """Sum of stock for all variants in group."""
        result = self.variants.filter(is_active=True).aggregate(
            total=models.Sum('stock_quantity')
        )
        return result['total'] or 0

    @property
    def display_image(self):
        """Get featured image or first variant's primary image."""
        if self.featured_image:
            return self.featured_image
        
        first_variant = self.variants.filter(is_active=True).first()
        if first_variant:
            return first_variant.primary_image
        return None

    def get_available_attribute_options(self):
        """
        Returns all unique attribute options across variants in this group.
        Useful for building navigation filters.
        """
        from .attribute import AttributeOption
        return AttributeOption.objects.filter(
            variants__groups=self
        ).select_related('attribute_type').distinct()

    def get_common_attribute_options(self):
        """
        Returns attribute options that are common to ALL variants in this group.
        Useful for identifying what defines this group.
        """
        from .attribute import AttributeOption
        from django.db.models import Count
        
        variant_count = self.variants.count()
        if variant_count == 0:
            return AttributeOption.objects.none()
        
        return AttributeOption.objects.filter(
            variants__groups=self
        ).annotate(
            usage_count=Count('variants', filter=models.Q(variants__groups=self))
        ).filter(
            usage_count=variant_count
        ).select_related('attribute_type')


class VariantGroupMembership(models.Model):
    """Through model for ordering variants within a group."""
    variant_group = models.ForeignKey(
        VariantGroup,
        on_delete=models.CASCADE,
        verbose_name='Grupo'
    )
    variant = models.ForeignKey(
        'catalog.Variant',
        on_delete=models.CASCADE,
        verbose_name='Variante'
    )
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name='Ordem de exibição'
    )

    class Meta:
        ordering = ['display_order']
        unique_together = ['variant_group', 'variant']
        verbose_name = 'Membro do Grupo'
        verbose_name_plural = 'Membros do Grupo'

    def __str__(self):
        return f"{self.variant_group.name} - {self.variant.sku}"
