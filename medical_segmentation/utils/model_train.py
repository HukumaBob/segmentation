import os
import uuid
import pandas as pd
from ultralytics import YOLO  # Импортируем YOLO из ultralytics
from django.conf import settings
from nettrain.models import NeuralNetworkVersion

def train_yolo_model(dataset_name, model_name, epochs, batch, img_size, **kwargs):
    """
    Функция для дообучения модели YOLOv8.
    
    :param model_name: Имя модели (например, yolo11n, yolo11m, yolo11l, yolo11x)
    :param epochs: Количество эпох обучения
    :param batch_size: Размер батча
    :param img_size: Размер изображения (например, 640)
    :param kwargs: Дополнительные опциональные параметры
    :return: Путь к обученной модели
    """
    # Путь к данным (YOLOv8 использует файл .yaml для описания датасета)
    data_path = os.path.join(settings.MEDIA_ROOT, 'yolo_dataset', dataset_name, 'dataset.yaml')  # Убедитесь, что у вас есть файл .yaml

    # Путь для сохранения модели
    save_dir = os.path.join(settings.MEDIA_ROOT, 'trained_models')
    os.makedirs(save_dir, exist_ok=True)

    unique_suffix = str(uuid.uuid4())

    # Название поддиректории для результатов обучения
    model_name_trained = f"{model_name}_{unique_suffix}_trained"

    # Загрузка модели
    model = YOLO(f"{model_name}.pt")  # Загрузите предобученную модель

    # Обучение модели
    model.train(
        data=data_path,  # Путь к файлу .yaml с описанием вашего датасета
        epochs=epochs,
        batch=batch,
        imgsz=img_size,
        project=save_dir,  # Путь для сохранения результатов проекта
        name=model_name_trained,
        **kwargs  # Передаем все опциональные параметры
    )

    # Путь к обученной модели
    model_save_path = os.path.join(save_dir, model_name_trained, 'weights', 'best.pt')


    # Попытка прочитать метрики из результатов
    results_file = os.path.join(save_dir, model_name_trained, 'results.csv')
    mAP50 = None
    if os.path.exists(results_file):
        # Читаем CSV-файл с метриками
        df = pd.read_csv(results_file)
        # Извлекаем значение mAP50 из последней строки
        mAP50 = df['metrics/mAP50(B)'].iloc[-1] if 'metrics/mAP50(B)' in df.columns else None

    return model_save_path, mAP50

def save_model_metadata(model_save_path, model_name, epochs, batch, img_size, accuracy):
    """
    Сохраняем метаданные обученной модели в базе данных.
    
    :param model_save_path: Путь к сохраненной модели
    :param model_name: Название модели
    :param epochs: Количество эпох
    :param batch: Размер батча
    :param img_size: Размер изображения
    :param accuracy: Точность модели
    """
    # Определяем номер версии
    last_version = NeuralNetworkVersion.objects.filter(name=model_name).order_by('-version_number').first()
    if last_version:
        # Извлекаем номер версии из предыдущей записи и увеличиваем его
        try:
            last_version_number = int(last_version.version_number.split('_v')[-1])
            new_version_number = last_version_number + 1
        except ValueError:
            new_version_number = 1  # Если номер не удается извлечь, начинаем с 1
    else:
        new_version_number = 1  # Если версий не было, начинаем с 1

    # Создаем новую запись с новым номером версии
    model_version = NeuralNetworkVersion.objects.create(
        name=model_name,
        version_number=f"{model_name}_v{new_version_number}",
        description=f"Модель дообучена на {epochs} эпохах",
        model_file=model_save_path,
        training_parameters={
            'epochs': epochs,
            'batch': batch,
            'img_size': img_size
        },
        accuracy=accuracy  # Передаем реальную точность
    )
    model_version.save()

