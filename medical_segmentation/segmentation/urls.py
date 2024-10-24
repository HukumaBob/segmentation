from django.urls import path
from . import views

app_name = 'segmentation'
urlpatterns = [
    path('get-tags/', views.get_tags_by_category, name='get_tags_by_category'),
    path('sequence/<int:sequence_id>/edit/', views.edit_sequence, name='edit_sequence'),
    path('generate_mask/', views.generate_mask, name='generate_mask'),
    path('get_image_size/', views.get_image_size, name='get_image_size'),
    path('extrapolate_masks/', views.extrapolate_masks, name='extrapolate_masks'),
    path('get_masks/', views.get_masks, name='get_masks'),
    path('delete_frames/', views.delete_frames, name='delete_frames'),
    path('delete_mask/', views.delete_mask, name='delete_mask'),
    path('api/masks/extract/', views.extract_masks, name='extract_masks'),
]