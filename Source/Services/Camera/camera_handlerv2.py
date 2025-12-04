import cv2
import os
import numpy as np
import time
from Services.Camera.camera_stream_pc import MJPEGStreamer

FRAME_WIDTH = 640
DATASET_PATH = os.path.join(os.path.dirname(__file__), "Dataset")

IMG_W = 800
IMG_H = 800

def preprocess_face(img_gray):
    """Pré-processamento simples para teste, sem Laplacian"""
    img = cv2.resize(img_gray, (IMG_W, IMG_H))
    img = cv2.GaussianBlur(img, (3, 3), 0)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    img = clahe.apply(img)
    img = cv2.equalizeHist(img)
    return img

def load_face_recognizer():
    faces = []
    labels = []
    name_map = {}
    label_counter = 0

    for person_name in os.listdir(DATASET_PATH):
        person_dir = os.path.join(DATASET_PATH, person_name)
        if not os.path.isdir(person_dir):
            continue

        images = [f for f in os.listdir(person_dir) if f.endswith((".png", ".jpg", ".jpeg"))]
        if not images:
            continue

        name_map[label_counter] = person_name
        for image_name in images:
            img_path = os.path.join(person_dir, image_name)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is None or img.shape[0] < 100 or img.shape[1] < 100:
                continue
            img = preprocess_face(img)
            faces.append(img)
            labels.append(label_counter)

        print(f"[INFO] {person_name}: {len(images)} imagens válidas")
        label_counter += 1

    if not faces:
        print("[ERROR] Nenhuma imagem válida no dataset.")
        return None, {}

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(labels))
    print(f"[INFO] LBPH treinado com {len(faces)} imagens de {len(name_map)} pessoas.")
    return recognizer, name_map

def camera_handler(shared_data, data_lock):
    streamer = MJPEGStreamer(width=FRAME_WIDTH, height=480, fps=30)
    streamer.start_stream()

    BASE_PATH = os.path.dirname(__file__)
    proto_path = os.path.join(BASE_PATH, "deploy.prototxt.txt")
    model_path = os.path.join(BASE_PATH, "res10_300x300_ssd_iter_140000.caffemodel")

    if not os.path.exists(proto_path) or not os.path.exists(model_path):
        raise FileNotFoundError("Arquivos do modelo DNN não encontrados em Services/Camera")

    dnn_net = cv2.dnn.readNetFromCaffe(proto_path, model_path)

    recognizer, name_map = load_face_recognizer()
    if recognizer is None:
        print("[ERROR] Reconhecedor não inicializado. Saindo...")
        return

    target_name = shared_data.get("main_target", None)

    try:
        while True:
            frame = streamer.get_frame()
            if frame is None:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            (h, w) = frame.shape[:2]

            # DETECÇÃO DE ROSTOS
            blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300),
                                         (104.0, 177.0, 123.0))
            dnn_net.setInput(blob)
            detections = dnn_net.forward()

            faces = []
            for i in range(0, detections.shape[2]):
                conf = detections[0, 0, i, 2]
                if conf > 0.6:
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    (x1, y1, x2, y2) = box.astype("int")
                    if (x2 - x1) > 50 and (y2 - y1) > 50:
                        faces.append((x1, y1, x2 - x1, y2 - y1))

            recognized_faces = []
            target_x = None
            target_found = False

            for (x, y, w_, h_) in faces:
                roi = gray[y:y+h_, x:x+w_]
                if roi.size == 0:
                    continue
                roi = preprocess_face(roi)

                # RECONHECIMENTO
                label_text = "Unknown"
                confidence = 999
                is_recognized = False

                label, pred_confidence = recognizer.predict(roi)
                label_text = name_map.get(label, "Unknown")
                confidence = pred_confidence
                if pred_confidence < 60:  # Limite maior
                    is_recognized = True
                else:
                    label_text = "Unknown"  # Marcar com

                print(f"[DEBUG] Label: {label_text}, Confidence: {pred_confidence}")

                recognized_faces.append((x, y, w_, h_, label_text, confidence, is_recognized))

                # TRACKING do target
                if target_name and label_text == target_name and is_recognized:
                    target_x = x + w_ // 2
                    target_found = True

            with data_lock:
                shared_data["target_x"] = target_x if target_found else None
                shared_data["target_count"] = len(faces)

            # DESENHAR NA TELA
            for (x, y, w_, h_, label_text, confidence, is_recognized) in recognized_faces:
                color = (0, 255, 0) if is_recognized else (0, 0, 255)
                status = "RECONHECIDO" if is_recognized else "DESCONHECIDO"
                cv2.rectangle(frame, (x, y), (x + w_, y + h_), color, 2)
                cv2.putText(frame, f"{label_text} ({confidence:.1f}) {status}",
                            (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            if target_name:
                status_target = "ENCONTRADO" if target_found else "PROCURANDO"
                cv2.putText(frame, f"Target: {target_name} [{status_target}]",
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            cv2.imshow("Face Tracking DEBUG", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        streamer.stop()
        cv2.destroyAllWindows()
