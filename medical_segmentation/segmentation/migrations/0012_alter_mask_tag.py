# Generated by Django 5.1.1 on 2024-10-01 08:12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('segmentation', '0011_framesequence_height_framesequence_width'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mask',
            name='tag',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='object_class', to='segmentation.objectclass', verbose_name='Tag'),
        ),
    ]