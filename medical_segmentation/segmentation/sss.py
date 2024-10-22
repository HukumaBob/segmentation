import numpy as np
from PIL import Image, ImageDraw

def subtract_circle_from_mask(current_mask):
    """Вычитает круг из середины текущей маски для проверки работы вычитания."""
    # Размеры маски
    height, width = current_mask.shape

    # Инициализируем итоговую маску как копию текущей
    final_mask = current_mask.copy()

    # Создаём пустую маску того же размера с нарисованным кругом в центре
    circle_mask = Image.new("L", (width, height), 0)  # Чёрное изображение (0 - фон)
    draw = ImageDraw.Draw(circle_mask)

    # Определяем параметры круга (центр и радиус)
    center = (width // 2, height // 2)
    radius = min(width, height) // 4  # Радиус круга — четверть меньшей стороны

    # Рисуем белый круг (255) в центре
    draw.ellipse(
        (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius),
        fill=255
    )

    # Преобразуем круговую маску в бинарный numpy-массив
    circle_mask_array = np.array(circle_mask) > 0  # 1 - пиксели круга, 0 - фон

    # Выполняем вычитание круга из текущей маски
    final_mask = np.where(circle_mask_array, 0, final_mask)

    # Вернём итоговую маску и круговую маску для проверки
    return final_mask, circle_mask_array

# Создаём случайную бинарную маску размером 100x100 для теста
test_mask = np.random.randint(0, 2, (100, 100), dtype=np.uint8)

# Выполняем проверку: вычитаем круг из середины
result_mask, circle_mask = subtract_circle_from_mask(test_mask)

# Преобразуем маски в изображения для наглядности
Image.fromarray((test_mask * 255).astype(np.uint8)).show(title="Original Mask")
Image.fromarray((circle_mask * 255).astype(np.uint8)).show(title="Circle Mask")
Image.fromarray((result_mask * 255).astype(np.uint8)).show(title="Result Mask")
