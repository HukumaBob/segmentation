# Generated by Django 5.1.1 on 2024-09-23 12:47

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('segmentation', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ObjectClass',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.AlterField(
            model_name='imageupload',
            name='object_class',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='segmentation.objectclass'),
        ),
    ]