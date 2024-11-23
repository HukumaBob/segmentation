from django.urls import path
from . import views

app_name = 'data_preparation'
urlpatterns = [
    path('upload-multiple/', views.upload_multiple_images, name='upload_multiple_images'),
    path('frame-sequences/', views.frame_sequence_list, name='frame_sequence_list'),
    path('upload-video/', views.upload_video, name='upload_video'),
    path('get_videos/', views.get_videos, name='get_videos'),
    path('delete-video/', views.delete_video, name='delete_video'),
    path('create-frame-sequence/<str:video_id>/', views.create_frame_sequence, name='create_frame_sequence'),
    path('view-frame-sequence/<str:video_id>/', views.view_frame_sequence, name='view_frame_sequence'),
    path('sequence/<int:sequence_id>/delete/', views.delete_sequence, name='delete_sequence'),
    # path('', views.frame_sequence_list, name='frame_sequence_list'),
    path('', views.TagListView.as_view(), name='tag_list'),
    path('add/', views.TagCreateView.as_view(), name='tag_add'),
    path('<int:pk>/edit/', views.TagUpdateView.as_view(), name='tag_edit'),
    path('<int:pk>/delete/', views.TagDeleteView.as_view(), name='tag_delete'),    
]
