# Generated by Django 5.1.1 on 2024-12-05 05:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nettrain', '0002_neuralnetworkversion_training_tags'),
    ]

    operations = [
        migrations.AlterField(
            model_name='neuralnetworkversion',
            name='description',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Description'),
        ),
    ]
