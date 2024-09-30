import json
from django.shortcuts import get_object_or_404, render
from segmentation.models import FrameSequence, Sequences, Mask
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os

# Путь для сохранения масок
MASK_DIR = "media/masks"
os.makedirs(MASK_DIR, exist_ok=True)

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


@csrf_exempt
def generate_mask(request):
    if request.method == 'POST':
        try:
            # Получение данных из запроса
            data = json.loads(request.body)
            frame_id = data['frame_id']
            point_x = data['point_x']
            point_y = data['point_y']

            # Поиск кадра в базе данных
            frame = get_object_or_404(FrameSequence, id=frame_id)

            # Генерация маски с помощью SAM2
            mask_image = generate_mask(frame.frame_file.path, (point_x, point_y))

            # Сохранение маски на диск
            mask_filename = f'mask_{frame_id}_{point_x}_{point_y}.png'
            mask_path = os.path.join(MASK_DIR, mask_filename)
            mask_image.save(mask_path)

            # Создание записи о маске в базе данных
            mask_record = Mask.objects.create(
                frame=frame,
                mask_file=mask_path,
                point_x=point_x,
                point_y=point_y,
            )

            # Возвращаем URL сохраненной маски
            return JsonResponse({'mask_url': mask_record.mask_file.url})
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)
