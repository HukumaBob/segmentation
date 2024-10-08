import json
import os
import numpy as np
from PIL import Image
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from segmentation.models import FrameSequence, Sequences, Mask, ObjectClass, Points
import torch
from sam2.build_sam import build_sam2_video_predictor

# Инициализация предсказателя
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Use device: {device}")

if device.type == "cuda":
    torch.autocast("cuda", dtype=torch.bfloat16).__enter__()
    if torch.cuda.get_device_properties(0).major >= 8:
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True

# Пути к модели и конфигурации
sam2_checkpoint = "segment-anything-2/checkpoints/sam2_hiera_large.pt"
model_cfg = "sam2_hiera_l.yaml"

# Создаем предсказатель SAM2
predictor = build_sam2_video_predictor(model_cfg, sam2_checkpoint, device=device)

def edit_sequence(request, sequence_id):
    sequence = get_object_or_404(Sequences, id=sequence_id)
    frames = FrameSequence.objects.filter(sequences=sequence)
    video = sequence.video

    # Получаем все доступные теги для отображения в шаблоне
    tags = ObjectClass.objects.all()

    context = {
        'sequence': sequence,
        'frames': frames,
        'video': video,
        'tags': tags,  # Передаем список тегов в шаблон
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
            points = data.get('points')
            tag_id = data.get('tag_id')
            mask_color = data.get('mask_color', '#00FF00')  # Цвет маски из запроса или значение по умолчанию

            if frame_id is None or not points or tag_id is None:
                return JsonResponse({'error': 'Missing required parameters'}, status=400)

            # Поиск кадра и тега в базе данных
            frame = get_object_or_404(FrameSequence, id=frame_id)
            tag = get_object_or_404(ObjectClass, id=tag_id)

            # Получение размеров изображения
            image = Image.open(frame.frame_file.path).convert("RGB")
            frame_width, frame_height = image.size

            # Преобразуем точки в формат numpy
            clicked_points = np.array([[pt['x'], pt['y']] for pt in points], dtype=np.float32)
            clicked_labels = np.array([1 if pt['sign'] == '+' else 0 for pt in points], dtype=np.int32)

            if clicked_points.size == 0:
                return JsonResponse({'error': 'No points provided for segmentation'}, status=400)

            # Логируем пересчитанные точки для отладки
            print(f"Received points (transformed): {clicked_points}")
            print(f"Image size (server): {frame_width}x{frame_height}")

            # Определение директории кадра и создание директории "mask", если не существует
            frame_dir = os.path.dirname(frame.frame_file.path)
            mask_dir = os.path.join(frame_dir, "mask")
            os.makedirs(mask_dir, exist_ok=True)

            # Проверяем, существует ли маска для данного кадра и тега
            mask_record, created = Mask.objects.get_or_create(
                frame_sequence=frame,
                tag=tag,
                defaults={'mask_file': '', 'mask_color': mask_color}
            )

            # Инициализация SAM2 для работы с последовательностью кадров
            inference_state = predictor.init_state(video_path=frame_dir)

            # Сегментируем маску с помощью SAM2
            _, _, out_mask_logits = predictor.add_new_points_or_box(
                inference_state=inference_state,
                frame_idx=0,
                obj_id=1,
                points=clicked_points,
                labels=clicked_labels,
            )

            # Преобразование маски в изображение
            current_mask = (out_mask_logits[0] > 0.0).cpu().numpy()
            if len(current_mask.shape) > 2:
                current_mask = current_mask.squeeze()

            # Создание наложения маски
            mask_overlay = Image.fromarray((current_mask * 255).astype(np.uint8), mode='L')
            mask_image = Image.new("RGBA", (frame_width, frame_height))
            mask_image.paste((0, 255, 0, 128), (0, 0), mask_overlay)

            # Генерируем имя файла маски
            mask_filename = f"{os.path.splitext(os.path.basename(frame.frame_file.name))[0]}_mask_{frame_id}.png"
            mask_path = os.path.join(mask_dir, mask_filename)
            mask_image.save(mask_path)

            # Обновляем существующую маску или сохраняем новую
            mask_record.mask_file = mask_path
            mask_record.mask_color = mask_color
            mask_record.save()

            # Сохранение точек в модели Points (обновляем или создаем заново)
            Points.objects.filter(mask=mask_record).delete()  # Удаляем предыдущие точки
            for point in points:
                Points.objects.create(
                    mask=mask_record,
                    points_sign=point['sign'],
                    point_x=point['x'],
                    point_y=point['y']
                )

            # Формируем URL маски
            relative_mask_url = os.path.relpath(mask_path, settings.MEDIA_ROOT)
            relative_mask_url = f"{settings.MEDIA_URL}{relative_mask_url.replace(os.sep, '/')}"

            # Возвращаем относительный URL маски и цвет
            return JsonResponse({'mask_url': relative_mask_url, 'mask_color': mask_color})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)
