import shutil
import uuid
import os
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST
from django.conf import settings
from django.db.models import Count

from utils.crop_frame import crop_frame
from .forms import FrameSequenceForm, VideoForm
from .models import ImageUpload, Video, Sequences
from segmentation.models import FrameSequence
from utils.ffmpeg_convert import extract_frames_from_video, convert_to_webm, save_webm
from django.http import JsonResponse
import logging
logger = logging.getLogger(__name__)

def image_list(request):
    if request.method == 'POST':
        if 'delete_selected' in request.POST:
            image_ids = request.POST.getlist('images')
            for image_id in image_ids:
                image = ImageUpload.objects.get(id=image_id)
                image.delete()
        elif 'delete_single' in request.POST:
            image_id = request.POST.get('delete_single')
            image = ImageUpload.objects.get(id=image_id)
            image.delete()
        return redirect('data_preparation:image_list')
    
    images = ImageUpload.objects.all()
    return render(request, 'data_preparation/image_list.html', {'images': images})

def upload_multiple_images(request):
    if request.method == 'POST':
        form = FrameSequenceForm(request.POST)
        if form.is_valid():
            # Получаем данные из формы
            features = form.cleaned_data['features']
            left_crop = form.cleaned_data['left_crop'] or 0
            right_crop = form.cleaned_data['right_crop'] or 0
            top_crop = form.cleaned_data['top_crop'] or 0
            bottom_crop = form.cleaned_data['bottom_crop'] or 0

            # Создаём новую последовательность
            sequence = Sequences.objects.create(
                features=features,
                left_crop=left_crop,
                right_crop=right_crop,
                top_crop=top_crop,
                bottom_crop=bottom_crop,
                start_time=0,  # можно заменить на данные, если нужно
                duration=0,    # можно заменить на данные, если нужно
                fps=1          # стандартное значение или заменить
            )

            # Обрабатываем множественные файлы
            files = request.FILES.getlist('images')
            for f in files:
                # Обрезаем изображение
                cropped_image = crop_frame(f, left_crop, top_crop, right_crop, bottom_crop)

                # Генерация уникального имени файла
                ext = f.name.split('.')[-1]
                new_filename = f"{uuid.uuid4()}.{ext}"

                frame_instance = FrameSequence(
                    sequences=sequence,
                    frame_file=None  # Временно None
                )
                frame_instance.frame_file.save(new_filename, cropped_image, save=False)  # Сохраняем файл
                frame_instance.save()

            return redirect('data_preparation:frame_sequence_list')
    else:
        form = FrameSequenceForm()

    return render(request, 'data_preparation/upload_multiple_images.html', {'form': form})

def frame_sequence_list(request):
    if request.method == 'POST':
        if 'delete_sequence' in request.POST:
            sequence_id = request.POST.get('delete_sequence')
            sequence = Sequences.objects.get(id=sequence_id)
            sequence.delete()  # Удаляет последовательность и связанные кадры через каскад
        elif 'edit_sequence' in request.POST:
            sequence_id = request.POST.get('edit_sequence')
            # Переход к странице редактирования (замените на ваш URL)
            return redirect('data_preparation:edit_sequence', sequence_id=sequence_id)
        return redirect('data_preparation:frame_sequence_list')

    # Группируем данные по последовательностям
    sequences = Sequences.objects.annotate(frame_count=Count('frame_sequences'))
    sequence_data = []
    for sequence in sequences:
        # Берём случайное изображение из связанной модели FrameSequence
        random_frame = sequence.frame_sequences.order_by('?').first()
        sequence_data.append({
            'sequence': sequence,
            'random_frame': random_frame,
        })

    return render(request, 'data_preparation/frame_sequence_list.html', {'sequence_data': sequence_data})

def upload_video(request):
    if request.method == 'POST':
        form = VideoForm(request.POST, request.FILES)
        if form.is_valid():
            video_instance = form.save()
            video_filename = video_instance.video_file.name
            video_path = os.path.join(settings.MEDIA_ROOT, video_filename)
            os.makedirs(os.path.dirname(video_path), exist_ok=True)

            # Проверяем, является ли видео в формате .webm
            if not video_filename.endswith('.webm'):
                # Конвертация в webm формат
                output_path = convert_to_webm(video_path, os.path.dirname(video_path))
                
                # Удаляем исходный файл после успешной конвертации
                if os.path.exists(output_path):
                    os.remove(video_path)
                else:
                    return JsonResponse({'error': 'Conversion to webm failed'}, status=500)
            else:
                output_path = video_path

            # Сохраняем webm видео в указанной директории
            saved_output_path = save_webm(output_path, os.path.dirname(output_path))

            # Обновляем путь к видеофайлу в записи модели
            video_instance.video_file.name = os.path.join('videos', os.path.basename(saved_output_path))
            video_instance.save()

            # Возвращаем URL видео для предпросмотра
            output_url = video_instance.video_file.url
            return JsonResponse({'file_url': output_url, 'video_id': video_instance.id})
        else:
            return JsonResponse({'error': 'Invalid form'}, status=400)

    # Отображение страницы загрузки видео с формой
    videos = Video.objects.all()
    return render(request, 'data_preparation/upload_video.html', {'form': VideoForm(), 'videos': videos})

def get_videos(request):
    """Возвращает список всех доступных видео."""
    videos = Video.objects.all().values('id', 'title', 'created_at', 'video_file')
    video_list = list(videos)
    return JsonResponse({'status': 'success', 'videos': video_list})

