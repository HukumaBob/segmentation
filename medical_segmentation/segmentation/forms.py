from django import forms
from .models import ObjectClass
from django.utils.translation import gettext_lazy as _

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result

class MultipleImageUploadForm(forms.Form):
    images = MultipleFileField(label=_("Images"))
    object_class = forms.ModelChoiceField(
        queryset=ObjectClass.objects.all(),
        label=_("Object Class")
        )

class VideoUploadForm(forms.Form):
    video = forms.FileField(widget=forms.ClearableFileInput(attrs={'id': 'id_video'}))
    start_time = forms.FloatField(label=_('Начало (в секундах)'), required=True, initial=0)
    duration = forms.FloatField(label=_('Продолжительность (в секундах)'), required=True, initial=5)
    fps = forms.IntegerField(label=_('Частота кадров (FPS)'), required=True, initial=1)
