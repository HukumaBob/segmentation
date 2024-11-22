import numpy as np
from ultralytics import SAM
from PIL import Image
import matplotlib.pyplot as plt
import os

# Загрузка модели SAM
model = SAM("sam2.1_b.pt")

# Путь к вашему изображению
image_path = "8f7c25d4-169b-43aa-91a3-6043ed46f60a.jpg"

# Загрузка изображения
image = Image.open(image_path)

# Выполнение сегментации
results = model.predict(image)

# Проверяем результаты
if isinstance(results, list) and len(results) > 0:
    # Извлекаем первый результат
    first_result = results[0]

    # Проверяем наличие масок
    if first_result.masks is not None and hasattr(first_result.masks, "data"):
        # Маски находятся в first_result.masks.data
        masks = first_result.masks.data.cpu().numpy()  # Преобразуем тензоры в массивы NumPy

        # Проверяем размерность масок
        if masks.ndim == 3:  # Ожидаем (количество масок, высота, ширина)
            print(f"Detected {masks.shape[0]} masks")

            # Создаем папку для сохранения масок
            save_dir = "segmented_masks"
            os.makedirs(save_dir, exist_ok=True)

            # Визуализация и сохранение каждой маски
            for i, mask in enumerate(masks):
                plt.figure(figsize=(10, 10))
                plt.imshow(mask, cmap="jet")
                plt.axis("off")
                plt.title(f"Mask {i + 1}")
                plt.show()

                # Сохранение маски в файл
                mask_path = os.path.join(save_dir, f"mask_{i + 1}.png")
                plt.imsave(mask_path, mask, cmap="jet")
                print(f"Mask {i + 1} saved to {mask_path}")
        else:
            print("Unexpected masks shape:", masks.shape)
    else:
        print("No masks found in the result.")
else:
    print("No results found.")
