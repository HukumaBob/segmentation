import json
import os
import numpy as np
from PIL import Image
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings

from .models import FrameSequence, Mask
from data_preparation.models import Sequences, Tag, TagsCategory
from .utils import (
    generate_mask_filename, 
    load_mask_as_array, 
    save_mask_image, 
    save_or_update_mask_record, 
    subtract_mask_from_mask, 
    subtract_new_masks_from_existing
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


def get_tags_by_category(request):
    category_id = request.GET.get('category_id')
    tags = Tag.objects.filter(category_id=category_id)

    tag_data = [{'id': tag.id, 'name': tag.name} for tag in tags]
    return JsonResponse(tag_data, safe=False)

def edit_sequence(request, sequence_id):
    sequence = get_object_or_404(Sequences, id=sequence_id)
    frames = FrameSequence.objects.filter(sequences=sequence).prefetch_related('masks')
    video = sequence.video

    # Получаем все категории и теги
    categories = TagsCategory.objects.all()
    tags = Tag.objects.all()

    context = {
        'sequence': sequence,
        'frames': frames,
        'video': video,
        'tags': tags,
        'categories': categories,  # Добавили категории
    }
    return render(request, 'segmentation/edit_sequence.html', context)
def get_masks(request):
    frame_id = request.GET.get('frame_id')
    frame = get_object_or_404(FrameSequence, id=frame_id)
    masks = Mask.objects.filter(frame_sequence=frame)

    mask_data = [{
        'id': mask.id,
        'mask_file': mask.mask_file.url,
        'tag': mask.tag.name if mask.tag else 'No tag',
        'id_tag': mask.tag.id if mask.id else 'No tag id',
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
            subtraction = data.get('subtraction', False)  # Получаем флаг вычитания

            # Получение объектов из базы данных
            frame = get_object_or_404(FrameSequence, id=frame_id)
            tag = get_object_or_404(Tag, id=tag_id)
            sequence = get_object_or_404(Sequences, id=sequence_id)

            # Получение всех кадров для данной последовательности и их сортировка
            frames = FrameSequence.objects.filter(sequences=sequence).order_by('id')
            frame_index_map = {f.id: idx for idx, f in enumerate(frames)}

            if frame_id not in frame_index_map:
                return JsonResponse({'error': 'Invalid frame ID for the given sequence'}, status=400)

            current_frame_index = frame_index_map[frame_id]
            print(f"Using frame {frame_id} with sequence index {current_frame_index}")

            image = Image.open(frame.frame_file.path).convert("RGB")
            frame_width, frame_height = image.size

            clicked_points = np.array([[pt['x'], pt['y']] for pt in points], dtype=np.float32)
            clicked_labels = np.array([1 if pt['sign'] == '+' else 0 for pt in points], dtype=np.int32)

            frame_dir = os.path.dirname(frame.frame_file.path)
            inference_state = predictor.init_state(video_path=frame_dir)

            _, _, out_mask_logits = predictor.add_new_points_or_box(
                inference_state=inference_state,
                frame_idx=current_frame_index,
                obj_id=tag,
                points=clicked_points,
                labels=clicked_labels,
            )

            current_mask = (out_mask_logits[0] > 0.0).cpu().numpy().squeeze()

            # Если subtraction=True, вычитаем текущую маску из существующих масок
            if subtraction:
                current_mask = subtract_new_masks_from_existing(frame, current_mask)

            mask_dir = os.path.join(frame_dir, "mask")
            os.makedirs(mask_dir, exist_ok=True)

            mask_filename = generate_mask_filename(frame, frame_id, tag_id)
            mask_path = os.path.join(mask_dir, mask_filename)
            save_mask_image(current_mask, mask_color, frame_width, frame_height, mask_path)

            mask_record = save_or_update_mask_record(frame, tag, mask_color, mask_path)

            return JsonResponse({
                'mask_url': f"{settings.MEDIA_URL}{mask_record.mask_file}",
                'mask_id': mask_record.id
            })

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
            subtraction = data.get('subtraction', False)  # Получаем флаг вычитания

            # Проверка обязательных параметров
            if not sequence_id or not tag_id or not current_frame_id:
                return JsonResponse({'error': 'Missing required parameters'}, status=400)

            # Получение объектов из базы данных
            sequence = get_object_or_404(Sequences, id=sequence_id)
            tag = get_object_or_404(Tag, id=tag_id)
            frames = FrameSequence.objects.filter(sequences=sequence).order_by('id')

            if not frames.exists():
                return JsonResponse({'error': 'No frames found for the given sequence'}, status=404)

            # Сопоставляем ID кадров с их индексами
            frame_index_map = {frame.id: idx for idx, frame in enumerate(frames)}
            current_frame_index = frame_index_map.get(current_frame_id)

            if current_frame_index is None:
                return JsonResponse({'error': 'Invalid frame ID for the sequence'}, status=400)

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

            # Получаем текущую маску
            # current_mask = (initial_out_mask_logits[0] > 0.0).cpu().numpy().squeeze()

            # Экстраполяция масок на все кадры
            for out_frame_idx, out_obj_ids, out_mask_logits in predictor.propagate_in_video(inference_state):
                # Извлекаем маски для каждого кадра и объекта
                video_segments[out_frame_idx] = {
                    obj_id: (out_mask_logits[i] > 0.0).cpu().numpy().squeeze()
                    for i, obj_id in enumerate(out_obj_ids)
                }

            # Сохранение и (при необходимости) вычитание масок для каждого кадра
            for frame in frames:
                frame_idx = frame_index_map[frame.id]
                segments = video_segments.get(frame_idx, {})  # Новые маски

                # Сохраняем новые маски без изменений
                for obj_id, new_mask_array in segments.items():
                    mask_dir = os.path.join(os.path.dirname(frame.frame_file.path), "mask")
                    os.makedirs(mask_dir, exist_ok=True)

                    mask_filename = generate_mask_filename(frame, frame.id, tag_id)
                    mask_path = os.path.join(mask_dir, mask_filename)

                    # Удаляем старую маску, если она уже существует
                    if os.path.exists(mask_path):
                        print(f"Deleting old mask: {mask_path}")
                        os.remove(mask_path)

                    # Сохраняем новую маску на диск
                    frame_width, frame_height = new_mask_array.shape[::-1]
                    print(f"Saving new mask at: {mask_path}")
                    save_mask_image(new_mask_array, mask_color, frame_width, frame_height, mask_path)

                    # Обновляем или создаём запись маски в БД
                    save_or_update_mask_record(frame, tag, mask_color, mask_path)

                # Если флаг subtraction включён, выполняем вычитание
                if subtraction:
                    print(f"Subtracting new masks from existing masks for frame {frame.id}")
                    existing_masks = Mask.objects.filter(frame_sequence=frame).exclude(tag=tag)  # Старые маски
                    subtract_new_masks_from_existing(existing_masks, segments)

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

@csrf_exempt  # Уберите, если используете CSRF-токены
@require_POST
def extract_masks(request):
    if request.method == 'POST':    
        try:
            data = json.loads(request.body)
            mask_id = data.get('mask_id')
            frame_id = data.get('frame_id')

            # Получаем переданную маску и её тег
            current_mask = Mask.objects.get(id=mask_id)
            current_tag = current_mask.tag

            # Находим кадр, связанный с переданной маской
            current_frame = FrameSequence.objects.get(id=frame_id)

            # Получаем все кадры из той же последовательности
            sequence_frames = FrameSequence.objects.filter(sequences=current_frame.sequences)

            # Проходим по каждому кадру из той же последовательности
            for frame in sequence_frames:
                print(f"Processing frame: {frame.id}")

                # Ищем маску в этом кадре с таким же тегом, что и у переданной маски
                same_tag_mask = Mask.objects.filter(frame_sequence=frame, tag=current_tag).first()

                if same_tag_mask:
                    print(f"Found mask with the same tag in frame {frame.id}: mask_id={same_tag_mask.id}")

                    # Загружаем маску с таким же тегом как бинарный массив
                    same_tag_mask_array = load_mask_as_array(same_tag_mask)

                    # Находим все остальные маски этого кадра (кроме той, что с тем же тегом)
                    other_masks = Mask.objects.filter(frame_sequence=frame).exclude(id=same_tag_mask.id)

                    # Вычитаем маску с тем же тегом из каждой другой маски
                    for mask in other_masks:
                        print(f"Subtracting mask {same_tag_mask.id} from mask {mask.id}")
                        subtract_mask_from_mask(mask, same_tag_mask_array)

            return JsonResponse({'message': 'Вычитание масок успешно выполнено.'}, status=200)

        except Mask.DoesNotExist:
            return JsonResponse({'error': 'Маска не найдена.'}, status=404)
        except FrameSequence.DoesNotExist:
            return JsonResponse({'error': 'Кадр не найден.'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=400)

