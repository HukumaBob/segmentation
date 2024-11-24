from django.contrib import admin
from .models import (
    Sequences,
    ImageUpload,
    TagsCategory,
    Tag,
    Video,
    Dataset
    )

@admin.register(TagsCategory)
class TagsCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'tags_category')
    search_fields = ('tags_category',)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'category', 'name', 'description')
    search_fields = ('name',)    

@admin.register(ImageUpload)
class ImageUploadAdmin(admin.ModelAdmin):
    list_display = ('id', 'image', 'tag', 'uploaded_at')
    list_filter = ('tag', 'uploaded_at')
    search_fields = ('tag__name',)

@admin.register(Sequences)
class SequencesAdmin(admin.ModelAdmin):
    list_display = ('id', 
                    'video',
                    'features', 
                    'start_time',
                    'duration',
                    'fps',
                    'left_crop',
                    'right_crop',
                    'top_crop',
                    'bottom_crop'
                    )
    search_fields = ('video',)    

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'description')
    search_fields = ('title',)   

@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "description")
    search_fields = ("name",)    