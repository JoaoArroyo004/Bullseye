import cv2
import os
import numpy as np
import time
from Services.Camera.camera_stream_pc import MJPEGStreamer

FRAME_WIDTH = 640
DATASET_PATH = os.path.join(os.path.dirname(__file__), "Dataset")
print(DATASET_PATH)

# Tamanho padrão das imagens no LBPH
IMG_W = 200
IMG_H = 200


# ============================
# PREPROCESSAMENTO DO ROSTO
# ============================

def preprocess_face(img_gray):
    """
    Normaliza e redimensiona o rosto, exatamente igual no treino e no reconhecimento.
    """
    # Redimensiona igual para todos
    img = cv2.resize(img_gray, (IMG_W, IMG_H))

    # Normaliza iluminação (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    img = clahe.apply(img)

    return img


# ============================
# TREINAMENTO DO LBPH
# ============================

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
                if img is None:
                    continue

                img = preprocess_face(img)

                faces.append(img)
                labels.append(label_counter)

            label_counter += 1

    if len(faces) == 0:
        print("[WARNING] Nenhuma imagem encontrada no dataset.")
        return None, {}

    # LBPH melhorado
    recognizer = cv2.face.LBPHFaceRecognizer_create(
        radius=2,
        neighbors=16,
        grid_x=8,
        grid_y=8
    )

    recognizer.train(faces, np.array(labels))
    print(f"[INFO] LBPH treinado com {len(name_map)} pessoas.")
    return recognizer, name_map


# ============================
# HANDLER PRINCIPAL DA CÂMERA
# ============================

def camera_handler(shared_data, data_lock):

    # Inicia câmera
    streamer = MJPEGStreamer(width=FRAME_WIDTH, height=480, fps=30)
    streamer.start_stream()

    BASE_PATH = os.path.join(os.path.dirname(__file__))
    print(BASE_PATH)

    proto_path = os.path.join(BASE_PATH, "deploy.prototxt.txt")
    model_path = os.path.join(BASE_PATH, "res10_300x300_ssd_iter_140000.caffemodel")

    if not os.path.exists(proto_path) or not os.path.exists(model_path):
        raise FileNotFoundError("Arquivos do modelo DNN não encontrados em Services/Camera")

    dnn_net = cv2.dnn.readNetFromCaffe(proto_path, model_path)



    recognizer, name_map = load_face_recognizer()

    frame_count = 0
    start_time = time.time()
    target_name = shared_data.get("main_target", None)

    try:
        while True:
            frame = streamer.get_frame()
            if frame is None:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            (h, w) = frame.shape[:2]

            # ============================
            # DETECÇÃO DE ROSTO (DNN)
            # ============================
            blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300),
                                         (104.0, 177.0, 123.0))
            dnn_net.setInput(blob)
            detections = dnn_net.forward()

            faces = []
            for i in range(0, detections.shape[2]):
                conf = detections[0, 0, i, 2]
                if conf > 0.60:
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    (x1, y1, x2, y2) = box.astype("int")

                    x1 = max(0, x1)
                    y1 = max(0, y1)
                    x2 = min(w, x2)
                    y2 = min(h, y2)

                    faces.append((x1, y1, x2 - x1, y2 - y1))

            recognized_faces = []
            target_found = False
            target_x = None

            # ============================
            # RECONHECIMENTO (LBPH)
            # ============================

            for (x, y, w_, h_) in faces:
                roi = gray[y:y+h_, x:x+w_]
                roi = preprocess_face(roi)  # <-- CRÍTICO!!!

                label_text = "Unknown"
                confidence = 999

                if recognizer is not None:
                    label, confidence = recognizer.predict(roi)

                    # Quanto mais baixo, melhor (LBPH é invertido)
                    if confidence < 60:
                        label_text = name_map.get(label, "Unknown")

                recognized_faces.append((x, y, w_, h_, label_text, confidence))

            # ============================
            # TRACKING DO TARGET
            # ============================

            with data_lock:
                targets = shared_data.get("current_targets", [])

            for (x, y, w_, h_, label_text, confidence) in recognized_faces:
                if label_text == target_name:
                    center_x = x + w_ // 2
                    target_x = center_x
                    target_found = True
                    break

            with data_lock:
                shared_data["target_x"] = target_x if target_found else None
                shared_data["target_count"] = len(faces)

            # ============================
            # DESENHAR NA TELA
            # ============================

            for (x, y, w_, h_, label_text, confidence) in recognized_faces:
                color = (0, 255, 0) if label_text == target_name else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x + w_, y + h_), color, 2)
                cv2.putText(frame, f"{label_text} ({confidence:.1f})",
                            (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # FPS
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
