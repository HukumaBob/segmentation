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
    title = models.CharField(max_length=255, verbose_name=_("Video title"))
    description = models.TextField(blank=True, verbose_name=_("Video description"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    video_file = models.FileField(upload_to='videos/', unique=True, verbose_name=_("Video file"))

    def __str__(self):
        return f" Видео ({self.id}) {self.title}"


class Sequences(models.Model):
    video = models.ForeignKey(Video, related_name='sequences', on_delete=models.CASCADE, verbose_name=_("Video"))
    features = models.CharField(max_length=255, verbose_name=_("Frames features"))
    start_time = models.IntegerField(null=False, default=0, verbose_name=_("Start time"))
    duration = models.IntegerField(null=False, default=0, verbose_name=_("Duration of sequence"))
    fps = models.IntegerField(null=False, default=1, verbose_name=_("FPS"))
    left_crop = models.IntegerField(null=False, default=0, verbose_name=_("Left crop"))
    right_crop = models.IntegerField(null=False, default=0, verbose_name=_("Right crop"))
    top_crop = models.IntegerField(null=False, default=0, verbose_name=_("Top crop"))
    bottom_crop = models.IntegerField(null=False, default=0, verbose_name=_("Bottom crop"))

    def __str__(self):
        return f"Последовательность кадров {self.features}"    


class FrameSequence(models.Model):
    sequences = models.ForeignKey(Sequences, related_name='frame_sequences', on_delete=models.CASCADE, verbose_name=_("Sequences"))
    frame_file = models.ImageField(upload_to='frames/', verbose_name=_("Frame"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    def __str__(self):
        return f"Кадр из последовательности {self.sequences.id} (id:{self.id})"


class Mask(models.Model):
    frame_sequence = models.ForeignKey(FrameSequence, related_name='masks', on_delete=models.CASCADE, verbose_name=_("Frame"))
    mask_file = models.ImageField(upload_to='masks/', verbose_name=_("Mask file"))
    tag = models.ForeignKey(ObjectClass, related_name='object_class', on_delete=models.CASCADE, verbose_name=_("Tagк"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    point_x = models.IntegerField()
    point_y = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Маска для кадра {self.frame_sequence.id} ({self.tag})"
