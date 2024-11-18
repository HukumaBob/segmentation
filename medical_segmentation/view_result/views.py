import os
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from nettrain.models import NeuralNetworkVersion
from ultralytics import YOLO
import cv2

def view_video(request):
    if request.method == 'POST' and request.FILES.get('video'):
        # Получаем загруженный видеофайл
        video_file = request.FILES['video']
        
        # Сохраняем видеофайл в папку MEDIA_ROOT/videos
        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'videos'))
        filename = fs.save(video_file.name, video_file)
        video_path = fs.path(filename)

        # Получаем выбранную модель из базы данных
        model_id = request.POST.get('model_id')
        model_instance = NeuralNetworkVersion.objects.get(id=model_id)
        model_file_path = model_instance.model_file.path

        # Загружаем модель YOLO
        model = YOLO(model_file_path)

        # Обработка видео с использованием OpenCV
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return render(request, 'error.html', {'message': 'Ошибка: не удалось открыть видеофайл'})

        # Обработка каждого кадра видео
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Распознавание объектов на кадре
            results = model(frame, stream=True)
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])  # Преобразование координат в целые числа
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 2)
                    cls = int(box.cls[0])
                    confidence = box.conf[0] * 100
                    class_name = "Class Name Here"  # Замените это на правильное имя класса

                    # Добавление текста на кадр
                    cv2.putText(frame, f"{class_name} {confidence:.2f}%", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            # Здесь можно добавить сохранение обработанного видео или отправку кадра в поток

        cap.release()
        cv2.destroyAllWindows()

        return render(request, 'success.html', {'video_path': video_path})

    # Получаем все доступные модели для выбора в шаблоне
    models = NeuralNetworkVersion.objects.all()
    return render(request, 'view_result/view_video.html', {'models': models})
