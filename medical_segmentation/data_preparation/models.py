import os
import shutil
from django.conf import settings
from django.apps import apps
from django.db import models
from django.utils.translation import gettext_lazy as _
import logging
from django.db.models.signals import post_delete
from django.dispatch import receiver

# from segmentation.models import FrameSequence

class TagsCategory(models.Model):
    tags_category = models.CharField(_('Category of tag'), max_length=100)
    def __str__(self):
        return self.tags_category    

class Tag(models.Model):
    category = models.ForeignKey(TagsCategory, related_name='tags', on_delete=models.CASCADE, verbose_name=_("Tags category"))
    name = models.CharField(_('Name'), max_length=100)
    code = models.CharField(null=True, max_length=10, default='0000000000', blank=True, verbose_name=_('Code of tag'))
    description = models.TextField(_('Description'), blank=True, null=True)

    def __str__(self):
        return self.name

class ImageUpload(models.Model):
    image = models.ImageField(_('Image'), upload_to='uploads/')
    tag = models.ForeignKey(Tag, verbose_name=_('Tag'), on_delete=models.SET_NULL, null=True, blank=True)
    mask = models.ImageField(_('Mask'), upload_to='masks/', blank=True, null=True)
    uploaded_at = models.DateTimeField(_('Uploaded At'), auto_now_add=True)

    def delete(self, *args, **kwargs):
        if self.image and os.path.isfile(self.image.path):
            os.remove(self.image.path)
        if self.mask and os.path.isfile(self.mask.path):
            os.remove(self.mask.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Image {self.id} - {self.tag or _('No class')}"

logger = logging.getLogger(__name__)

class Video(models.Model):
    title = models.CharField(max_length=255, verbose_name=_("Video title"))
    description = models.TextField(blank=True, verbose_name=_("Video description"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    video_file = models.FileField(upload_to='videos/', unique=True, verbose_name=_("Video file"))

    def __str__(self):
        return f"Видео ({self.id}) {self.title}"

    def delete(self, *args, **kwargs):
        video_path = self.video_file.path  # Путь к видеофайлу
        video_dir = os.path.dirname(video_path)  # Директория видео

        # Путь к папке с кадрами
        video_name = os.path.splitext(os.path.basename(video_path))[0]  # Имя файла без расширения
        frames_dir = os.path.join('frames', video_name)

        # Удаляем видеофайл
        if self.video_file and os.path.isfile(video_path):
            try:
                os.remove(video_path)
                logger.info(f"Видео удалено: {video_path}")
            except Exception as e:
                logger.error(f"Ошибка при удалении видеофайла {video_path}: {e}")
        else:
            logger.warning(f"Файл для удаления не найден: {video_path}")

        # Удаляем папку с кадрами
        full_frames_dir = os.path.join(settings.MEDIA_ROOT, frames_dir)
        if os.path.isdir(full_frames_dir):
            try:
                shutil.rmtree(full_frames_dir)
                logger.info(f"Папка с кадрами удалена: {full_frames_dir}")
            except Exception as e:
                logger.error(f"Ошибка при удалении папки {full_frames_dir}: {e}")
        else:
            logger.warning(f"Папка с кадрами не найдена: {full_frames_dir}")

        # Вызов метода родительского класса для удаления записи из БД
        super().delete(*args, **kwargs)

        # Удаляем директорию видео, если она пуста
        try:
            if os.path.isdir(video_dir) and not os.listdir(video_dir):
                os.rmdir(video_dir)
                logger.info(f"Директория удалена: {video_dir}")
            else:
                logger.warning(f"Директория не пуста или не существует: {video_dir}")
        except Exception as e:
            logger.error(f"Ошибка при удалении директории {video_dir}: {e}")

class Sequences(models.Model):
    video = models.ForeignKey(
        Video,
        related_name='sequences',
        on_delete=models.CASCADE,
        verbose_name=_("Video"),
        null=True,
        blank=True
        )
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
        FrameSequence = apps.get_model('segmentation', 'FrameSequence')  # Динамическое получение модели
        frame_sequences = FrameSequence.objects.filter(sequences=self)
        for frame in frame_sequences:
            frame.delete()
        super().delete(*args, **kwargs)

class Dataset(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название датасета")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")

    def __str__(self):
        return self.name
