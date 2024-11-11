from django.contrib import admin
from .models import NeuralNetworkVersion


@admin.register(NeuralNetworkVersion)
class NeuralNetworkVersioneAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'version_number',
        'description',
        'model_file',
        'created_at',
        'training_parameters',
        'accuracy'
        )
    search_fields = ('name',)  