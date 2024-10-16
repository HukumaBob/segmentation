import json
import os
import numpy as np
from PIL import Image
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from segmentation.models import FrameSequence, Sequences, Mask, Tag, Points
from .utils import (
    generate_mask_filename, save_mask_image, save_or_update_mask_record
)
import torch
from sam2.build_sam import build_sam2_video_predictor

ALPHA = 128

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
    tags = Tag.objects.all()

    context = {
        'sequence': sequence,
        'frames': frames,
        'video': video,
        'tags': tags,  # Передаем список тегов в шаблон
    }
    return render(request, 'data_preparation/edit_sequence.html', context)

def get_masks(request):
    frame_id = request.GET.get('frame_id')
    frame = get_object_or_404(FrameSequence, id=frame_id)
    masks = Mask.objects.filter(frame_sequence=frame)

    mask_data = [{
        'id': mask.id,
        'mask_file': mask.mask_file.url,
        'tag': mask.tag.name if mask.tag else 'No tag',
        'color': mask.mask_color
    } for mask in masks]

    return JsonResponse(mask_data, safe=False)

@csrf_exempt
def delete_mask(request):
    mask_id = request.GET.get('mask_id')  # Получаем ID маски
    delete_all = request.GET.get('delete_all') == 'true'  # Проверяем флаг delete_all

    if not mask_id:
        return HttpResponseNotFound("Mask ID not provided.")

    # Пытаемся получить маску
    mask = get_object_or_404(Mask, id=mask_id)

    if delete_all:
        # Удаляем все маски с таким же тегом и ID >= текущего
        masks_to_delete = Mask.objects.filter(tag=mask.tag, id__gte=mask.id)
        deleted_ids = list(masks_to_delete.values_list('id', flat=True))  # Сохраняем ID удалённых масок
        masks_to_delete.delete()  # Удаляем маски
    else:
        # Удаляем только одну маску
        deleted_ids = [mask.id]
        mask.delete()

    return JsonResponse({
        'status': 'success',
        'deleted_ids': deleted_ids,
        'message': f'Deleted {len(deleted_ids)} masks.'
    }, status=200)

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

            sequence_id = data.get('sequence_id')
            frame_id = int(data.get('frame_id'))
            points = data.get('points')
            tag_id = data.get('tag_id')
            mask_color = data.get('mask_color', '#00FF00')

            # Получение объектов из базы данных
            frame = get_object_or_404(FrameSequence, id=frame_id)
            tag = get_object_or_404(Tag, id=tag_id)
            sequence = get_object_or_404(Sequences, id=sequence_id)

            # Получение всех кадров для данной последовательности и их сортировка
            frames = FrameSequence.objects.filter(sequences=sequence).order_by('id')

            # Создаём словарь для сопоставления frame.id с индексами
            frame_index_map = {f.id: idx for idx, f in enumerate(frames)}

            if frame_id not in frame_index_map:
                return JsonResponse({'error': 'Invalid frame ID for the given sequence'}, status=400)

            # Получаем индекс текущего кадра в последовательности
            current_frame_index = frame_index_map[frame_id]
            print(f"Using frame {frame_id} with sequence index {current_frame_index}")

            # Получаем размеры изображения
            image = Image.open(frame.frame_file.path).convert("RGB")
            frame_width, frame_height = image.size

            # Преобразуем точки в numpy-формат
            clicked_points = np.array([[pt['x'], pt['y']] for pt in points], dtype=np.float32)
            clicked_labels = np.array([1 if pt['sign'] == '+' else 0 for pt in points], dtype=np.int32)

            # Инициализация предсказания
            frame_dir = os.path.dirname(frame.frame_file.path)
            inference_state = predictor.init_state(video_path=frame_dir)

            # Предсказание с использованием текущего индекса кадра
            _, _, out_mask_logits = predictor.add_new_points_or_box(
                inference_state=inference_state,
                frame_idx=current_frame_index,  # Используем правильный индекс кадра
                obj_id=tag,
                points=clicked_points,
                labels=clicked_labels,
            )

            current_mask = (out_mask_logits[0] > 0.0).cpu().numpy().squeeze()

            # Сохранение маски
            mask_dir = os.path.join(frame_dir, "mask")
            os.makedirs(mask_dir, exist_ok=True)

            mask_filename = generate_mask_filename(frame, frame_id, tag_id)
            mask_path = os.path.join(mask_dir, mask_filename)
            save_mask_image(current_mask, mask_color, frame_width, frame_height, mask_path)

            # Сохранение или обновление записи маски в БД
            mask_record = save_or_update_mask_record(frame, tag, mask_color, mask_path)

            return JsonResponse({'mask_url': f"{settings.MEDIA_URL}{mask_record.mask_file}"})

        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)

