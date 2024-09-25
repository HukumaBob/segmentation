import uuid
import os
from django.shortcuts import render, redirect
from django.conf import settings
from .forms import MultipleImageUploadForm
from .models import ImageUpload
from utils.ffmpeg_convert import extract_frames_from_video, convert_to_webm, save_webm
from django.core.files.storage import FileSystemStorage
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
    if request.method == 'POST' and request.FILES.get('video'):
        video = request.FILES['video']
        video_filename = video.name
        video_path = os.path.join(settings.MEDIA_ROOT, 'videos', video_filename)
        
        os.makedirs(os.path.dirname(video_path), exist_ok=True)
        
        with open(video_path, 'wb+') as destination:
            for chunk in video.chunks():
                destination.write(chunk)
        
        if not video_filename.endswith('.webm'):
            output_path = convert_to_webm(video_path, os.path.dirname(video_path))
            # Удаляем исходный файл после конвертации
            if os.path.exists(video_path):
                os.remove(video_path)
        else:
            output_path = save_webm(video_path, os.path.dirname(video_path))
        
        output_url = os.path.join(settings.MEDIA_URL, 'videos', os.path.basename(output_path))
        return JsonResponse({'file_url': output_url})
    return render(request, 'segmentation/upload_video.html')

def delete_video(request):
    if request.method == 'POST':
        file_url = request.POST.get('file_url')
        # Убедитесь, что путь к файлу формируется правильно
        file_path = os.path.join(settings.MEDIA_ROOT, file_url.lstrip('/media/'))
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return JsonResponse({'status': 'success'})
            except Exception as e:
                return JsonResponse({'status': 'failed', 'error': str(e)})
        else:
            return JsonResponse({'status': 'failed', 'error': 'File does not exist'})
    return JsonResponse({'status': 'failed'})

def create_frame_sequence(request, video_filename):
    video_path = os.path.join(settings.MEDIA_ROOT, 'videos', video_filename)
    output_folder = os.path.join(settings.MEDIA_ROOT, 'frames', video_filename.split('.')[0])

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    extract_frames_from_video(video_path, start_time=0, duration=10, fps=10, output_folder=output_folder)

    return redirect('frame_list', video_id=video_filename.split('.')[0])


def frame_list(request, video_id):
    frame_folder = os.path.join(settings.MEDIA_ROOT, 'frames', video_id)
    if not os.path.exists(frame_folder):
        return render(request, 'segmentation/frame_list.html', {'frames': [], 'error': 'Frames not found'})

    frames = sorted([os.path.join('/media/frames', video_id, f) for f in os.listdir(frame_folder) if f.endswith('.jpg')])
    return render(request, 'segmentation/frame_list.html', {'frames': frames})