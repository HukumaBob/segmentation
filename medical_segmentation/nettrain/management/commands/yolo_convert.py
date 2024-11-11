import os
import cv2
import random
from albumentations import (
    Compose, HorizontalFlip, RandomBrightnessContrast, ShiftScaleRotate, CLAHE, HueSaturationValue, BboxParams
)
from django.core.management.base import BaseCommand
from django.conf import settings
from segmentation.models import FrameSequence, Mask

class Command(BaseCommand):
    help = "Prepare data for YOLO training with augmentation and dataset split"

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

        # Настроим аугментацию с помощью Albumentations
        augmentation = Compose([
            HorizontalFlip(p=0.5),
            RandomBrightnessContrast(p=0.5),
            ShiftScaleRotate(shift_limit=0.1, scale_limit=0.1, rotate_limit=15, p=0.5),
            CLAHE(p=0.2),
            HueSaturationValue(p=0.3)
        ], bbox_params=BboxParams(format='yolo', label_fields=['class_labels']))

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

        # Обработка фреймов и масок
        self.process_frames(train_frames, train_images_path, train_labels_path, augmentation)
        self.process_frames(val_frames, val_images_path, val_labels_path)
        self.process_frames(test_frames, test_images_path, test_labels_path)

        self.stdout.write(self.style.SUCCESS("Датасет успешно подготовлен с аугментацией и разбиением."))

    def process_frames(self, frames, images_path, labels_path, augmentation=None):
        """Обрабатывает кадры, выполняя аугментацию и создавая файлы аннотаций."""
        for frame in frames:
            frame_file_path = frame.frame_file.path
            frame_image = cv2.imread(frame_file_path)

            if frame_image is None:
                self.stdout.write(self.style.ERROR(f"Не удалось загрузить изображение: {frame_file_path}"))
                continue

            # Получаем размеры изображения
            image_height, image_width = frame_image.shape[:2]

            # Создаем файл аннотаций
            label_file_path = os.path.join(labels_path, f"{frame.id}.txt")
            with open(label_file_path, 'w') as label_file:
                masks = Mask.objects.filter(frame_sequence=frame)
                bounding_boxes = []
                class_labels = []

                for mask in masks:
                    if not mask.tag:
                        continue

                    mask_path = mask.mask_file.path
                    bboxes = self.get_bounding_boxes_from_mask(mask_path, image_width, image_height)
                    class_id = mask.tag.id
                    for bbox in bboxes:
                        x_center, y_center, width, height = bbox
                        bounding_boxes.append((x_center, y_center, width, height))
                        class_labels.append(class_id)
                        label_file.write(f"{class_id} {x_center} {y_center} {width} {height}\n")

            # Сохраняем исходное изображение
            image_name = f"{frame.id}.jpg"
            image_save_path = os.path.join(images_path, image_name)
            cv2.imwrite(image_save_path, frame_image)

            # Выполняем аугментацию, если она указана и есть bounding boxes
            if augmentation and bounding_boxes:
                augmented = augmentation(image=frame_image, bboxes=bounding_boxes, class_labels=class_labels)
                aug_image = augmented['image']
                aug_bboxes = augmented['bboxes']

                # Сохраняем аугментированное изображение и аннотации
                aug_image_name = f"{frame.id}_aug.jpg"
                aug_image_save_path = os.path.join(images_path, aug_image_name)
                cv2.imwrite(aug_image_save_path, aug_image)

                aug_label_file_path = os.path.join(labels_path, f"{frame.id}_aug.txt")
                with open(aug_label_file_path, 'w') as aug_label_file:
                    for (x_center, y_center, width, height), class_id in zip(aug_bboxes, class_labels):
                        aug_label_file.write(f"{class_id} {x_center} {y_center} {width} {height}\n")

    def get_bounding_boxes_from_mask(self, mask_path, image_width, image_height):
        """Вычисляет bounding boxes из маски."""
        mask_image = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask_image is None:
            return []

        contours, _ = cv2.findContours(mask_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        bounding_boxes = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            x_center = (x + w / 2) / image_width
            y_center = (y + h / 2) / image_height
            width = w / image_width
            height = h / image_height
            bounding_boxes.append((x_center, y_center, width, height))
        return bounding_boxes
