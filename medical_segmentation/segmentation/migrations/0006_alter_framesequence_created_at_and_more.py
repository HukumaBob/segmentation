# Generated by Django 5.1.1 on 2024-09-26 06:55

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('segmentation', '0005_alter_video_video_file'),
    ]

    operations = [
        migrations.AlterField(
            model_name='framesequence',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='framesequence',
            name='frame_file',
            field=models.ImageField(upload_to='frames/', verbose_name='Frame'),
        ),
        migrations.AlterField(
            model_name='framesequence',
            name='video',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='frame_sequences', to='segmentation.video', verbose_name='Video'),
        ),
        migrations.AlterField(
            model_name='mask',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='mask',
            name='frame_sequence',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='masks', to='segmentation.framesequence', verbose_name='Frame'),
        ),
        migrations.AlterField(
            model_name='mask',
            name='mask_file',
            field=models.ImageField(upload_to='masks/', verbose_name='Mask file'),
        ),
        migrations.AlterField(
            model_name='mask',
            name='tag',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='object_class', to='segmentation.objectclass', verbose_name='Tagк'),
        ),
        migrations.AlterField(
            model_name='video',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='video',
            name='description',
            field=models.TextField(blank=True, verbose_name='Video description'),
        ),
        migrations.AlterField(
            model_name='video',
            name='title',
            field=models.CharField(max_length=255, verbose_name='Video title'),
        ),
        migrations.AlterField(
            model_name='video',
            name='video_file',
            field=models.FileField(unique=True, upload_to='videos/', verbose_name='Video file'),
        ),
    ]
