from django.shortcuts import render
from django.http import JsonResponse
from utils.model_train import save_model_metadata, train_yolo_model
import threading


def start_training_view(request):
    if request.method == 'POST':
        model_name = request.POST.get('model_name', 'yolov5s')  # Можно выбрать модель YOLOv5s, YOLOv5m и т.д.
        epochs = int(request.POST.get('epochs', 10))
        batch_size = int(request.POST.get('batch_size', 16))
        img_size = int(request.POST.get('img_size', 640))

        # Запускаем обучение в отдельном потоке, чтобы не блокировать веб-сервер
        def train_and_save():
            model_save_path = train_yolo_model(model_name, epochs, batch_size, img_size)
            accuracy = 0.9  # Вы можете получить точность из результатов обучения
            save_model_metadata(model_save_path, model_name, epochs, accuracy)

        threading.Thread(target=train_and_save).start()

        return JsonResponse({'status': 'Training started successfully!'})

    return render(request, 'nettrain/start_training.html')
