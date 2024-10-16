import json
import os
import numpy as np
from PIL import Image
from django.http import HttpResponseNotFound, JsonResponse
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from segmentation.models import FrameSequence, Sequences, Mask, Tag, Points
import torch
from sam2.build_sam import build_sam2_video_predictor

ALPHA = 128

def hex_to_rgba(hex_color, alpha=128):
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return (r, g, b, alpha)


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

@receiver(post_delete, sender=Mask)
def delete_mask_file(sender, instance, **kwargs):
    """Удаляем файл маски при удалении объекта Mask."""
    if instance.mask_file and os.path.isfile(instance.mask_file.path):
        os.remove(instance.mask_file.path)

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
            sequence_id = data.get('sequence_id')
            frame_id = int(data.get('frame_id'))
            points = data.get('points')
            tag_id = data.get('tag_id')
            mask_color = data.get('mask_color', '#00FF00')  # Цвет маски из запроса или значение по умолчанию

            if frame_id is None or not points or tag_id is None:
                return JsonResponse({'error': 'Missing required parameters'}, status=400)

            # Поиск кадра и тега в базе данных
            frame = get_object_or_404(FrameSequence, id=frame_id)
            tag = get_object_or_404(Tag, id=tag_id)
            sequence = get_object_or_404(Sequences, id=sequence_id)

            # Получение всех кадров для данной последовательности и сортировка по id
            frames = FrameSequence.objects.filter(sequences=sequence).order_by('id')
            if not frames.exists():
                return JsonResponse({'error': 'No frames found for the given sequence'}, status=404)

            # Печатаем все ID кадров в последовательности для отладки
            frame_ids = [frame.id for frame in frames]
            print(f"All frame IDs in sequence {sequence_id}: {frame_ids}")

            # Проверяем, принадлежит ли frame_id данной последовательности
            if frame_id not in frame_ids:
                return JsonResponse({
                    'error': f'Invalid frame ID {frame_id} for the selected sequence {sequence_id}.',
                    'valid_ids': frame_ids,
                    'received_id': frame_id
                }, status=400)
            
            
            # Создание словаря для сопоставления frame.id и индексов в последовательности
            frame_index_map = {frame.id: index for index, frame in enumerate(frames)}
            print(f"Frame index map: {frame_index_map}")

            # Определяем индекс текущего кадра в последовательности
            current_frame_index = frame_index_map[frame_id]
            print(f"Using frame {frame_id} with sequence index {current_frame_index}")            

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
                frame_idx=current_frame_index,
                obj_id=tag,
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
            mask_image.paste((hex_to_rgba(hex_color=mask_color, alpha=ALPHA)), (0, 0), mask_overlay)

            # Генерируем имя файла маски
            mask_filename = f"{os.path.splitext(os.path.basename(frame.frame_file.name))[0]}_mask_{frame_id}.png"

            mask_path = os.path.join(mask_dir, mask_filename)
            mask_image.save(mask_path)
            # Формируем URL маски
            relative_mask_url = os.path.relpath(mask_path, settings.MEDIA_ROOT)
            relative_mask_url = f"{relative_mask_url.replace(os.sep, '/')}"
            # Обновляем существующую маску или сохраняем новую
            mask_record.mask_file = relative_mask_url
            mask_record.mask_color = mask_color
            mask_record.save()
            relative_mask_url = f"{settings.MEDIA_URL}{relative_mask_url}"


            # Сохранение точек в модели Points (обновляем или создаем заново)
            Points.objects.filter(mask=mask_record).delete()  # Удаляем предыдущие точки
            for point in points:
                Points.objects.create(
                    mask=mask_record,
                    points_sign=point['sign'],
                    point_x=point['x'],
                    point_y=point['y']
                )


            # Возвращаем относительный URL маски и цвет
            return JsonResponse({'mask_url': relative_mask_url, 'mask_color': mask_color})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)

