import os
from django.db import models
from django.utils.translation import gettext_lazy as _

class ObjectClass(models.Model):
    name = models.CharField(_('Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True, null=True)

    def __str__(self):
        return self.name

class ImageUpload(models.Model):
    image = models.ImageField(_('Image'), upload_to='uploads/')
    object_class = models.ForeignKey(
        ObjectClass, verbose_name=_('Object Class'),
        on_delete=models.SET_NULL, null=True, blank=True
        )
    mask = models.ImageField(
        _('Mask'), upload_to='masks/', blank=True, null=True
        )
    uploaded_at = models.DateTimeField(
        _('Uploaded At'), auto_now_add=True
        )
    def delete(self, *args, **kwargs):
        # Удаление файла изображения перед удалением записи
        if self.image:
            if os.path.isfile(self.image.path):
                os.remove(self.image.path)
        super().delete(*args, **kwargs)    

    def __str__(self):
        return f"Image {self.id} - {self.object_class or _('No class')}"


class Video(models.Model):
    title = models.CharField(max_length=255, verbose_name="Название видео")
    description = models.TextField(blank=True, verbose_name="Описание видео")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    video_file = models.FileField(upload_to='videos/', verbose_name="Файл видео")

    def __str__(self):
        return self.title


class FrameSequence(models.Model):
    video = models.ForeignKey(Video, related_name='frame_sequences', on_delete=models.CASCADE, verbose_name="Видео")
    frame_file = models.ImageField(upload_to='frames/', verbose_name="Кадр")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return f"Кадр из {self.video.title} ({self.id})"


class Mask(models.Model):
    frame_sequence = models.ForeignKey(FrameSequence, related_name='masks', on_delete=models.CASCADE, verbose_name="Кадр")
    mask_file = models.ImageField(upload_to='masks/', verbose_name="Файл маски")
    tag = models.ForeignKey(ObjectClass, related_name='object_class', on_delete=models.CASCADE, verbose_name="Ярлык")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return f"Маска для кадра {self.frame_sequence.id} ({self.tag})"
