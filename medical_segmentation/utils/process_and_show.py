import argparse
import os
import cv2
from ultralytics import YOLO


def process_and_show_video(input_path, model_path, output_path, class_names=None):
    # Проверяем наличие входного файла
    if not os.path.exists(input_path):
        print(f"Ошибка: Файл {input_path} не найден.")
        return

    # Загружаем модель YOLO
    print("Загрузка модели YOLO...")
    model = YOLO(model_path)

    # Открываем видео с использованием OpenCV
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print("Ошибка: не удалось открыть видеофайл.")
        return

    # Получаем параметры видео
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Кодек для MP4

    # Создаём объект для записи видео
    print(f"Сохранение обработанного видео в: {output_path}")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Обработка видео
    print("Начало обработки видео. Нажмите 'q', чтобы выйти.")
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Распознавание объектов на кадре
        results = model(frame, stream=True)
        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])  # Преобразование координат в целые числа
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 2)
                cls = int(box.cls[0])
                confidence = box.conf[0] * 100

                # Получаем имя класса, если список классов указан
                class_name = class_names[cls] if class_names and cls < len(class_names) else "Unknown"

                # Добавление текста на кадр
                cv2.putText(frame, f"{class_name} {confidence:.2f}%", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        # Показываем обработанный кадр в окне
        cv2.imshow('Processed Video', frame)

        # Сохраняем обработанный кадр в видеофайл
        out.write(frame)

        # Прерывание по нажатию клавиши 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Освобождаем ресурсы
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print("Обработка завершена.")


def main():
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description="Видеообработка с использованием YOLO.")
    parser.add_argument("input", help="Путь к входному видеофайлу.")
    parser.add_argument("model", help="Путь к файлу модели YOLO.")
    parser.add_argument("output", help="Путь для сохранения выходного видео.")
    parser.add_argument("--classes", help="Файл с именами классов (по одному на строку).", default=None)

    args = parser.parse_args()

    # Загрузка имён классов, если указано
    class_names = None
    if args.classes:
        with open(args.classes, "r") as f:
            class_names = [line.strip() for line in f.readlines()]

    # Запуск обработки
    process_and_show_video(args.input, args.model, args.output, class_names)


if __name__ == "__main__":
    main()