@csrf_exempt
def extrapolate_masks(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # Получение параметров из запроса
            sequence_id = data.get('sequence_id')
            tag_id = data.get('tag_id')
            current_frame_id = int(data.get('current_frame_id'))
            mask_color = data.get('mask_color', '#00FF00')
            points = data.get('points')

            # Проверка обязательных параметров
            if not sequence_id or not tag_id or not current_frame_id:
                return JsonResponse({'error': 'Missing required parameters'}, status=400)

            # Получение объектов из базы данных
            sequence = get_object_or_404(Sequences, id=sequence_id)
            tag = get_object_or_404(Tag, id=tag_id)
            frames = FrameSequence.objects.filter(sequences=sequence).order_by('id')

            if not frames.exists():
                return JsonResponse({'error': 'No frames found for the given sequence'}, status=404)

            # Сопоставление frame.id с индексами в последовательности
            frame_index_map = {frame.id: idx for idx, frame in enumerate(frames)}
            if current_frame_id not in frame_index_map:
                return JsonResponse({'error': 'Invalid frame ID for the sequence'}, status=400)

            current_frame_index = frame_index_map[current_frame_id]
            print(f"Using frame {current_frame_id} with index {current_frame_index}")

            # Преобразование точек в numpy
            clicked_points = np.array([[pt['x'], pt['y']] for pt in points], dtype=np.float32)
            clicked_labels = np.array([1 if pt['sign'] == '+' else 0 for pt in points], dtype=np.int32)

            # Инициализация предсказания для последовательности
            frame_dir = os.path.dirname(frames[0].frame_file.path)
            inference_state = predictor.init_state(video_path=frame_dir)
            video_segments = {}

            print(f"Adding points to frame index {current_frame_index}")
            _, _, initial_out_mask_logits = predictor.add_new_points_or_box(
                inference_state=inference_state,
                frame_idx=current_frame_index,
                obj_id=tag,
                points=clicked_points,
                labels=clicked_labels,
            )

            print(f"Initial mask generated successfully for frame {current_frame_id}")

            # Экстраполяция масок на все кадры
            for out_frame_idx, out_obj_ids, out_mask_logits in predictor.propagate_in_video(inference_state):
                video_segments[out_frame_idx] = {
                    obj_id: (out_mask_logits[i] > 0.0).cpu().numpy().squeeze()
                    for i, obj_id in enumerate(out_obj_ids)
                }

            # Сохранение масок для всех кадров
            for frame in frames:
                frame_idx = frame_index_map[frame.id]
                segments = video_segments.get(frame_idx, {})

                for obj_id, mask_array in segments.items():
                    # Путь для сохранения маски
                    mask_dir = os.path.join(os.path.dirname(frame.frame_file.path), "mask")
                    os.makedirs(mask_dir, exist_ok=True)

                    mask_filename = generate_mask_filename(frame, frame.id, tag_id)
                    mask_path = os.path.join(mask_dir, mask_filename)

                    # Получение размеров кадра
                    frame_width, frame_height = mask_array.shape[::-1]
                    save_mask_image(mask_array, mask_color, frame_width, frame_height, mask_path)

                    # Сохранение маски в БД
                    save_or_update_mask_record(frame, tag, mask_color, mask_path)

            return JsonResponse({'status': 'Extrapolation completed successfully'})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
        except Exception as e:
            print(f"Error occurred: {e}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)


@csrf_exempt  # Временно отключаем CSRF-проверку для тестирования
def delete_frames(request):
    """Удаляет выбранные кадры и их маски из базы данных и файловой системы."""
    if request.method != 'POST':
        return JsonResponse({'status': 'failed', 'error': 'Only POST requests are allowed.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))  # Загружаем JSON-данные
        frame_ids = data.get('frame_ids', [])

        if not frame_ids:
            return JsonResponse({'status': 'failed', 'error': 'No frames selected.'}, status=400)

        frames = FrameSequence.objects.filter(id__in=frame_ids)

        # Удаляем маски и файлы кадров
        for frame in frames:
            delete_masks_for_frame(frame)  # Удаляем все маски для кадра

            if frame.frame_file and os.path.isfile(frame.frame_file.path):
                os.remove(frame.frame_file.path)  # Удаляем файл кадра с диска

        # Удаляем кадры из базы данных
        frames.delete()

        return JsonResponse({'status': 'success'}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'failed', 'error': 'Invalid JSON data.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'failed', 'error': str(e)}, status=500)

def delete_masks_for_frame(frame):
    """Удаляет все маски для данного кадра, включая файлы."""
    masks = frame.masks.all()  # Получаем все маски, связанные с кадром
    for mask in masks:
        mask.delete()  # Используем метод delete(), чтобы гарантировать удаление файла