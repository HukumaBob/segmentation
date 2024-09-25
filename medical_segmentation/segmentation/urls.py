from django.urls import path
from . import views

urlpatterns = [
    path('upload-multiple/', views.upload_multiple_images, name='upload_multiple_images'),
    path('upload-video/', views.upload_video, name='upload_video'),
    path('delete-video/', views.delete_video, name='delete_video'),
    path('create-frame-sequence/<str:video_filename>/', views.create_frame_sequence, name='create_frame_sequence'),
    path('frame-list/<str:video_id>/', views.frame_list, name='frame_list'),
    path('', views.image_list, name='image_list'),
]
