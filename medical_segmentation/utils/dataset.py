import os
import cv2
import json
import random
import yaml
from django.conf import settings
from data_preparation.models import Dataset
from segmentation.models import FrameSequence, Mask

ROUND_COORDINATES = 4
MINIMAL_BOX_WIDTH = 0.1
MINIMAL_BOX_HEIGHT = 0.1


def prepare_dataset(dataset_name, dataset_description, train_percentage, val_percentage, selected_sequences):
    """
    Функция для подготовки датасета в форматах YOLO и COCO.

    :param dataset_name: Название датасета
    :param train_percentage: Процент данных для обучения
    :param val_percentage: Процент данных для валидации
    :param selected_sequences: QuerySet или список выбранных FrameSequence
    """
    # Проверяем, существует ли датасет с таким именем
    dataset, created = Dataset.objects.get_or_create(name=dataset_name)

    # Определим пути для сохранения датасета
    dataset_path = os.path.join(settings.MEDIA_ROOT, 'yolo_dataset', dataset_name)
    train_images_path = os.path.join(dataset_path, 'train', 'images')
    train_labels_path = os.path.join(dataset_path, 'train', 'labels')
    val_images_path = os.path.join(dataset_path, 'val', 'images')
    val_labels_path = os.path.join(dataset_path, 'val', 'labels')
    test_images_path = os.path.join(dataset_path, 'test', 'images')
    test_labels_path = os.path.join(dataset_path, 'test', 'labels')

    # Создаем директории
    for path in [train_images_path, train_labels_path, val_images_path, val_labels_path, test_images_path, test_labels_path]:
        os.makedirs(path, exist_ok=True)

    # Фильтруем кадры на основе выбранных последовательностей
    frame_sequences = FrameSequence.objects.filter(sequences__id__in=selected_sequences).filter(masks__isnull=False).distinct()
    frame_sequences = list(frame_sequences)  # Преобразуем в список
    random.shuffle(frame_sequences)

    # Разделяем данные
    total_frames = len(frame_sequences)
    train_split = int(train_percentage / 100 * total_frames)
    val_split = int((train_percentage + val_percentage) / 100 * total_frames)

    train_frames = frame_sequences[:train_split]
    val_frames = frame_sequences[train_split:val_split]
    test_frames = frame_sequences[val_split:]

    coco_annotations = {"images": [], "annotations": [], "categories": []}
    annotation_id = 1
    category_id = 0
    category_map = {}

    # Функция для обработки кадров
    def process_frames(frames, images_path, labels_path, split):
        nonlocal annotation_id, category_id, category_map

        for frame in frames:
            frame_path = frame.frame_file.path
            frame_image = cv2.imread(frame_path)
            if frame_image is None:
                print(f"Не удалось загрузить: {frame_path}")
                continue

            original_height, original_width = frame_image.shape[:2]
            image_id = frame.id

            coco_annotations["images"].append({
                "id": image_id,
                "file_name": os.path.basename(frame_path),
                "height": original_height,
                "width": original_width
            })

            label_path = os.path.join(labels_path, f"{frame.id}.txt")
            with open(label_path, 'w') as label_file:
                masks = Mask.objects.filter(frame_sequence=frame)
                for mask in masks:
                    if not mask.tag:
                        continue

                    if mask.tag.name not in category_map:
                        category_map[mask.tag.name] = category_id
                        coco_annotations["categories"].append({
                            "id": category_id,
                            "name": mask.tag.name
                        })
                        category_id += 1

                    class_id = category_map[mask.tag.name]
                    bboxes = get_bounding_boxes_from_mask(mask.mask_file.path, original_width, original_height)
                    for bbox in bboxes:
                        x_center, y_center, width, height = bbox
                        if width >= 0.01 and height >= 0.01:
                            label_file.write(f"{class_id} {x_center} {y_center} {width} {height}\n")
                            coco_annotations["annotations"].append({
                                "id": annotation_id,
                                "image_id": image_id,
                                "category_id": class_id,
                                "bbox": [int((x_center - width / 2) * original_width),
                                         int((y_center - height / 2) * original_height),
                                         int(width * original_width),
                                         int(height * original_height)],
                                "area": int((width * original_width) * (height * original_height)),
                                "iscrowd": 0
                            })
                            annotation_id += 1

            image_name = f"{frame.id}.jpg"
            image_save_path = os.path.join(images_path, image_name)
            cv2.imwrite(image_save_path, frame_image)

    # Функция для получения bounding boxes из маски
    def get_bounding_boxes_from_mask(mask_path, image_width, image_height):
        mask_image = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask_image is None:
            return []

        contours, _ = cv2.findContours(mask_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        bounding_boxes = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            x_center = round((x + w / 2) / image_width, ROUND_COORDINATES)
            y_center = round((y + h / 2) / image_height, ROUND_COORDINATES)
            width = round(w / image_width, ROUND_COORDINATES)
            height = round(h / image_height, ROUND_COORDINATES)
            if width >= MINIMAL_BOX_WIDTH and height >= MINIMAL_BOX_HEIGHT:
                bounding_boxes.append((x_center, y_center, width, height))
        return bounding_boxes

    # Обрабатываем кадры
    process_frames(train_frames, train_images_path, train_labels_path, "train")
    process_frames(val_frames, val_images_path, val_labels_path, "val")
    process_frames(test_frames, test_images_path, test_labels_path, "test")

    # Сохраняем COCO
    coco_output_path = os.path.join(dataset_path, 'coco_annotations.json')
    with open(coco_output_path, 'w') as coco_file:
        json.dump(coco_annotations, coco_file, indent=4)

    # Создаем `dataset.yaml`
    yaml_data = {
        'train': train_images_path,
        'val': val_images_path,
        'test': test_images_path,
        'names': list(category_map.keys())
    }
    yaml_path = os.path.join(dataset_path, 'dataset.yaml')
    with open(yaml_path, 'w') as yaml_file:
        yaml.dump(yaml_data, yaml_file, default_flow_style=False)

    # Обновляем описание датасета, если он только что создан
    if created:
        dataset.description = dataset_description
        dataset.save()

    print(f"Датасет '{dataset_name}' успешно подготовлен!")


