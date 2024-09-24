from django.shortcuts import render, redirect
from .forms import MultipleImageUploadForm
from .models import ImageUpload

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
                ImageUpload.objects.create(image=f, object_class=object_class)
            
            return redirect('image_list')
    else:
        form = MultipleImageUploadForm()

    return render(request, 'segmentation/upload_multiple_images.html', {'form': form})
