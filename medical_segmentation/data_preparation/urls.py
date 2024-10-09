from django.urls import path
from . import views

urlpatterns = [
    path('sequence/<int:sequence_id>/edit/', views.edit_sequence, name='edit_sequence'),
    path('generate_mask/', views.generate_mask, name='generate_mask'),
    path('get_image_size/', views.get_image_size, name='get_image_size'),
    path('extrapolate_masks/', views.extrapolate_masks, name='extrapolate_masks'),
]
