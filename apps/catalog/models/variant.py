from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from simple_history.models import HistoricalRecords
from imagekit.models import ProcessedImageField, ImageSpecField
from imagekit.processors import ResizeToFill, ResizeToFit


class Variant(models.Model):
    """
    Individual SKU with its own price, stock, and images.
    Each variant is a unique combination of attribute options.
    """
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='Produto'
    )
    sku = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='SKU'
    )
    name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Nome',
        help_text='Nome personalizado (gerado automaticamente se vazio)'
    )
    
    # Pricing
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Preço de custo'
    )
    sell_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Preço de venda'
    )
    compare_at_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Preço comparativo',
        help_text='Preço "de" para mostrar desconto'
    )
    
    # Inventory
    stock_quantity = models.IntegerField(
        default=0,
        verbose_name='Quantidade em estoque'
    )
    track_inventory = models.BooleanField(
        default=True,
        verbose_name='Rastrear estoque'
    )
    allow_backorder = models.BooleanField(
        default=False,
        verbose_name='Permitir compra sem estoque'
    )
    low_stock_threshold = models.PositiveIntegerField(
        default=5,
        verbose_name='Limite de estoque baixo'
    )
    
    # Physical properties (optional)
    weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name='Peso (kg)'
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name='Ativo'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criado em'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Atualizado em'
    )
    
    # Attribute options for this variant
    attribute_options = models.ManyToManyField(
        'catalog.AttributeOption',
        through='VariantAttribute',
        related_name='variants',
        verbose_name='Opções de atributos'
    )
    
    # History tracking
    history = HistoricalRecords()

    class Meta:
        ordering = ['product', 'sku']
        verbose_name = 'Variante'
        verbose_name_plural = 'Variantes'

    def __str__(self):
        return self.name or self.sku

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self._generate_name()
        super().save(*args, **kwargs)

    def _generate_name(self):
        """Generate variant name from product name and attribute options."""
        if not self.pk:
            return self.sku
        
        options = self.variantattribute_set.select_related(
            'attribute_option__attribute_type'
        ).order_by('attribute_option__attribute_type__display_order')
        
        if not options.exists():
            return f"{self.product.name} - {self.sku}"
        
        option_strings = [
            opt.attribute_option.get_display_value() 
            for opt in options
        ]
        return f"{self.product.name} - {' / '.join(option_strings)}"

    def get_option_value(self, attribute_slug):
        """Get the option value for a specific attribute type."""
        try:
            va = self.variantattribute_set.select_related(
                'attribute_option__attribute_type'
            ).get(attribute_option__attribute_type__slug=attribute_slug)
            return va.attribute_option.value
        except VariantAttribute.DoesNotExist:
            return None

    def get_options_dict(self):
        """Return dict of {attribute_slug: option_value}"""
        return {
            va.attribute_option.attribute_type.slug: va.attribute_option.value
            for va in self.variantattribute_set.select_related(
                'attribute_option__attribute_type'
            )
        }

    @property
    def is_on_sale(self):
        return bool(self.compare_at_price and self.compare_at_price > self.sell_price)

    @property
    def discount_percentage(self):
        if not self.is_on_sale:
            return 0
        return int(((self.compare_at_price - self.sell_price) / self.compare_at_price) * 100)

    @property
    def is_in_stock(self):
        if not self.track_inventory:
            return True
        return self.stock_quantity > 0 or self.allow_backorder

    @property
    def is_low_stock(self):
        if not self.track_inventory:
            return False
        return 0 < self.stock_quantity <= self.low_stock_threshold

    @property
    def primary_image(self):
        return self.images.filter(is_primary=True).first() or self.images.first()

    @property
    def profit_margin(self):
        if not self.cost_price or self.cost_price == 0:
            return None
        return ((self.sell_price - self.cost_price) / self.cost_price) * 100


class VariantAttribute(models.Model):
    """
    Through model linking Variant to AttributeOption.
    Ensures each variant has only one value per attribute type.
    """
    variant = models.ForeignKey(
        Variant,
        on_delete=models.CASCADE,
        verbose_name='Variante'
    )
    attribute_option = models.ForeignKey(
        'catalog.AttributeOption',
        on_delete=models.CASCADE,
        verbose_name='Opção de Atributo'
    )

    class Meta:
        unique_together = ['variant', 'attribute_option']
        verbose_name = 'Atributo da Variante'
        verbose_name_plural = 'Atributos das Variantes'

    def __str__(self):
        return f"{self.variant.sku} - {self.attribute_option}"

    def save(self, *args, **kwargs):
        # Ensure only one option per attribute type per variant
        existing = VariantAttribute.objects.filter(
            variant=self.variant,
            attribute_option__attribute_type=self.attribute_option.attribute_type
        ).exclude(pk=self.pk)
        
        if existing.exists():
            existing.delete()
        
        super().save(*args, **kwargs)


class VariantImage(models.Model):
    """Images for each variant with automatic thumbnail generation."""
    variant = models.ForeignKey(
        Variant,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Variante'
    )
    image = ProcessedImageField(
        upload_to='variants/%Y/%m/',
        processors=[ResizeToFit(1200, 1200)],
        format='JPEG',
        options={'quality': 85},
        verbose_name='Imagem'
    )
    thumbnail = ImageSpecField(
        source='image',
        processors=[ResizeToFill(300, 300)],
        format='JPEG',
        options={'quality': 70}
    )
    thumbnail_small = ImageSpecField(
        source='image',
        processors=[ResizeToFill(100, 100)],
        format='JPEG',
        options={'quality': 60}
    )
    alt_text = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Texto alternativo'
    )
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name='Ordem de exibição'
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name='Imagem principal'
    )

    class Meta:
        ordering = ['-is_primary', 'display_order']
        verbose_name = 'Imagem da Variante'
        verbose_name_plural = 'Imagens das Variantes'

    def __str__(self):
        return f"{self.variant.sku} - Imagem {self.display_order}"

    def save(self, *args, **kwargs):
        # Ensure only one primary image per variant
        if self.is_primary:
            VariantImage.objects.filter(
                variant=self.variant,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        
        # Auto-generate alt text if empty
        if not self.alt_text:
            self.alt_text = str(self.variant)
        
        super().save(*args, **kwargs)
