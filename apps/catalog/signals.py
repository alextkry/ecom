"""
Django signals for the catalog app.
Handles automatic creation of price history records.
"""

from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import Variant, PriceHistory


@receiver(pre_save, sender=Variant)
def track_price_changes(sender, instance, **kwargs):
    """
    Create PriceHistory records when variant prices change.
    """
    if not instance.pk:
        # New variant, no history to track
        return
    
    try:
        old_instance = Variant.objects.get(pk=instance.pk)
    except Variant.DoesNotExist:
        return
    
    # Track cost price changes
    if old_instance.cost_price != instance.cost_price:
        PriceHistory.objects.create(
            variant=instance,
            change_type='cost',
            old_price=old_instance.cost_price,
            new_price=instance.cost_price,
        )
    
    # Track sell price changes
    if old_instance.sell_price != instance.sell_price:
        PriceHistory.objects.create(
            variant=instance,
            change_type='sell',
            old_price=old_instance.sell_price,
            new_price=instance.sell_price,
        )
    
    # Track compare at price changes
    if old_instance.compare_at_price != instance.compare_at_price:
        PriceHistory.objects.create(
            variant=instance,
            change_type='compare',
            old_price=old_instance.compare_at_price,
            new_price=instance.compare_at_price,
        )
