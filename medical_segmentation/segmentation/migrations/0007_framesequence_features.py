# Generated by Django 5.1.1 on 2024-09-26 08:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('segmentation', '0006_alter_framesequence_created_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='framesequence',
            name='features',
            field=models.CharField(default=0, max_length=255, verbose_name='Frames features'),
            preserve_default=False,
        ),
    ]