from django.contrib import admin
from .models import ImageUpload, ObjectClass

@admin.register(ObjectClass)
class ObjectClassAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description')
    search_fields = ('name',)

@admin.register(ImageUpload)
class ImageUploadAdmin(admin.ModelAdmin):
    list_display = ('id', 'image', 'object_class', 'uploaded_at')
    list_filter = ('object_class', 'uploaded_at')
    search_fields = ('object_class__name',)
