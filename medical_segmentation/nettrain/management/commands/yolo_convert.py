import os
import cv2
import json
import random
import yaml  # Импортируем библиотеку для работы с YAML
from django.core.management.base import BaseCommand
from django.conf import settings
from segmentation.models import FrameSequence, Mask

ROUND_COORDINATES = 8

class Command(BaseCommand):
    help = "Prepare data for YOLO training and COCO format"

    def handle(self, *args, **kwargs):
        # Определим пути для сохранения датасета
        dataset_path = os.path.join(settings.MEDIA_ROOT, 'yolo_dataset')
        train_images_path = os.path.join(dataset_path, 'train', 'images')
        train_labels_path = os.path.join(dataset_path, 'train', 'labels')
        val_images_path = os.path.join(dataset_path, 'val', 'images')
        val_labels_path = os.path.join(dataset_path, 'val', 'labels')
        test_images_path = os.path.join(dataset_path, 'test', 'images')
        test_labels_path = os.path.join(dataset_path, 'test', 'labels')

        # Создадим директории, если они не существуют
        for path in [train_images_path, train_labels_path, val_images_path, val_labels_path, test_images_path, test_labels_path]:
            os.makedirs(path, exist_ok=True)

        # Извлечем все фреймы, у которых есть связанные маски
        frame_sequences = list(FrameSequence.objects.filter(masks__isnull=False).distinct())
        random.shuffle(frame_sequences)

        # Разделим данные: 80% - обучение, 10% - валидация, 10% - тест
        total_frames = len(frame_sequences)
        train_split = int(0.8 * total_frames)
        val_split = int(0.9 * total_frames)

        train_frames = frame_sequences[:train_split]
        val_frames = frame_sequences[train_split:val_split]
        test_frames = frame_sequences[val_split:]

        # Сохраняем аннотации в формате COCO
        coco_annotations = {
            "images": [],
            "annotations": [],
            "categories": []
        }
        self.annotation_id = 1  # Уникальный ID для аннотаций
        self.category_map = {}  # Карта для хранения категорий
        self.category_id = 0  # Уникальный ID для категорий

        # Обрабатываем фреймы
        self.process_frames(train_frames, train_images_path, train_labels_path, coco_annotations, "train")
        self.process_frames(val_frames, val_images_path, val_labels_path, coco_annotations, "val")
        self.process_frames(test_frames, test_images_path, test_labels_path, coco_annotations, "test")

        # Сохраняем COCO-аннотации в файл
        coco_output_path = os.path.join(dataset_path, 'coco_annotations.json')
        with open(coco_output_path, 'w') as coco_file:
            json.dump(coco_annotations, coco_file, indent=4)

        # Создаем файл dataset.yaml для YOLO
        self.create_dataset_yaml(dataset_path, train_images_path, val_images_path, self.category_map)

        self.stdout.write(self.style.SUCCESS("Датасет успешно подготовлен в формате YOLO и COCO."))

    def create_dataset_yaml(self, dataset_path, train_images_path, val_images_path, category_map):
        """Создает файл dataset.yaml для YOLO."""
        dataset_yaml_path = os.path.join(dataset_path, 'dataset.yaml')
        data = {
            'train': train_images_path,
            'val': val_images_path,
            'names': list(category_map.keys())
        }
        with open(dataset_yaml_path, 'w') as yaml_file:
            yaml.dump(data, yaml_file, default_flow_style=False)

    def process_frames(self, frames, images_path, labels_path, coco_annotations, split):
        """Обрабатывает кадры, создавая файлы аннотаций."""
        # target_size = (640, 640)  # Размер, к которому будем приводить изображения

        for frame in frames:
            frame_file_path = frame.frame_file.path
            frame_image = cv2.imread(frame_file_path)

            if frame_image is None:
                self.stdout.write(self.style.ERROR(f"Не удалось загрузить изображение: {frame_file_path}"))
                continue

            # Получаем исходные размеры изображения
            original_height, original_width = frame_image.shape[:2]

            # Изменяем размер изображения
            # frame_image_resized = cv2.resize(frame_image, target_size)
            # new_height, new_width = target_size

            image_id = frame.id

            # Добавляем информацию об изображении в COCO
            coco_annotations["images"].append({
                "id": image_id,
                "file_name": os.path.basename(frame_file_path),
                "height": original_height,
                "width": original_width
            })

            # Создаем файл аннотаций для YOLO
            label_file_path = os.path.join(labels_path, f"{frame.id}.txt")
            with open(label_file_path, 'w') as label_file:
                masks = Mask.objects.filter(frame_sequence=frame)
                bounding_boxes = []
                class_labels = []

                for mask in masks:
                    if not mask.tag:
                        continue

                    # Добавляем категорию в COCO, если она ещё не добавлена
                    if mask.tag.name not in self.category_map:
                        self.category_map[mask.tag.name] = self.category_id
                        coco_annotations["categories"].append({
                            "id": self.category_id,
                            "name": mask.tag.name
                        })
                        self.category_id += 1

                    class_id = self.category_map[mask.tag.name]
                    mask_path = mask.mask_file.path
                    bboxes = self.get_bounding_boxes_from_mask(mask_path, original_width, original_height)

                    for bbox in bboxes:
                        x_center, y_center, width, height = bbox

                        # Фильтруем bounding boxes с размерами менее 1% от ширины или высоты изображения
                        if width >= 0.01 and height >= 0.01:
                            bounding_boxes.append((x_center, y_center, width, height))
                            class_labels.append(class_id)
                            label_file.write(f"{class_id} {x_center} {y_center} {width} {height}\n")

                            # Добавляем аннотацию в COCO
                            x_min = int((x_center - width / 2) * original_width)
                            y_min = int((y_center - height / 2) * original_height)
                            coco_annotations["annotations"].append({
                                "id": self.annotation_id,
                                "image_id": image_id,
                                "category_id": class_id,
                                "bbox": [x_min, y_min, int(width * original_width), int(height * original_height)],
                                "area": int((width * original_width) * (height * original_height)),
                                "iscrowd": 0
                            })
                            self.annotation_id += 1

            # Сохраняем изображение с новым размером
            image_name = f"{frame.id}.jpg"
            image_save_path = os.path.join(images_path, image_name)
            cv2.imwrite(image_save_path, frame_image)

    def get_bounding_boxes_from_mask(self, mask_path, image_width, image_height):
        """Вычисляет bounding boxes из маски."""
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
            if width >= 0.01 and height >= 0.01:
                bounding_boxes.append((x_center, y_center, width, height))
        return bounding_boxes
