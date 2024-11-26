from django.shortcuts import render
from django.http import JsonResponse
from data_preparation.models import Dataset
from nettrain.models import NeuralNetworkVersion
from utils.model_train import save_model_metadata, train_yolo_model
import threading

def start_training_view(request):
    if request.method == 'POST':
        # Собираем все параметры в словарь
        all_params = request.POST.dict()
        # Получаем обязательные параметры
        # Удаляем параметры, которые не нужны для вызова train_yolo_model
        model_description = all_params.pop('model_description', None)
        all_params.pop('csrfmiddlewaretoken', None)  # Удаляем CSRF токен
        model_name = all_params.pop('model_name', None)  
        epochs = int(all_params.pop('epochs', None))  
        batch_size = int(all_params.pop('batch_size', None))  
        img_size = int(all_params.pop('img_size', None))  
        dataset_name = all_params.pop('dataset_name', None)

        # Проверяем, что выбранный датасет существует
        try:
            dataset = Dataset.objects.get(name=dataset_name)
        except Dataset.DoesNotExist:
            return JsonResponse({'error': 'Selected dataset does not exist.'}, status=400)
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
            model_save_path, accuracy, data_path = train_yolo_model(
                dataset_name = dataset_name,
                model_name=model_name,
                epochs=epochs,
                batch=batch_size,
                img_size=img_size,
                **all_params  # Передаем все параметры как именованные аргументы
            )
            save_model_metadata(model_description, data_path, model_save_path, model_name, epochs, batch_size, img_size, accuracy, **all_params)

        threading.Thread(target=train_and_save).start()

        return JsonResponse({'status': 'Training started successfully!'})
    # Загрузка всех доступных датасетов
    datasets = Dataset.objects.all()    
    trained_models = NeuralNetworkVersion.objects.all()    

    return render(request, 'nettrain/start_training.html', {
        'datasets': datasets,
        'trained_models': trained_models
        })
