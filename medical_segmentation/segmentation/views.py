from django.shortcuts import render, redirect
from .forms import MultipleImageUploadForm
from .models import ImageUpload

def image_list(request):
    images = ImageUpload.objects.all()
    return render(request, 'segmentation/image_list.html', {'images': images})

def upload_multiple_images(request):
    if request.method == 'POST':
        form = MultipleImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            files = request.FILES.getlist('images')  # Получаем список всех загруженных файлов
            object_class = form.cleaned_data['object_class']  # Получаем выбранный класс объекта
            
            # Проходим по каждому загруженному файлу и создаем отдельные записи
            for f in files:
                ImageUpload.objects.create(image=f, object_class=object_class)
            
            return redirect('image_list')  # Перенаправляем на список изображений
    else:
        form = MultipleImageUploadForm()

    return render(request, 'segmentation/upload_multiple_images.html', {'form': form})