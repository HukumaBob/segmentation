from ultralytics import YOLO
import cv2
import math

# Замените 0 на путь к вашему видеофайлу
cap = cv2.VideoCapture('000.mpg')

# Убедитесь, что видео успешно открыто
if not cap.isOpened():
    print("Ошибка: не удалось открыть видеофайл")
    exit()

# Настройка ширины и высоты кадра (если необходимо)
cap.set(3, 640)
cap.set(4, 480)

# Загрузка модели YOLO
model = YOLO("best.pt")

# Имена классов объектов
classNames = [
    "adenoma",
    "duodenum",
    "papilla_maj",
    "antrum",
    "angiectasis",
    "mouthpiece",
    "tongue",
    "exesa",
    "pylorus",
    "oesophagus",
    "ampulla_duodeni",
    "gastroesophageal_junction",
    "foam",
    "palate",
    "pharynx",
    "vestibular_fold",
    "angulus ventriculi",
    "epiglottis",
    "teeth",
    "phlebectasia"
]


while True:
    success, img = cap.read()
    
    # Проверка успешного чтения кадра. Если достигнут конец видео, выходим из цикла
    if not success:
        print("Конец видео")
        break

    # Получение результатов с модели YOLO
    results = model(img, stream=True)

    # Обработка результатов
    for r in results:
        boxes = r.boxes
        for box in boxes:
            # Координаты ограничивающего прямоугольника
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)  # Преобразование в целые значения

            # Рисуем прямоугольник на изображении
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 255), 3)

            # Доверие (confidence)
            confidence = math.ceil((box.conf[0] * 100)) / 100
            print("Confidence --->", confidence)

            # Имя класса
            cls = int(box.cls[0])
            print("Class name -->", classNames[cls])

            # Выводим детали объекта на изображении
            org = [x1, y1]
            font = cv2.FONT_HERSHEY_SIMPLEX
            fontScale = 1
            color = (255, 0, 0)
            thickness = 2

            cv2.putText(img, classNames[cls], org, font, fontScale, color, thickness)

    # Отображение изображения с наложенными результатами
    cv2.imshow('Video', img)

    # Нажмите 'q', чтобы выйти из просмотра видео
    if cv2.waitKey(55) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
