# Generated by Django 5.1.1 on 2024-09-26 06:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('segmentation', '0004_alter_mask_tag'),
    ]

    operations = [
        migrations.AlterField(
            model_name='video',
            name='video_file',
            field=models.FileField(unique=True, upload_to='videos/', verbose_name='Файл видео'),
        ),
    ]