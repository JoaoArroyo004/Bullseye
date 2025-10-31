import cv2
import os
import numpy as np
import time
from Services.Camera.camera_stream import MJPEGStreamer

FRAME_WIDTH = 640
DATASET_PATH = "dataset"  # pasta com subpastas para cada pessoa (ex: dataset/Ana, dataset/Bob)

# ======================
# Inicialização do reconhecimento facial
# ======================

def load_face_recognizer():
    faces = []
    labels = []
    name_map = {}
    label_counter = 0

    # Percorre subpastas dentro de dataset/
    for person_name in os.listdir(DATASET_PATH):
        person_dir = os.path.join(DATASET_PATH, person_name)
        if os.path.isdir(person_dir):
            name_map[label_counter] = person_name
            for image_name in os.listdir(person_dir):
                image_path = os.path.join(person_dir, image_name)
                img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    faces.append(img)
                    labels.append(label_counter)
            label_counter += 1

    if len(faces) == 0:
        print("[WARNING] Nenhuma imagem encontrada em 'dataset/'. Reconhecimento desativado.")
        return None, {}

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(labels))
    print(f"[INFO] Reconhecedor treinado com {len(name_map)} pessoas.")
    return recognizer, name_map


# ======================
# Função principal da câmera
# ======================

def camera_handler(shared_data, data_lock):
    """
    Thread que lê a câmera, detecta rostos e atualiza shared_data["target_x"].
    Se houver dataset, tenta reconhecer quem é.
    """
    streamer = MJPEGStreamer(width=FRAME_WIDTH, height=480, fps=30)
    streamer.start_stream()

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    recognizer, name_map = load_face_recognizer()

    CENTER_X = FRAME_WIDTH // 2
    frame_count = 0
    start_time = time.time()

    try:
        while True:
            frame = streamer.get_frame()
            if frame is None:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)

            if len(faces) > 0:
                (x, y, w, h) = faces[0]
                center_x = x + w // 2

                # Atualiza posição do rosto no shared_data
                with data_lock:
                    shared_data["target_x"] = center_x
                    shared_data["target_count"] = len(faces)

                # Reconhecimento facial (se disponível)
                face_roi = gray[y:y + h, x:x + w]
                label_text = "Unknown"

                if recognizer is not None:
                    label, confidence = recognizer.predict(face_roi)
                    if confidence < 50:
                        label_text = name_map.get(label, "Unknown")
                    print(f"[FACE] {label_text} ({confidence:.1f})")

                # Desenhar bounding box e nome
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, label_text, (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # FPS display
            frame_count += 1
            elapsed = time.time() - start_time
            if elapsed >= 2:
                fps = frame_count / elapsed
                frame_count = 0
                start_time = time.time()
                cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.imshow("Face Tracking", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        streamer.stop()
        cv2.destroyAllWindows()
