from PIL import Image
from io import BytesIO

def crop_frame(image_file, left_crop, top_crop, right_crop, bottom_crop, width, height):
    """
    Обрезает изображение и изменяет его размер до указанных ширины и высоты.
    """
    image = Image.open(image_file)

    # Применение обрезки
    cropped_image = image.crop((
        left_crop,
        top_crop,
        image.width - right_crop,
        image.height - bottom_crop
    ))

    # Изменение размера с использованием LANCZOS
    resized_image = cropped_image.resize((width, height), Image.Resampling.LANCZOS)

    # Сохранение изображения в память
    output = BytesIO()
    resized_image.save(output, format=image.format)
    output.seek(0)

    return output

