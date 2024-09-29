from django.shortcuts import get_object_or_404, render

from segmentation.models import FrameSequence, Sequences

def edit_sequence(request, sequence_id):
    # Получаем последовательность по её ID
    sequence = get_object_or_404(Sequences, id=sequence_id)

    # Получаем все кадры, связанные с этой последовательностью
    frames = FrameSequence.objects.filter(sequences=sequence)

    # Получаем видео, связанное с этой последовательностью
    video = sequence.video

    # Передаем в шаблон саму последовательность, список кадров и объект видео
    context = {
        'sequence': sequence,
        'frames': frames,
        'video': video,
    }
    return render(request, 'data_preparation/edit_sequence.html', context)
