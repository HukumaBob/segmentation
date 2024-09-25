from django.contrib import admin
from .models import (
    FrameSequence,
    ImageUpload,
    Mask,
    ObjectClass,
    Video,
    )

@admin.register(ObjectClass)
class ObjectClassAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description')
    search_fields = ('name',)

@admin.register(ImageUpload)
class ImageUploadAdmin(admin.ModelAdmin):
    list_display = ('id', 'image', 'object_class', 'uploaded_at')
    list_filter = ('object_class', 'uploaded_at')
    search_fields = ('object_class__name',)

@admin.register(FrameSequence)
class FrameSequenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'video', 'frame_file')
    search_fields = ('video',)    

@admin.register(Mask)
class MaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'frame_sequence', 'mask_file', "tag")
    search_fields = ('tag',) 

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'description')
    search_fields = ('title',)   