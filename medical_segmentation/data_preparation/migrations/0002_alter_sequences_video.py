# Generated by Django 5.1.1 on 2024-11-20 11:49

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_preparation', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sequences',
            name='video',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sequences', to='data_preparation.video', verbose_name='Video'),
        ),
    ]