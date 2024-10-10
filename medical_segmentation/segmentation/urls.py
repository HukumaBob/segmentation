from django.urls import path
from . import views

urlpatterns = [
    path('upload-multiple/', views.upload_multiple_images, name='upload_multiple_images'),
    path('upload-video/', views.upload_video, name='upload_video'),
    path('delete-video/', views.delete_video, name='delete_video'),
    path('create-frame-sequence/<str:video_id>/', views.create_frame_sequence, name='create_frame_sequence'),
    path('view-frame-sequence/<str:video_id>/', views.view_frame_sequence, name='view_frame_sequence'),
    path('sequence/<int:sequence_id>/delete/', views.delete_sequence, name='delete_sequence'),
    path('', views.image_list, name='image_list'),
]
