from django.contrib import admin
from django.contrib import admin

from .models import (
    FrameSequence,
    Points,
    Mask,
    )


@admin.register(FrameSequence)
class FrameSequenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'sequences', 'frame_file')
    search_fields = ('sequences',)    

@admin.register(Mask)
class MaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'frame_sequence', 'mask_file', "tag")
    search_fields = ('tag',) 

@admin.register(Points)
class PointsAdmin(admin.ModelAdmin):
    list_display = ('id', 'mask', 'points_sign', 'point_x', 'point_y')
    search_fields = ('mask',)