@csrf_exempt
def extrapolate_masks(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # Получаем данные из запроса и приводим current_frame_id к целому числу
            points = data.get('points')
            sequence_id = data.get('sequence_id')
            tag_id = data.get('tag_id')
            mask_color = data.get('mask_color', '#00FF00')
            current_frame_id = int(data.get('current_frame_id'))  # Приводим ID текущего кадра к типу int

            # Логируем входящие данные для отладки
            print(f"Received parameters: sequence_id={sequence_id}, tag_id={tag_id}, current_frame_id={current_frame_id}")

            if sequence_id is None or tag_id is None or current_frame_id is None:
                return JsonResponse({'error': 'Missing required parameters'}, status=400)

            # Поиск последовательности и тега в базе данных
            sequence = get_object_or_404(Sequences, id=sequence_id)
            tag = get_object_or_404(Tag, id=tag_id)

            # Получение всех кадров для данной последовательности и сортировка по id
            frames = FrameSequence.objects.filter(sequences=sequence).order_by('id')
            if not frames.exists():
                return JsonResponse({'error': 'No frames found for the given sequence'}, status=404)

            # Печатаем все ID кадров в последовательности для отладки
            frame_ids = [frame.id for frame in frames]
            print(f"All frame IDs in sequence {sequence_id}: {frame_ids}")

            # Проверяем, принадлежит ли current_frame_id данной последовательности
            if current_frame_id not in frame_ids:
                return JsonResponse({
                    'error': f'Invalid frame ID {current_frame_id} for the selected sequence {sequence_id}.',
                    'valid_ids': frame_ids,
                    'received_id': current_frame_id
                }, status=400)

            # Создание словаря для сопоставления frame.id и индексов в последовательности
            frame_index_map = {frame.id: index for index, frame in enumerate(frames)}
            print(f"Frame index map: {frame_index_map}")

            # Определяем индекс текущего кадра в последовательности
            current_frame_index = frame_index_map[current_frame_id]
            print(f"Using frame {current_frame_id} with sequence index {current_frame_index}")

            # Ищем текущий кадр по переданному ID
            current_frame = get_object_or_404(FrameSequence, id=current_frame_id)
            print(f"Current frame details: id={current_frame.id}, sequence={current_frame.sequences.id}, file={current_frame.frame_file.path}")

            # Проверяем, существует ли начальная маска для текущего кадра
            initial_mask = Mask.objects.filter(frame_sequence=current_frame, tag=tag).first()
            if not initial_mask:
                # Автоматически создаем начальную маску, если ее нет
                print(f"Initial mask not found for frame {current_frame_id}.")

            print(f"Points found for mask: {list(points)}")

            # Преобразуем точки в формат numpy
            clicked_points = np.array([[pt['x'], pt['y']] for pt in points], dtype=np.float32)
            clicked_labels = np.array([1 if pt['sign'] == '+' else 0 for pt in points], dtype=np.int32)
            
            print(f"Transformed points: {clicked_points}, labels: {clicked_labels}")

            if clicked_points.size == 0:
                return JsonResponse({'error': 'No points provided for segmentation'}, status=400)

            # Логируем пересчитанные точки для отладки
            print(f"Received initial points (transformed) from frame {current_frame_id}: {clicked_points}")

            # Инициализация предсказания для всего видео
            frame_dir = os.path.dirname(current_frame.frame_file.path)
            mask_dir = os.path.join(frame_dir, "mask")
            os.makedirs(mask_dir, exist_ok=True)

            inference_state = predictor.init_state(video_path=frame_dir)
            video_segments = {}

            print(f"Adding points to frame index {current_frame_index}")
            _, _, initial_out_mask_logits = predictor.add_new_points_or_box(
                inference_state=inference_state,
                frame_idx=current_frame_index,  # Используем текущий индекс в последовательности
                obj_id=tag,
                points=clicked_points,
                labels=clicked_labels,
            )

            print(f"Initial mask logits generated successfully for frame {current_frame_id}")

            # Экстраполяция на все кадры
            for out_frame_idx, out_obj_ids, out_mask_logits in predictor.propagate_in_video(inference_state):
                video_segments[out_frame_idx] = {
                    out_obj_id: (out_mask_logits[i] > 0.0).cpu().numpy()
                    for i, out_obj_id in enumerate(out_obj_ids)
                }

            # Сохранение сегментированных масок
            for frame in frames:
                frame_idx = frame_index_map[frame.id]  # Получаем индекс текущего кадра
                segments = video_segments.get(frame_idx, {})

                for obj_id, mask in segments.items():
                    if len(mask.shape) > 2:
                        mask = mask.squeeze()

                    # Создание наложения маски
                    mask_overlay = Image.fromarray((mask * 255).astype(np.uint8), mode='L')
                    frame_width, frame_height = mask_overlay.size
                    mask_image = Image.new("RGBA", (frame_width, frame_height))
                    mask_image.paste((hex_to_rgba(hex_color=mask_color, alpha=ALPHA)), (0, 0), mask_overlay)

                    # Генерация имени файла маски
                    mask_filename = f"{os.path.splitext(os.path.basename(frame.frame_file.name))[0]}_mask_{frame.id}_tag_{tag}.png"
                    mask_path = os.path.join(mask_dir, mask_filename)
                    mask_image.save(mask_path)
                    relative_mask_url = os.path.relpath(mask_path, settings.MEDIA_ROOT)
                    relative_mask_url = f"{relative_mask_url.replace(os.sep, '/')}"                    

                    # Обновляем или создаем новую запись маски в базе данных
                    mask_record, created = Mask.objects.get_or_create(
                        frame_sequence=frame,
                        tag=tag,
                        defaults={'mask_file': '', 'mask_color': mask_color}
                    )
                    mask_record.mask_file = relative_mask_url
                    mask_record.mask_color = mask_color
                    mask_record.save()

            return JsonResponse({'status': 'Extrapolation completed successfully'})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
        except Exception as e:
            print(f"Error occurred: {str(e)}")
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