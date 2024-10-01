import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
import numpy as np
from PIL import Image
from segmentation.models import FrameSequence, Sequences, Mask, ObjectClass
from django.views.decorators.csrf import csrf_exempt
import os
from django.conf import settings


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
            data = json.loads(request.body)
            frame_id = data.get('frame_id')
            point_x = data.get('point_x')
            point_y = data.get('point_y')
            tag_id = data.get('tag_id')  # Получаем значение tag_id из запроса

            # Проверка обязательных параметров
            if frame_id is None or point_x is None or point_y is None or tag_id is None:
                return JsonResponse({'error': 'Missing required parameters'}, status=400)

            # Поиск кадра и тега в базе данных
            frame = get_object_or_404(FrameSequence, id=frame_id)
            tag = get_object_or_404(ObjectClass, id=tag_id)

            # Получаем оригинальные размеры изображения
            image = Image.open(frame.frame_file.path)
            frame_width, frame_height = image.size

            # Создание маски с прозрачным фоном и точкой выделения
            mask = np.zeros((frame_height, frame_width, 4), dtype=np.uint8)  # 4 канала: R, G, B, A
            mask[:, :, 3] = 0  # Устанавливаем прозрачность (A) на 0 — полностью прозрачный фон

            # Устанавливаем белую точку с непрозрачным фоном
            mask[point_y, point_x] = [255, 0, 0, 255]  # Красная точка (R, G, B, A)

            # Преобразование маски в изображение RGBA и сохранение
            mask_image = Image.fromarray(mask, mode='RGBA')
            mask_path = os.path.join(settings.MEDIA_ROOT, f'masks/mask_{frame_id}_{point_x}_{point_y}.png')
            os.makedirs(os.path.dirname(mask_path), exist_ok=True)
            mask_image.save(mask_path)

            # Создание объекта Mask и привязка к кадру и тегу
            mask_record = Mask.objects.create(
                frame_sequence=frame,
                mask_file=f'masks/mask_{frame_id}_{point_x}_{point_y}.png',
                tag=tag,
                point_x=point_x,
                point_y=point_y
            )

            # Возвращаем правильный URL маски
            return JsonResponse({'mask_url': mask_record.mask_file.url})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
        except Exception as e:
            print("Error occurred:", str(e))
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)
