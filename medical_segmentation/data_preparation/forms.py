from django import forms

from segmentation.models import FrameSequence
from .models import Tag, Sequences, Video
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
        queryset=Tag.objects.all(),
        label=_("Object Class")
        )

class VideoForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ['id', 'title', 'description', 'video_file']

class SequenceForm(forms.ModelForm):
    class Meta:
        model = Sequences
        fields = ['id', 
                    'video',
                    'features', 
                    'start_time',
                    'duration',
                    'fps',
                    'left_crop',
                    'right_crop',
                    'top_crop',
                    'bottom_crop'
                    ]

class VideoUploadForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ['title', 'description', 'video_file']  # Включаем необходимые поля модели
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter video title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter video description'}),
            'video_file': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }

class FrameSequenceForm(forms.Form):
    features = forms.CharField(
        max_length=255,
        required=True,
        label="Sequence Features"
    )
    left_crop = forms.IntegerField(required=False, initial=0, label="Left Crop")
    right_crop = forms.IntegerField(required=False, initial=0, label="Right Crop")
    top_crop = forms.IntegerField(required=False, initial=0, label="Top Crop")
    bottom_crop = forms.IntegerField(required=False, initial=0, label="Bottom Crop")

        