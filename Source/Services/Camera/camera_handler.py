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
    target_name = shared_data.get("main_target", None)

    try:
        while True:
            frame = streamer.get_frame()
            if frame is None:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            if len(faces) > 0:
                recognized_faces = []
                target_found = False
                target_x = None

                for (x, y, w, h) in faces:
                    face_roi = gray[y:y + h, x:x + w]
                    label_text = "Unknown"
                    confidence = 999

                    # Reconhece o rosto (se modelo disponível)
                    if recognizer is not None:
                        label, confidence = recognizer.predict(face_roi)
                        if confidence < 80:
                            label_text = name_map.get(label, "Unknown")

                    # Guarda o resultado
                    recognized_faces.append((x, y, w, h, label_text, confidence))

                # Verifica se algum rosto corresponde ao(s) target(s)
                with data_lock:
                    targets = shared_data.get("current_targets", [])

                for (x, y, w, h, label_text, confidence) in recognized_faces:
                    if label_text == target_name:
                        center_x = x + w // 2
                        target_x = center_x
                        target_found = True
                        break  # só o primeiro alvo encontrado

                # Atualiza shared_data
                with data_lock:
                    if target_found:
                        shared_data["target_x"] = target_x
                        shared_data["target_count"] = len(faces)
                    else:
                        # Nenhum alvo válido encontrado
                        shared_data["target_x"] = None
                        shared_data["target_count"] = len(faces)

                # Desenhar as detecções na tela
                for (x, y, w, h, label_text, confidence) in recognized_faces:
                    color = (0, 255, 0) if label_text == target_name else (0, 0, 255)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    cv2.putText(frame, f"{label_text} ({confidence:.1f})", (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)


            # FPS display
            frame_count += 1
            elapsed = time.time() - start_time
            if elapsed >= 2:
                fps = frame_count / elapsed
                frame_count = 0
                start_time = time.time()
                cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
            if target_name:
                cv2.putText(frame, f"Target: {target_name}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            cv2.imshow("Face Tracking", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        streamer.stop()
        cv2.destroyAllWindows()
