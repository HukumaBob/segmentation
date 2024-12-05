from django import forms

from segmentation.models import FrameSequence
from .models import Dataset, Procedure, Tag, Sequences, Video
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
    procedure = forms.ModelChoiceField(
        queryset=Procedure.objects.all(),
        label=_("Procedure")
        )    
    features = forms.CharField(
        max_length=255,
        required=True,
        label="Sequence Features"
    )
    start_time = forms.IntegerField(required=False, initial=0, label="Start time")
    duration = forms.IntegerField(required=False, initial=0, label="Duration")
    fps = forms.IntegerField(required=False, initial=0, label="FPS")
    left_crop = forms.IntegerField(required=False, initial=0, label="Left Crop")
    right_crop = forms.IntegerField(required=False, initial=0, label="Right Crop")
    top_crop = forms.IntegerField(required=False, initial=0, label="Top Crop")
    bottom_crop = forms.IntegerField(required=False, initial=0, label="Bottom Crop")
    width = forms.IntegerField(required=False, initial=0, label="Width")
    height = forms.IntegerField(required=False, initial=0, label="Height")

class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['category', 'name', 'code', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class DatasetSplitForm(forms.Form):
    dataset_name = forms.CharField(
        label="Название датасета",
        max_length=100,
        required=True,
        help_text="Уникальное название для сохранения датасета."
    )    
    dataset_description = forms.CharField(
        label="Описание датасета",
        max_length=255,
        required=False,
        help_text="Описание датасета."
    )        
    train_percentage = forms.IntegerField(
        label="Процент обучения",
        min_value=0,
        max_value=100,
        initial=80,
        help_text="Процент данных для обучения"
    )
    val_percentage = forms.IntegerField(
        label="Процент валидации",
        min_value=0,
        max_value=100,
        initial=10,
        help_text="Процент данных для валидации"
    )
    sequences = forms.ModelMultipleChoiceField(
        queryset=Sequences.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Выберите последовательности (Sequences)",
        help_text="Укажите последовательности, которые войдут в датасет."
    )

    def clean(self):
        cleaned_data = super().clean()
        train = cleaned_data.get("train_percentage", 0)
        val = cleaned_data.get("val_percentage", 0)

        # Вычисляем test_percentage
        test = max(0, 100 - train - val)
        cleaned_data["test_percentage"] = test

        # Проверяем, чтобы сумма train, val и test строго равнялась 100
        if train + val + test != 100:
            raise forms.ValidationError(
                "Сумма процентов обучения, валидации и тестирования должна быть равна 100."
            )
        return cleaned_data

    def clean_dataset_name(self):
        name = self.cleaned_data.get("dataset_name")
        if Dataset.objects.filter(name=name).exists():
            raise forms.ValidationError(f"Датасет с названием '{name}' уже существует.")
        return name
    
class DatasetTableForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ['name', 'description']
