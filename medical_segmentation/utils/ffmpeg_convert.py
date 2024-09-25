import os
import subprocess
import uuid

def extract_frames_from_video(video_path, start_time, duration, fps, output_folder):
    # Проверяем, существует ли видеофайл
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"The video file '{video_path}' does not exist.")

    # Создаем выходную директорию, если она не существует
    os.makedirs(output_folder, exist_ok=True)

    # Команда FFmpeg для извлечения кадров
    command = [
        'ffmpeg',
        '-ss', str(start_time),          # Начало фрагмента
        '-i', video_path,                # Входное видео
        '-t', str(duration),             # Длительность фрагмента
        '-r', str(fps),                  # Частота кадров
        '-q:v', '0',                     # Качество изображений (0 - наивысшее, 31 - худшее)
        os.path.join(output_folder, '%05d.jpg')  # Путь для сохранения кадров с нумерацией файлов
    ]
    
    # Выполнение команды через subprocess
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg error: {e}")

    # После извлечения кадров возвращаем список файлов в директории
    extracted_frames = sorted([os.path.join('frames/', os.path.basename(output_folder), frame)
                               for frame in os.listdir(output_folder)
                               if frame.endswith('.jpg')])

    return extracted_frames

# # Пример использования
# video_path = 'output.mp4'
# start_time = 10  # Начать с 10 секунды
# duration = 5     # Продолжительность 5 секунд
# output_folder = 'photo'

# extract_frames_from_video(video_path, start_time, duration, output_folder)

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
