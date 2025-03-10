# sales/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import F
from .models import SaleItem

@receiver(post_save, sender=SaleItem)
def update_product_stock_on_sale_item_save(sender, instance, created, **kwargs):
    """
    Signal handler to update product stock quantity when a SaleItem is saved (created).
    Uses the update() method to avoid saving an unresolved F() expression.
    """
    if created:
        product_variant = instance.product_variant
        quantity = instance.quantity
        if product_variant:
            # Use the update() method on the queryset to perform an atomic update.
            product_variant.__class__.objects.filter(pk=product_variant.pk).update(
                stock_quantity=F('stock_quantity') - quantity
            )
            product_variant.refresh_from_db()
