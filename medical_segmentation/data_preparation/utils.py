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
    return f"{frame_name}_mask_{frame_id}_tag_{tag_id}.png"

def save_mask_image(mask_array, mask_color, frame_width, frame_height, mask_path):
    """Создаёт изображение маски и сохраняет его в указанный путь."""
    # Преобразуем маску в изображение
    mask_overlay = Image.fromarray((mask_array * 255).astype(np.uint8), mode='L')
    mask_image = Image.new("RGBA", (frame_width, frame_height))
    mask_image.paste(hex_to_rgba(mask_color), (0, 0), mask_overlay)
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
