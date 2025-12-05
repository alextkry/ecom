from django.db import models
from django.core.validators import RegexValidator


class AttributeType(models.Model):
    """
    Dynamic attribute types that can be added at runtime.
    Examples: Color, Length, Number, Size, Material, etc.
    """
    DATATYPE_CHOICES = [
        ('text', 'Texto'),
        ('number', 'Número'),
        ('decimal', 'Decimal'),
        ('color', 'Cor (Hex)'),
    ]
    
    name = models.CharField(
        max_length=100,
        verbose_name='Nome'
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name='Slug'
    )
    datatype = models.CharField(
        max_length=20,
        choices=DATATYPE_CHOICES,
        default='text',
        verbose_name='Tipo de dado'
    )
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name='Ordem de exibição'
    )
    
    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Tipo de Atributo'
        verbose_name_plural = 'Tipos de Atributos'

    def __str__(self):
        return self.name


class AttributeOption(models.Model):
    """
    Possible values for each attribute type.
    Examples: 
        - AttributeType="Color" -> Options: "branco", "preto", "azul"
        - AttributeType="Length" -> Options: "230m", "350m", "480m"
        - AttributeType="Number" -> Options: "5", "8", "10", "20"
    """
    hex_color_validator = RegexValidator(
        regex=r'^#[0-9A-Fa-f]{6}$',
        message='Cor deve estar no formato hexadecimal (#RRGGBB)'
    )
    
    attribute_type = models.ForeignKey(
        AttributeType,
        on_delete=models.CASCADE,
        related_name='options',
        verbose_name='Tipo de Atributo'
    )
    value = models.CharField(
        max_length=100,
        verbose_name='Valor'
    )
    display_value = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Valor de exibição',
        help_text='Nome alternativo para exibição (opcional)'
    )
    color_hex = models.CharField(
        max_length=7,
        blank=True,
        validators=[hex_color_validator],
        verbose_name='Cor Hex',
        help_text='Para swatches de cor (#RRGGBB)'
    )
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name='Ordem de exibição'
    )

    class Meta:
        ordering = ['display_order', 'value']
        unique_together = ['attribute_type', 'value']
        verbose_name = 'Opção de Atributo'
        verbose_name_plural = 'Opções de Atributos'

    def __str__(self):
        return f"{self.attribute_type.name}: {self.display_value or self.value}"

    def get_display_value(self):
        return self.display_value or self.value
