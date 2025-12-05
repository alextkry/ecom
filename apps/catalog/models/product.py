from django.db import models
from django.utils.text import slugify
from simple_history.models import HistoricalRecords


class Product(models.Model):
    """
    Base product model.
    Example: "Linha Modelo_X" which has multiple variants.
    Products don't have their own images - they use images from their variants.
    """
    name = models.CharField(
        max_length=255,
        verbose_name='Nome'
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        verbose_name='Slug'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Descrição'
    )
    categories = models.ManyToManyField(
        'Category',
        blank=True,
        related_name='products',
        verbose_name='Categorias'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Ativo'
    )
    
    # JSON metadata fields - store the JSON representation for comparison
    # These are updated when saving from bulk edit and used to detect changes
    metadata_attributes = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Metadados: Atributos',
        help_text='JSON dos atributos do produto'
    )
    metadata_variants = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Metadados: Variantes',
        help_text='JSON das variantes do produto'
    )
    metadata_groups = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Metadados: Grupos',
        help_text='JSON dos grupos do produto'
    )
    metadata_categories = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Metadados: Categorias',
        help_text='JSON das categorias do produto'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criado em'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Atualizado em'
    )
    
    # History tracking
    history = HistoricalRecords()

    class Meta:
        ordering = ['name']
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'

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
    def active_variant_count(self):
        return self.variants.filter(is_active=True).count()

    def get_thumbnail_url(self):
        """Get thumbnail URL from the first variant that has an image."""
        # Get first variant with images
        for variant in self.variants.prefetch_related('images').all():
            primary_image = variant.primary_image
            if primary_image:
                try:
                    return primary_image.thumbnail_small.url
                except Exception:
                    return primary_image.image.url
        return None

    def get_all_categories(self):
        """Get all categories including ancestors."""
        all_cats = set()
        for cat in self.categories.all():
            all_cats.add(cat)
            for ancestor in cat.get_ancestors():
                all_cats.add(ancestor)
        return all_cats

    def get_attribute_types(self):
        """Get all attribute types used by this product's variants."""
        from .attribute import AttributeType
        return AttributeType.objects.filter(
            options__variantattribute__variant__product=self
        ).distinct().order_by('display_order')
