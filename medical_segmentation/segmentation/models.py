import os
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_delete
from django.dispatch import receiver
from data_preparation.models import Sequences, Tag

class FrameSequence(models.Model):
    sequences = models.ForeignKey(Sequences, related_name='frame_sequences', on_delete=models.CASCADE, verbose_name=_("Sequences"))
    frame_file = models.ImageField(upload_to='frames/', verbose_name=_("Frame"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    height = models.IntegerField(null=True, blank=True, verbose_name=_("Height of frame"))
    width = models.IntegerField(null=True, blank=True, verbose_name=_("Width of frame"))

    def __str__(self):
        return f"Кадр из последовательности {self.sequences.id} (id:{self.id})"

class Mask(models.Model):
    STATUS_CHOICES = [
        ('pending', _("Pending")),
        ('processed', _("Processed")),
        ('failed', _("Failed")),
    ]    
    frame_sequence = models.ForeignKey(FrameSequence, related_name='masks', on_delete=models.CASCADE, verbose_name=_("Frame"))
    mask_file = models.ImageField(upload_to='mask/', verbose_name=_("Mask file"))
    mask_color = models.CharField(max_length=7, verbose_name=_("Mask Color"), null=True, blank=True)
    tag = models.ForeignKey(Tag, related_name='object_class', on_delete=models.CASCADE, verbose_name=_("Tag"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_("Status")
    )    

    def delete(self, *args, **kwargs):
        if self.mask_file and os.path.isfile(self.mask_file.path):
            os.remove(self.mask_file.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Маска для кадра {self.frame_sequence.id} ({self.tag})"
    
    @property
    def mask_url(self):
        return f"{settings.MEDIA_URL}{self.mask_file}"

@receiver(post_delete, sender=Mask)
def delete_mask_file(sender, instance, **kwargs):
    """Удаляем файл маски при удалении объекта Mask."""
    if instance.mask_file and os.path.isfile(instance.mask_file.path):
        os.remove(instance.mask_file.path)    

class Points(models.Model):
    POSITIVE = '+'
    NEGATIVE = '-'
    SIGN_CHOICES = [
        (POSITIVE, 'Positive'),
        (NEGATIVE, 'Negative')
    ]

    mask = models.ForeignKey(Mask, related_name='points', on_delete=models.CASCADE, verbose_name=_("Mask"))
    points_sign = models.CharField(max_length=1, choices=SIGN_CHOICES, verbose_name=_("Sign"))
    point_x = models.IntegerField()
    point_y = models.IntegerField()

    def __str__(self):
        return f"X:{self.point_x}, Y:{self.point_y}, Sign:{self.points_sign}"