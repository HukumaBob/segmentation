from django.shortcuts import render
from django.http import JsonResponse
from data_preparation.models import Dataset
from utils.model_train import save_model_metadata, train_yolo_model
import threading

def start_training_view(request):
    if request.method == 'POST':
        # Получаем обязательные параметры
        model_name = request.POST.get('model_name', 'yolo11n')
        epochs = int(request.POST.get('epochs', 10))
        batch_size = int(request.POST.get('batch_size', 16))
        img_size = int(request.POST.get('img_size', 640))
        dataset_name = request.POST.get('dataset_name')
        
        # Проверяем, что выбранный датасет существует
        try:
            dataset = Dataset.objects.get(name=dataset_name)
        except Dataset.DoesNotExist:
            return JsonResponse({'error': 'Selected dataset does not exist.'}, status=400)

        # Собираем все параметры в словарь
        all_params = request.POST.dict()

        # Удаляем параметры, которые не нужны для вызова train_yolo_model
        all_params.pop('csrfmiddlewaretoken', None)  # Удаляем CSRF токен
        all_params.pop('model_name', None)  
        all_params.pop('epochs', None)  
        all_params.pop('batch_size', None)  
        all_params.pop('img_size', None)  
        all_params.pop('dataset_name', None)
        
        # Фильтруем пустые или незаполненные значения
        all_params = {k: v for k, v in all_params.items() if v}  # Оставляем только непустые значения

        # Преобразуем значения параметров, где это необходимо
        for key, value in all_params.items():
            try:
                # Сначала попробуем преобразовать значение в int (учитывает как положительные, так и отрицательные числа)
                all_params[key] = int(value)
            except ValueError:
                try:
                    # Если преобразование в int не удалось, попробуем преобразовать в float
                    all_params[key] = float(value)
                except ValueError:
                    # Если преобразование в float также не удалось, проверим на булевые значения
                    if value.lower() in ['true', 'false']:
                        all_params[key] = value.lower() == 'true'


        # Запускаем обучение в отдельном потоке
        def train_and_save():
            model_save_path, accuracy = train_yolo_model(
                dataset_name = dataset_name,
                model_name=model_name,
                epochs=epochs,
                batch=batch_size,
                img_size=img_size,
                **all_params  # Передаем все параметры как именованные аргументы
            )
            save_model_metadata(model_save_path, model_name, epochs, batch_size, img_size, accuracy)

        threading.Thread(target=train_and_save).start()

        return JsonResponse({'status': 'Training started successfully!'})
    # Загрузка всех доступных датасетов
    datasets = Dataset.objects.all()    

    return render(request, 'nettrain/start_training.html', {'datasets': datasets})
