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
