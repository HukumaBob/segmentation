# Generated by Django 5.1.1 on 2024-10-14 05:29

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('segmentation', '0015_rename_objectclass_tag'),
    ]

    operations = [
        migrations.CreateModel(
            name='TagsCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tags_category', models.CharField(max_length=100, verbose_name='Category of tag')),
            ],
        ),
        migrations.RemoveField(
            model_name='imageupload',
            name='object_class',
        ),
        migrations.AddField(
            model_name='imageupload',
            name='tag',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='segmentation.tag', verbose_name='Tag'),
        ),
        migrations.AddField(
            model_name='tag',
            name='code',
            field=models.IntegerField(blank=True, null=True, verbose_name='Code of tag'),
        ),
    ]