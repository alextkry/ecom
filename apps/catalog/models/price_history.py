from django.db import models
from django.conf import settings
from decimal import Decimal


class PriceHistory(models.Model):
    """
    Track price changes for variants for audit purposes.
    Automatically created when variant prices change.
    """
    CHANGE_TYPE_CHOICES = [
        ('cost', 'Preço de Custo'),
        ('sell', 'Preço de Venda'),
        ('compare', 'Preço Comparativo'),
    ]
    
    variant = models.ForeignKey(
        'catalog.Variant',
        on_delete=models.CASCADE,
        related_name='price_history',
        verbose_name='Variante'
    )
    change_type = models.CharField(
        max_length=10,
        choices=CHANGE_TYPE_CHOICES,
        verbose_name='Tipo de alteração'
    )
    old_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Preço anterior'
    )
    new_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Novo preço'
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Alterado por'
    )
    changed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Alterado em'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Observações'
    )

    class Meta:
        ordering = ['-changed_at']
        verbose_name = 'Histórico de Preço'
        verbose_name_plural = 'Histórico de Preços'

    def __str__(self):
        return f"{self.variant.sku} - {self.get_change_type_display()}: {self.old_price} → {self.new_price}"

    @property
    def price_difference(self):
        if self.old_price is None or self.new_price is None:
            return None
        return self.new_price - self.old_price

    @property
    def percentage_change(self):
        if self.old_price is None or self.old_price == 0:
            return None
        diff = self.price_difference
        if diff is None:
            return None
        return (diff / self.old_price) * 100
