from django.urls import path
from . import views

urlpatterns = [
    path('upload-multiple/', views.upload_multiple_images, name='upload_multiple_images'),
    path('upload-video/', views.upload_video_and_extract_frames, name='upload_video_and_extract_frames'),
    path('frame-list/<str:video_id>/', views.frame_list, name='frame_list'),
    path('', views.image_list, name='image_list'),
]
