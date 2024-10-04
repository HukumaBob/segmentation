import json
import os
import numpy as np
from PIL import Image, ImageDraw
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

# Путь для сохранения масок
MASK_DIR = os.path.join(settings.MEDIA_ROOT, "masks")
os.makedirs(MASK_DIR, exist_ok=True)

def edit_sequence(request, sequence_id):
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
            image = Image.open(frame.frame_file.path).convert("RGB")  # Убедитесь, что изображение в формате RGB
            frame_width, frame_height = image.size

            # Преобразуем точки в формат numpy
            clicked_points = np.array([[pt['x'], pt['y']] for pt in points], dtype=np.float32)
            clicked_labels = np.array([1 if pt['sign'] == '+' else 0 for pt in points], dtype=np.int32)

            # Проверка наличия точек
            if clicked_points.size == 0:
                return JsonResponse({'error': 'No points provided for segmentation'}, status=400)

            # Инициализация состояния SAM2 для работы с последовательностью кадров
            video_sequence_dir = MASK_DIR  # Директория для последовательности кадров
            os.makedirs(video_sequence_dir, exist_ok=True)

            # Сохранение кадра в директорию последовательности
            frame_filename = os.path.basename(frame.frame_file.name)
            frame_path = os.path.join(video_sequence_dir, frame_filename)
            image.save(frame_path)

            # Инициализация SAM2 для работы с последовательностью
            inference_state = predictor.init_state(video_path=video_sequence_dir)

            # Шаг 3. Сегментируем маску с помощью SAM2 с заданными точками
            print('Сегментируем маску с помощью SAM2')
            
            # Убедитесь, что точки имеют размерность (N, 2), а метки - (N,)
            print(f"clicked_points.shape: {clicked_points.shape}, clicked_labels.shape: {clicked_labels.shape}")

            # Сегментация
            _, out_obj_ids, out_mask_logits = predictor.add_new_points_or_box(
                inference_state=inference_state,
                frame_idx=0,  # Индекс первого кадра
                obj_id=1,  # ID объекта для сегментации
                points=clicked_points,
                labels=clicked_labels,
            )

            # Преобразование маски в изображение
            current_mask = (out_mask_logits[0] > 0.0).cpu().numpy()
            if len(current_mask.shape) > 2:
                current_mask = current_mask.squeeze()  # Убираем лишние оси, если они есть

            # Создание наложения маски
            mask_overlay = Image.fromarray((current_mask * 255).astype(np.uint8), mode='L')
            mask_image = Image.new("RGBA", (frame_width, frame_height))
            mask_image.paste((0, 255, 0, 128), (0, 0), mask_overlay)  # Полупрозрачная маска зеленого цвета

            # # Наложение точек на сегментированную маску
            # draw = ImageDraw.Draw(mask_image)
            # for point in points:
            #     x, y, sign = point['x'], point['y'], point['sign']
            #     color = (0, 255, 0, 255) if sign == '+' else (255, 0, 0, 255)
            #     draw.ellipse((x-3, y-3, x+3, y+3), fill=color)

            # Сохранение результирующей маски
            mask_filename = f'mask_{frame_id}.png'
            mask_path = os.path.join(MASK_DIR, mask_filename)
            mask_image.save(mask_path)

            # Создание объекта Mask и сохранение точки
            mask_record = Mask.objects.create(
                frame_sequence=frame,
                mask_file=f'masks/{mask_filename}',
                tag=tag,
                mask_color="#00FF00"  # Зеленый цвет для новой маски
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
            return JsonResponse({'mask_url': mask_record.mask_file.url, 'mask_color': "#00FF00"})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)
