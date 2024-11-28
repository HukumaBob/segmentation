from django.urls import path
from . import views

app_name = 'nettrain'
urlpatterns = [
    path('start_training/', views.start_training_view, name='start_training'),
    path('delete-model/<int:model_id>/', views.delete_model, name='delete-model'),
    path('download-model/<int:model_id>/', views.download_model, name='download-model'),
]