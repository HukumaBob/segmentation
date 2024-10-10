import os
import subprocess
import uuid
import re

def extract_frames_from_video(video_path, start_time, duration, fps, output_folder, left_crop=0, right_crop=0, top_crop=0, bottom_crop=0):
    # Проверяем, существует ли видеофайл
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"The video file '{video_path}' does not exist.")

    # Создаем выходную директорию, если она не существует
    os.makedirs(output_folder, exist_ok=True)

    # Ищем последний файл в папке output_folder с расширением .jpg
    existing_files = sorted([f for f in os.listdir(output_folder) if f.endswith('.jpg')])
    
    if existing_files:
        # Извлекаем номер последнего кадра из имени файла (например, "00123.jpg")
        last_frame = existing_files[-1]
        match = re.search(r'(\d+)\.jpg$', last_frame)
        if match:
            start_number = int(match.group(1)) + 1  # Номер следующего кадра
        else:
            start_number = 0  # Если не удается определить номер, начинаем с 0
    else:
        start_number = 0  # Если файлов нет, начинаем с 0

    # Команда FFmpeg для извлечения кадров
    command = [
        'ffmpeg',
        '-ss', str(start_time),                      # Начало фрагмента
        '-i', video_path,                            # Входное видео
        '-t', str(duration),                         # Длительность фрагмента
        '-r', str(fps),                              # Частота кадров
        '-q:v', '0',                                 # Качество изображений (0 - наивысшее, 31 - худшее)
        '-vf', f"crop=iw-{left_crop + right_crop}:ih-{top_crop + bottom_crop}:{left_crop}:{top_crop}",  # Обрезка
        '-start_number', str(start_number),           # Начало нумерации кадров
        os.path.join(output_folder, '%05d.jpg')      # Путь для сохранения кадров с нумерацией файлов
    ]

    # Выполнение команды через subprocess
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg error: {e}")

    # После извлечения кадров возвращаем список только новых файлов, начиная с текущего start_number
    extracted_frames = sorted([os.path.join('frames/', os.path.basename(output_folder), frame)
                               for frame in os.listdir(output_folder)
                               if frame.endswith('.jpg') and int(re.search(r'(\d+)\.jpg$', frame).group(1)) >= start_number])

    return extracted_frames



def convert_to_webm(input_path, output_dir):
    output_filename = f"{uuid.uuid4()}.webm"
    output_path = os.path.join(output_dir, output_filename)
    subprocess.run(['ffmpeg', '-i', input_path, '-c:v', 'libvpx-vp9', '-b:v', '2M', output_path])
    return output_path

def save_webm(input_path, output_dir):
    output_filename = f"{uuid.uuid4()}.webm"
    output_path = os.path.join(output_dir, output_filename)
    os.rename(input_path, output_path)
    return output_path
