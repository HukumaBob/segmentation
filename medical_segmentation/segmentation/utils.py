import os
from django.conf import settings
from PIL import Image
import numpy as np
from segmentation.models import Mask
from utils.colors_convert import hex_to_rgba


# Константа для прозрачности (при необходимости)
ALPHA = 128

def generate_mask_filename(frame, frame_id, tag_id):
    """Генерирует имя файла маски."""
    frame_name = os.path.splitext(os.path.basename(frame.frame_file.name))[0]
    return f"{frame_name}_mask_{frame_id}_tag-id_{tag_id}.png"

def save_mask_image(mask_array, mask_color, frame_width, frame_height, mask_path):
    """Создаёт изображение маски и сохраняет его в указанный путь."""
    mask_overlay = Image.fromarray((mask_array * 255).astype(np.uint8), mode='L')
    mask_image = Image.new("RGBA", (frame_width, frame_height))
    mask_image.paste(hex_to_rgba(mask_color), (0, 0), mask_overlay)
    
    # Сохраняем изображение на диск
    print(f"Saving new mask at: {mask_path}")
    mask_image.save(mask_path)

def save_or_update_mask_record(frame, tag, mask_color, mask_path):
    """Создаёт или обновляет запись маски в базе данных."""
    relative_mask_url = os.path.relpath(mask_path, settings.MEDIA_ROOT).replace(os.sep, "/")
    mask_record, created = Mask.objects.get_or_create(
        frame_sequence=frame,
        tag=tag,
        defaults={'mask_file': '', 'mask_color': mask_color}
    )
    mask_record.mask_file = relative_mask_url
    mask_record.mask_color = mask_color
    mask_record.save()
    return mask_record

def subtract_new_masks_from_existing(existing_masks, new_masks):
    """
    Вычитает новые маски из всех старых масок, связанных с кадром.
    
    Args:
        existing_masks (QuerySet): Список старых масок из БД.
        new_masks (dict): Словарь новых масок {obj_id: numpy_array}.
    """
    for mask_record in existing_masks:
        old_mask_path = os.path.join(settings.MEDIA_ROOT, mask_record.mask_file.name)

        if os.path.exists(old_mask_path):
            print(f"Loading existing mask: {old_mask_path}")
            old_mask = Image.open(old_mask_path).convert("L")
            old_mask_array = np.array(old_mask) > 0

            # Вычитаем каждую новую маску из старой
            for obj_id, new_mask_array in new_masks.items():
                print(f"Subtracting new mask from existing mask for {mask_record.frame_sequence.id}")
                old_mask_array = np.where(new_mask_array, 0, old_mask_array)

            # Проверяем, не стала ли итоговая маска пустой
            if not old_mask_array.any():
                print(f"Warning: Mask for frame {mask_record.frame_sequence.id} is empty after subtraction.")

            # Удаляем старую маску перед сохранением новой
            print(f"Deleting old mask: {old_mask_path}")
            os.remove(old_mask_path)

            # Сохраняем изменённую старую маску на диск
            frame_width, frame_height = old_mask_array.shape[::-1]
            print(f"Saving modified mask at: {old_mask_path}")
            save_mask_image(old_mask_array, mask_record.mask_color, frame_width, frame_height, old_mask_path)

            # Обновляем или создаём запись маски в БД
            save_or_update_mask_record(mask_record.frame_sequence, mask_record.tag, 
                                       mask_record.mask_color, old_mask_path)

