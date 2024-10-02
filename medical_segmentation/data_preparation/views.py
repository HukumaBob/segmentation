import json
import os
import numpy as np
from PIL import Image
from random import randint
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from segmentation.models import FrameSequence, Sequences, Mask, ObjectClass, Points

# Путь для сохранения масок
MASK_DIR = os.path.join(settings.MEDIA_ROOT, "masks")
os.makedirs(MASK_DIR, exist_ok=True)

def edit_sequence(request, sequence_id):
    # Получаем последовательность по её ID
    sequence = get_object_or_404(Sequences, id=sequence_id)
    frames = FrameSequence.objects.filter(sequences=sequence)
    video = sequence.video

    context = {
        'sequence': sequence,
        'frames': frames,
        'video': video,
    }
    return render(request, 'data_preparation/edit_sequence.html', context)

@csrf_exempt
def get_image_size(request):
    if request.method == 'GET':
        frame_id = request.GET.get('frame_id')
        frame = get_object_or_404(FrameSequence, id=frame_id)

        # Открытие изображения и получение размеров
        image = Image.open(frame.frame_file.path)
        width, height = image.size

        return JsonResponse({'width': width, 'height': height})

    return JsonResponse({'error': 'Invalid request method'}, status=400)


@csrf_exempt
def generate_mask(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Получение данных из запроса
            frame_id = data.get('frame_id')
            points = data.get('points')  # points - список точек вида [{"x": 120, "y": 45, "sign": "+"}, ...]
            tag_id = data.get('tag_id')

            # Проверка параметров
            if frame_id is None or not points or tag_id is None:
                return JsonResponse({'error': 'Missing required parameters'}, status=400)

            # Поиск кадра и тега в базе данных
            frame = get_object_or_404(FrameSequence, id=frame_id)
            tag = get_object_or_404(ObjectClass, id=tag_id)

            # Получение размеров изображения
            image = Image.open(frame.frame_file.path)
            frame_width, frame_height = image.size

            # Создание пустой маски размером с кадр (с прозрачным фоном)
            mask = np.zeros((frame_height, frame_width, 4), dtype=np.uint8)
            mask[:, :, 3] = 0  # Устанавливаем прозрачность

            # Назначение случайного цвета для маски
            mask_color = f'#{randint(0, 255):02x}{randint(0, 255):02x}{randint(0, 255):02x}'
            print(f"Generated mask color: {mask_color}")

            # Установка точек на маске
            for point in points:
                x, y, sign = point['x'], point['y'], point['sign']
                if 0 <= x < frame_width and 0 <= y < frame_height:
                    if sign == '+':
                        color = [0, 255, 0, 255]  # Зеленая точка для положительных
                    else:
                        color = [255, 0, 0, 255]  # Красная точка для отрицательных
                    mask[y, x] = color
                else:
                    print(f"Skipping out-of-bounds point: X={x}, Y={y}")

            # Преобразование маски в изображение и сохранение
            mask_image = Image.fromarray(mask, mode='RGBA')
            mask_filename = f'mask_{frame_id}.png'
            mask_path = os.path.join(MASK_DIR, mask_filename)

            print(f"Saving mask to path: {mask_path}")
            mask_image.save(mask_path)

            # Создание объекта Mask и сохранение точки
            mask_record = Mask.objects.create(
                frame_sequence=frame,
                mask_file=f'masks/{mask_filename}',
                tag=tag,
                mask_color=mask_color  # Сохраняем цвет маски
            )

            # Сохранение точек в модели Points
            for point in points:
                Points.objects.create(
                    mask=mask_record,
                    points_sign=point['sign'],
                    point_x=point['x'],
                    point_y=point['y']
                )

            # Возвращаем URL маски и цвет
            return JsonResponse({'mask_url': mask_record.mask_file.url, 'mask_color': mask_color})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)
