# segmentation/forms.py
from django import forms
from segmentation.models import Mask, FrameSequence, Tag, Points, Sequences

class MaskForm(forms.ModelForm):
    class Meta:
        model = Mask
        fields = ['frame_sequence', 'tag', 'mask_file', 'mask_color']

    def clean(self):
        """Проверяем, что маска соответствует кадру и тегу."""
        cleaned_data = super().clean()
        frame_sequence = cleaned_data.get("frame_sequence")
        tag = cleaned_data.get("tag")

        if not frame_sequence or not tag:
            raise forms.ValidationError("Кадр и тег обязательны для маски.")

        return cleaned_data


class PointsForm(forms.ModelForm):
    class Meta:
        model = Points
        fields = ['mask', 'points_sign', 'point_x', 'point_y']


class FrameDeletionForm(forms.Form):
    frame_ids = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=True,
        error_messages={'required': 'Выберите хотя бы один кадр для удаления.'},
    )

    def __init__(self, *args, **kwargs):
        frames = kwargs.pop('frames', None)
        super().__init__(*args, **kwargs)
        if frames:
            self.fields['frame_ids'].choices = [(frame.id, str(frame)) for frame in frames]
