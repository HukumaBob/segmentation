# sam2_utils.py
import torch
import numpy as np
from PIL import Image
from sam2.build_sam import build_sam2_video_predictor

# Подготовка модели SAM2
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
sam2_checkpoint = "checkpoints/sam2_hiera_large.pt"
model_cfg = "sam2_hiera_l.yaml"
predictor = build_sam2_video_predictor(model_cfg, sam2_checkpoint, device=device)

def generate_mask(image_path, point):
    """
    Генерация маски для заданного изображения и точки.
    :param image_path: Путь к изображению кадра.
    :param point: Координаты точки (x, y).
    :return: Объект PIL с маской.
    """
    # Инициализация предсказания
    inference_state = predictor.init_state(image_path)
    predictor.reset_state(inference_state)
    
    # Конвертация точки в массив NumPy
    points = np.array([point], dtype=np.float32)
    labels = np.array([1], dtype=np.int32)  # Метка 1 означает положительный клик

    # Генерация маски
    _, out_obj_ids, out_mask_logits = predictor.add_new_points_or_box(
        inference_state=inference_state,
        frame_idx=0,  # В нашем случае работаем с одним изображением
        obj_id=1,     # Идентификатор объекта
        points=points,
        labels=labels,
    )

    # Преобразование маски в изображение
    mask = (out_mask_logits[0] > 0.0).cpu().numpy()
    mask_image = Image.fromarray((mask * 255).astype(np.uint8))  # Преобразуем в формат PIL
    return mask_image
