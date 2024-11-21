from PIL import Image
import io

def crop_frame(file, left, top, right, bottom):
    """
    Обрезает изображение согласно параметрам кропа.
    :param file: Файл изображения (InMemoryUploadedFile)
    :param left: Слева (пиксели)
    :param top: Сверху (пиксели)
    :param right: Справа (пиксели)
    :param bottom: Снизу (пиксели)
    :return: Новый обрезанный файл изображения
    """
    # Открываем изображение из файла
    img = Image.open(file)

    # Вычисляем размеры обрезки
    width, height = img.size
    crop_box = (
        left,
        top,
        width - right,
        height - bottom
    )
    img_cropped = img.crop(crop_box)

    # Сохраняем обрезанное изображение в память
    output = io.BytesIO()
    img_cropped.save(output, format=img.format)
    output.seek(0)

    return output
