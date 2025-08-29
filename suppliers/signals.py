
# Django import
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum
from .models import SupplierPayment

# Python import 
from decimal import Decimal


@receiver(post_save, sender=SupplierPayment)
def update_po_total_paid_amount_on_payment_save(sender, instance, created, **kwargs):
    """
    Signal handler to update PurchaseOrder.total_paid_amount when a SupplierPayment is saved (created or updated).
    """
    purchase_order = instance.purchase_order
    if purchase_order:
        total_paid = SupplierPayment.objects.filter(purchase_order=purchase_order).aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
        purchase_order.total_paid_amount = total_paid
        purchase_order.save()

@receiver(post_delete, sender=SupplierPayment)
def update_po_total_paid_amount_on_payment_delete(sender, instance, **kwargs):
    """
    Signal handler to update PurchaseOrder.total_paid_amount when a SupplierPayment is deleted.
    """
    purchase_order = instance.purchase_order
    if purchase_order:
        total_paid = SupplierPayment.objects.filter(purchase_order=purchase_order).aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
        purchase_order.total_paid_amount = total_paid
        purchase_order.save()