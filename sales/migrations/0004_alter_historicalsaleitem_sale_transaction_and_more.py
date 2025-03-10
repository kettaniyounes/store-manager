# Generated by Django 5.1.5 on 2025-03-09 15:31

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0003_alter_historicalsaleitem_sale_transaction_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalsaleitem',
            name='sale_transaction',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='sales.saletransaction', verbose_name='Sale Transaction'),
        ),
        migrations.AlterField(
            model_name='historicalsaletransaction',
            name='transaction_id',
            field=models.CharField(db_index=True, default=uuid.uuid4, help_text='Unique transaction identifier (e.g., receipt number)', max_length=100, verbose_name='Transaction ID'),
        ),
        migrations.AlterField(
            model_name='saleitem',
            name='sale_transaction',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sale_items', to='sales.saletransaction', verbose_name='Sale Transaction'),
        ),
        migrations.AlterField(
            model_name='saletransaction',
            name='transaction_id',
            field=models.CharField(default=uuid.uuid4, help_text='Unique transaction identifier (e.g., receipt number)', max_length=100, unique=True, verbose_name='Transaction ID'),
        ),
    ]
