# Generated by Django 5.1.5 on 2025-03-01 21:35

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalproduct',
            name='brand',
            field=models.ForeignKey(blank=True, db_constraint=False, help_text='Optional brand of the product', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='products.brand', verbose_name='Brand'),
        ),
        migrations.AlterField(
            model_name='product',
            name='brand',
            field=models.ForeignKey(blank=True, help_text='Optional brand of the product', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='products', to='products.brand', verbose_name='Brand'),
        ),
    ]
