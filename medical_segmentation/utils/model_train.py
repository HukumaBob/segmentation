import os
from ultralytics import YOLO  # Импортируем YOLO из ultralytics
from django.conf import settings
from nettrain.models import NeuralNetworkVersion

def train_yolo_model(model_name, epochs, batch, img_size):
    """
    Функция для дообучения модели YOLOv8.
    
    :param model_name: Имя модели (например, yolo11n, yolo11m, yolo11l, yolo11x)
    :param epochs: Количество эпох обучения
    :param batch_size: Размер батча
    :param img_size: Размер изображения (например, 640)
    :return: Путь к обученной модели
    """
    # Путь к данным (YOLOv8 использует файл .yaml для описания датасета)
    data_path = os.path.join(settings.MEDIA_ROOT, 'yolo_dataset', 'dataset.yaml')  # Убедитесь, что у вас есть файл .yaml

    # Путь для сохранения модели
    save_dir = os.path.join(settings.MEDIA_ROOT, 'trained_models')
    os.makedirs(save_dir, exist_ok=True)

    # Название поддиректории для результатов обучения
    model_name_trained = f"{model_name}_trained"

    # Загрузка модели
    model = YOLO(f"{model_name}.pt")  # Загрузите предобученную модель

    # Обучение модели
    model.train(
        data=data_path,  # Путь к файлу .yaml с описанием вашего датасета
        epochs=epochs,
        batch=batch,
        imgsz=img_size,
        project=save_dir,  # Путь для сохранения результатов проекта
        name=model_name_trained
    )

    # Путь к обученной модели
    model_save_path = os.path.join(save_dir, model_name_trained, 'weights', 'best.pt')

    return model_save_path

def save_model_metadata(model_save_path, model_name, epochs, batch, img_size, accuracy):
    """
    Сохраняем метаданные обученной модели в базе данных.
    
    :param model_save_path: Путь к сохраненной модели
    :param model_name: Название модели
    :param epochs: Количество эпох
    :param batch_size: Размер батча
    :param img_size: Размер изображения
    :param accuracy: Точность модели
    """
    model_version = NeuralNetworkVersion.objects.create(
        name=model_name,
        version_number=f"{model_name}_v{epochs}",
        description=f"Модель дообучена на {epochs} эпохах",
        model_file=model_save_path,
        training_parameters={
            'epochs': epochs,
            'batch': batch,
            'img_size': img_size
        },
        accuracy=accuracy  # Здесь вы можете передать реальную точность, если она известна
    )
    model_version.save()
