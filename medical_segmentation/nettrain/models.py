from django.db import models
from django.utils.translation import gettext_lazy as _

class NeuralNetworkVersion(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name=_("Model Name")
    )
    version_number = models.CharField(
        max_length=20,
        verbose_name=_("Version Number")
    )
    description = models.CharField(
        max_length=255,
        verbose_name=_("Description"),
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at")
    )
    model_file = models.FileField(
        upload_to='models/',
        verbose_name=_("Model File"),
        null=True,
        blank=True
    )
    training_parameters = models.JSONField(
        verbose_name=_("Training Parameters"),
        null=True,
        blank=True
    )    
    training_tags = models.JSONField(
        verbose_name=_("Training Tags"),
        null=True,
        blank=True
    )
    accuracy = models.FloatField(
        verbose_name=_("Model Accuracy"),
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.name} - Версия {self.version_number} (Точность: {self.accuracy})"