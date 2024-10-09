import os
from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from PIL import Image
from django.utils.translation import gettext_lazy as _

class ObjectClass(models.Model):
    name = models.CharField(_('Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True, null=True)

    def __str__(self):
        return self.name

class ImageUpload(models.Model):
    image = models.ImageField(_('Image'), upload_to='uploads/')
    object_class = models.ForeignKey(ObjectClass, verbose_name=_('Object Class'), on_delete=models.SET_NULL, null=True, blank=True)
    mask = models.ImageField(_('Mask'), upload_to='masks/', blank=True, null=True)
    uploaded_at = models.DateTimeField(_('Uploaded At'), auto_now_add=True)

    def delete(self, *args, **kwargs):
        if self.image and os.path.isfile(self.image.path):
            os.remove(self.image.path)
        if self.mask and os.path.isfile(self.mask.path):
            os.remove(self.mask.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Image {self.id} - {self.object_class or _('No class')}"

class Video(models.Model):
    title = models.CharField(max_length=255, verbose_name=_("Video title"))
    description = models.TextField(blank=True, verbose_name=_("Video description"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    video_file = models.FileField(upload_to='videos/', unique=True, verbose_name=_("Video file"))

    def __str__(self):
        return f"Видео ({self.id}) {self.title}"

    def delete(self, *args, **kwargs):
        video_dir = os.path.dirname(self.video_file.path)
        if self.video_file and os.path.isfile(self.video_file.path):
            os.remove(self.video_file.path)
        super().delete(*args, **kwargs)
        # Удаляем всю директорию с кадрами и масками, если она существует
        if os.path.isdir(video_dir):
            os.rmdir(video_dir)

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

    def delete(self, *args, **kwargs):
        frame_sequences = FrameSequence.objects.filter(sequences=self)
        for frame in frame_sequences:
            frame.delete()
        super().delete(*args, **kwargs)

class FrameSequence(models.Model):
    sequences = models.ForeignKey(Sequences, related_name='frame_sequences', on_delete=models.CASCADE, verbose_name=_("Sequences"))
    frame_file = models.ImageField(upload_to='frames/', verbose_name=_("Frame"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    height = models.IntegerField(null=True, blank=True, verbose_name=_("Height of frame"))
    width = models.IntegerField(null=True, blank=True, verbose_name=_("Width of frame"))

    def save(self, *args, **kwargs):
        if not self.height or not self.width:
            image = Image.open(self.frame_file)
            self.width, self.height = image.size
        super(FrameSequence, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.frame_file and os.path.isfile(self.frame_file.path):
            os.remove(self.frame_file.path)
        # Удаление связанных масок
        masks = Mask.objects.filter(frame_sequence=self)
        for mask in masks:
            mask.delete()
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Кадр из последовательности {self.sequences.id} (id:{self.id})"

class Mask(models.Model):
    frame_sequence = models.ForeignKey(FrameSequence, related_name='masks', on_delete=models.CASCADE, verbose_name=_("Frame"))
    mask_file = models.ImageField(upload_to='mask/', verbose_name=_("Mask file"))
    mask_color = models.CharField(max_length=7, verbose_name=_("Mask Color"), null=True, blank=True)
    tag = models.ForeignKey(ObjectClass, related_name='object_class', on_delete=models.CASCADE, verbose_name=_("Tag"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    def delete(self, *args, **kwargs):
        if self.mask_file and os.path.isfile(self.mask_file.path):
            os.remove(self.mask_file.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Маска для кадра {self.frame_sequence.id} ({self.tag})"
    
    @property
    def mask_url(self):
        return f"{settings.MEDIA_URL}{self.mask_file}"

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
