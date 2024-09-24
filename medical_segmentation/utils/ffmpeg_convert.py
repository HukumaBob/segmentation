import subprocess

def extract_frames_from_video(video_path, start_time, duration, output_folder):
    # Команда FFmpeg для извлечения кадров
    command = [
        'ffmpeg',
        '-ss', str(start_time),          # Начало фрагмента
        '-i', video_path,                # Входное видео
        '-t', str(duration),             # Длительность фрагмента
        '-vf', 'fps=1',                  # Извлечение 1 кадра в секунду
        '-q:v', '10',                    # Качество изображений (0 - наивысшее, 31 - худшее)
        f'{output_folder}/%05d.jpg'      # Путь для сохранения кадров
    ]
    
    # Вызов команды через subprocess
    subprocess.run(command)

# Пример использования
video_path = 'output.mp4'
start_time = 10  # Начать с 10 секунды
duration = 5     # Продолжительность 5 секунд
output_folder = 'photo'

extract_frames_from_video(video_path, start_time, duration, output_folder)
