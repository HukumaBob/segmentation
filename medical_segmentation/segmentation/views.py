import uuid
import os
from django.shortcuts import get_object_or_404, render, redirect
from django.conf import settings
from .forms import MultipleImageUploadForm, VideoForm
from .models import FrameSequence, ImageUpload, Video
from utils.ffmpeg_convert import extract_frames_from_video, convert_to_webm, save_webm
from django.http import JsonResponse

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
        return redirect('image_list')
    
    images = ImageUpload.objects.all()
    return render(request, 'segmentation/image_list.html', {'images': images})

def upload_multiple_images(request):
    if request.method == 'POST':
        form = MultipleImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            files = request.FILES.getlist('images')
            object_class = form.cleaned_data['object_class']
            
            for f in files:
                # Генерация нового имени файла с помощью UUID
                ext = f.name.split('.')[-1]  # Получаем расширение файла
                new_filename = f"{uuid.uuid4()}.{ext}"  # Генерируем уникальное имя

                # Создаем экземпляр ImageUpload и сохраняем его
                image_instance = ImageUpload(
                    image=f,  # передаем файл, который позже будет сохранен с новым именем
                    object_class=object_class
                )
                image_instance.image.name = new_filename  # Устанавливаем новое имя файла
                image_instance.save()  # Сохраняем экземпляр модели в БД
            
            return redirect('image_list')
    else:
        form = MultipleImageUploadForm()

    return render(request, 'segmentation/upload_multiple_images.html', {'form': form})

def upload_video(request):
    if request.method == 'POST':
        form = VideoForm(request.POST, request.FILES)
        if form.is_valid():
            video_instance = form.save(commit=False)
            video_file = request.FILES['video_file']
            video_filename = video_file.name

            # Сохраняем исходное видео
            video_instance.video_file = video_file
            video_instance.save()

            video_path = os.path.join(settings.MEDIA_ROOT, 'videos', video_filename)
            os.makedirs(os.path.dirname(video_path), exist_ok=True)

            # Обрабатываем видео
            if not video_filename.endswith('.webm'):
                # Конвертируем в webm
                output_path = convert_to_webm(video_path, os.path.dirname(video_path))
                
                # Удаляем исходный файл, если конвертация прошла успешно
                if os.path.exists(video_path):
                    os.remove(video_path)
            else:
                output_path = video_path

            # Сохраняем видео в новом формате
            saved_output_path = save_webm(output_path, os.path.dirname(output_path))
            
            # Обновляем путь к конвертированному видео в модели
            video_instance.video_file.name = os.path.join('videos', os.path.basename(saved_output_path))
            video_instance.save()

            # Возвращаем URL видео для предпросмотра
            output_url = os.path.join(settings.MEDIA_URL, 'videos', os.path.basename(saved_output_path))
            return JsonResponse({'file_url': output_url, 'video_id': video_instance.id})
        else:
            return JsonResponse({'error': 'Invalid form'}, status=400)

    return render(request, 'segmentation/upload_video.html', {'form': VideoForm()})


def delete_video(request):
    if request.method == 'POST':
        file_url = request.POST.get('file_url')
        video = Video.objects.filter(video_file=file_url.split('/media/')[1]).first()

        # Убедитесь, что видео существует и удалите его из базы данных и файловой системы
        if video:
            try:
                video.video_file.delete(save=False)  # Удаляем файл
                video.delete()  # Удаляем запись в базе данных
                return JsonResponse({'status': 'success'})
            except Exception as e:
                return JsonResponse({'status': 'failed', 'error': str(e)})
        else:
            return JsonResponse({'status': 'failed', 'error': 'Video does not exist'})
    return JsonResponse({'status': 'failed'})

def create_frame_sequence(request, video_id):
    # Получаем объект Video по уникальному идентификатору
    video = get_object_or_404(Video, id=video_id)

    # Указываем путь к файлу видео и выходной директории для кадров
    video_path = os.path.join(settings.MEDIA_ROOT, video.video_file.name)  # Используем имя файла из объекта
    output_folder = os.path.join(settings.MEDIA_ROOT, 'frames', os.path.splitext(os.path.basename(video.video_file.name))[0])

    # Извлекаем кадры из видео и получаем список файлов
    extracted_frames = extract_frames_from_video(
        video_path, start_time=request.GET.get('start_time', 0), duration=request.GET.get('duration', 10), 
        fps=request.GET.get('fps', 10), output_folder=output_folder
    )

    if not extracted_frames:
        return JsonResponse({'error': 'No frames were extracted'})

    # Сохраняем каждый кадр как объект FrameSequence
    for frame_path in extracted_frames:
        frame_str_path = str(frame_path)  # Приведение PosixPath к строке
        FrameSequence.objects.create(
            video=video,
            frame_file=frame_str_path
        )

    return redirect('frame_list', video_id=video.id) 


def frame_list(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    frames = video.frame_sequences.all()  # Получаем связанные кадры

    # Создаем список URL для всех кадров
    frame_urls = [frame.frame_file.url for frame in frames]

    return render(request, 'segmentation/frame_list.html', {'frames': frame_urls})
