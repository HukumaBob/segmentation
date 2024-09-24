import uuid
import os
from django.shortcuts import render, redirect
from django.conf import settings
from .forms import MultipleImageUploadForm, VideoUploadForm
from .models import ImageUpload
from utils.ffmpeg_convert import extract_frames_from_video

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

def upload_video_and_extract_frames(request):
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            video_file = request.FILES['video']
            start_time = form.cleaned_data['start_time']
            duration = form.cleaned_data['duration']
            fps = form.cleaned_data['fps']

            # Сохранение загруженного видео с уникальным именем
            ext = video_file.name.split('.')[-1]
            video_filename = f"{uuid.uuid4()}.{ext}"
            video_path = os.path.join(settings.MEDIA_ROOT, 'videos', video_filename)

            with open(video_path, 'wb+') as destination:
                for chunk in video_file.chunks():
                    destination.write(chunk)

            # Папка для сохранения кадров
            output_folder = os.path.join(settings.MEDIA_ROOT, 'frames', video_filename.split('.')[0])

            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

            # Вызов функции для извлечения кадров
            extract_frames_from_video(video_path, start_time, duration, output_folder)

            # Переадресация на страницу с отображением кадров
            return redirect('frame_list', video_id=video_filename.split('.')[0])

    else:
        form = VideoUploadForm()

    return render(request, 'segmentation/upload_video.html', {'form': form})

def frame_list(request, video_id):
    # Папка, где хранятся кадры
    frame_folder = os.path.join(settings.MEDIA_ROOT, 'frames', video_id)
    
    # Проверяем, что папка существует
    if not os.path.exists(frame_folder):
        return render(request, 'segmentation/frame_list.html', {'frames': [], 'error': 'Frames not found'})
    
    # Получаем список кадров, сортируем
    frames = sorted([os.path.join('/media/frames', video_id, f) for f in os.listdir(frame_folder) if f.endswith('.jpg')])

    # Передаем кадры в шаблон
    return render(request, 'segmentation/frame_list.html', {'frames': frames})