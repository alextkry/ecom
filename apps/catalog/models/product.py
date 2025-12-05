from django.db import models
from django.utils.text import slugify
from simple_history.models import HistoricalRecords


class Product(models.Model):
    """
    Base product model.
    Example: "Linha Modelo_X" which has multiple variants.
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
    is_active = models.BooleanField(
        default=True,
        verbose_name='Ativo'
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

    def get_attribute_types(self):
        """Get all attribute types used by this product's variants."""
        from .attribute import AttributeType
        return AttributeType.objects.filter(
            options__variantattribute__variant__product=self
        ).distinct().order_by('display_order')