def delete_video(request):
    if request.method == 'POST':
        file_url = request.POST.get('file_url')
        if not file_url:
            return JsonResponse({'status': 'failed', 'error': 'File URL is missing'})
        
        # Извлечение имени файла из URL
        try:
            video_file_path = file_url.split('/media/')[1]
        except IndexError:
            return JsonResponse({'status': 'failed', 'error': 'Invalid file URL'})
        
        # Поиск объекта в базе данных
        video = Video.objects.filter(video_file=video_file_path).first()

        # Убедитесь, что видео существует и удалите его из базы данных и файловой системы
        if video:
            try:
                video.delete()  # Удаляем запись и связанные файлы
                return JsonResponse({'status': 'success'})
            except Exception as e:
                return JsonResponse({'status': 'failed', 'error': str(e)})
        else:
            return JsonResponse({'status': 'failed', 'error': 'Video does not exist'})
    return JsonResponse({'status': 'failed'})


def view_frame_sequence(request, video_id):
    logger.info(f"Fetching frame sequences for video: {video_id}")
    video = get_object_or_404(Video, id=video_id)

    # Извлекаем все последовательности, связанные с данным видео
    sequences = [
        {'id': seq.id, 'features': seq.features, 'start_time': seq.start_time, 'duration': seq.duration}
        for seq in video.sequences.all()
    ]

    # Проверяем, есть ли последовательности
    if not sequences:
        return JsonResponse({'status': 'success', 'sequences': [], 'message': 'No sequences found for this video.'})

    # Возвращаем список последовательностей и статус успеха
    return JsonResponse({'status': 'success', 'sequences': sequences})

def create_frame_sequence(request, video_id):
    logger.info(f"Create frame sequence called for video: {video_id}")
    video = get_object_or_404(Video, id=video_id)

    # Получаем параметры из запроса
    sequence_name = request.GET.get('sequence_name', 'Default Sequence Name')
    start_time = float(request.GET.get('start_time', 0))
    duration = float(request.GET.get('duration', 10))
    fps = int(request.GET.get('fps', 10))
    left_crop = int(request.GET.get('left_crop', 0))
    right_crop = int(request.GET.get('right_crop', 0))
    top_crop = int(request.GET.get('top_crop', 0))
    bottom_crop = int(request.GET.get('bottom_crop', 0))

    video_path = os.path.join(settings.MEDIA_ROOT, video.video_file.name)
    output_folder = os.path.join('frames', os.path.splitext(os.path.basename(video.video_file.name))[0], sequence_name)

    extracted_frames = extract_frames_from_video(
        video_path, start_time=start_time, duration=duration, 
        fps=fps, output_folder=os.path.join(settings.MEDIA_ROOT, output_folder),
        left_crop=left_crop, right_crop=right_crop,
        top_crop=top_crop, bottom_crop=bottom_crop
    )

    if not extracted_frames:
        return JsonResponse({'error': 'No frames were extracted'})

    # Создаем или получаем существующий объект Sequences
    sequence, created = Sequences.objects.get_or_create(
        video=video,
        features=sequence_name,
        start_time=start_time,
        duration=duration,
        fps=fps,
        left_crop=left_crop,
        right_crop=right_crop,
        top_crop=top_crop,
        bottom_crop=bottom_crop
    )

    # Сохраняем каждый кадр как объект FrameSequence
    for frame_path in extracted_frames:
        frame_str_path = os.path.join(output_folder, frame_path)
        FrameSequence.objects.create(
            sequences=sequence,
            frame_file=frame_str_path
        )

    # Подготовка данных для обновления списка последовательностей на клиенте
    sequences = [
        {'id': seq.id, 'features': seq.features, 'start_time':seq.start_time, 'duration':seq.duration}
        for seq in video.sequences.all()
    ]

    # Возвращаем обновленные данные о последовательностях и статус успеха
    return JsonResponse({'status': 'success', 'sequences': sequences})

@require_POST
def delete_sequence(request, sequence_id):
    try:
        # Находим последовательность
        sequence = get_object_or_404(Sequences, id=sequence_id)
        video = sequence.video

        # Удаляем связанные кадры и их директорию с диска
        delete_frames_directory(sequence)

        # Удаляем последовательность из базы данных
        sequence.delete()

        # Возвращаем обновленные последовательности для данного видео
        sequences = [
            {'id': seq.id, 'features': seq.features, 'start_time': seq.start_time, 'duration': seq.duration}
            for seq in video.sequences.all()
        ]
        return JsonResponse({'status': 'success', 'sequences': sequences})
    except Exception as e:
        return JsonResponse({'status': 'failed', 'error': str(e)})

def delete_frames_directory(sequence):
    """
    Удаляет директорию, содержащую все кадры данной последовательности.
    """
    # Находим все кадры, связанные с данной последовательностью
    frames = FrameSequence.objects.filter(sequences=sequence)

    # Проверяем путь к первому кадру, чтобы найти директорию
    if frames.exists():
        first_frame_path = frames.first().frame_file.path
        frame_dir = os.path.dirname(first_frame_path)

        # Удаляем директорию, если она существует
        if os.path.isdir(frame_dir):
            try:
                shutil.rmtree(frame_dir)
                print(f"Удалена директория: {frame_dir}")
            except Exception as e:
                print(f"Ошибка при удалении директории {frame_dir}: {e}")
        else:
            print(f"Директория не найдена: {frame_dir}")
    else:
        print("Кадры для удаления не найдены.")

    # Удаляем все объекты FrameSequence для данной последовательности
    frames.delete()
