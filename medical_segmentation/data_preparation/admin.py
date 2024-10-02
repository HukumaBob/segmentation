from django.contrib import admin
from segmentation.models import Points

@admin.register(Points)
class PointsAdmin(admin.ModelAdmin):
    list_display = ('id', 'mask', 'points_sign', 'point_x', 'point_y')
    search_fields = ('mask',)