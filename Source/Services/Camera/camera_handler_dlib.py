import cv2
import numpy as np
import time
from threading import Lock
from Services.Camera.camera_stream import MJPEGStreamer
import dlib
from pathlib import Path

# ============================
# CONFIGURAÇÕES
# ============================
FRAME_WIDTH = 640
DATASET_PATH = "dataset"

# ============================
# FILTRO TEMPORAL
# ============================
class FaceRecognitionFilter:
    """Filtro temporal para estabilizar reconhecimento"""
    def __init__(self, buffer_size=5):
        self.buffer_size = buffer_size
        self.buffer = {}
        
    def add_prediction(self, face_id, label, confidence):
        if face_id not in self.buffer:
            self.buffer[face_id] = []
            
        self.buffer[face_id].append((label, confidence))
        if len(self.buffer[face_id]) > self.buffer_size:
            self.buffer[face_id].pop(0)
            
    def get_filtered_prediction(self, face_id):
        if face_id not in self.buffer or not self.buffer[face_id]:
            return "Unknown", 999
            
        labels = [pred[0] for pred in self.buffer[face_id]]
        most_common = max(set(labels), key=labels.count)
        
        confidences = [pred[1] for pred in self.buffer[face_id] if pred[0] == most_common]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 999
            
        return most_common, avg_confidence

# ============================
# CARREGANDO DATASET DLIB
# ============================
detector = dlib.get_frontal_face_detector()
sp = dlib.shape_predictor("models/shape_predictor_5_face_landmarks.dat")
facerec = dlib.face_recognition_model_v1("models/dlib_face_recognition_resnet_model_v1.dat")

known_embeddings = []
known_names = []

for person_dir in Path(DATASET_PATH).iterdir():
    if not person_dir.is_dir():
        continue
    person_name = person_dir.name
    for img_path in person_dir.iterdir():
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        faces = detector(rgb_img, 1)
        for face in faces:
            shape = sp(rgb_img, face)
            embedding = facerec.compute_face_descriptor(rgb_img, shape)
            known_embeddings.append(np.array(embedding))
            known_names.append(person_name)

known_embeddings = np.array(known_embeddings)

# ============================
# FUNÇÃO DE RECONHECIMENTO
# ============================
def recognize_face(face_img):
    rgb_img = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
    faces = detector(rgb_img, 1)
    if len(faces) == 0:
        return "Unknown", 999

    shape = sp(rgb_img, faces[0])
    embedding = np.array(facerec.compute_face_descriptor(rgb_img, shape))

    if len(known_embeddings) == 0:
        return "Unknown", 999

    distances = np.linalg.norm(known_embeddings - embedding, axis=1)
    min_idx = np.argmin(distances)
    if distances[min_idx] < 0.6:
        return known_names[min_idx], distances[min_idx]
    return "Unknown", distances[min_idx]

# ============================
# LOOP PRINCIPAL
# ============================
def camera_handler(shared_data, data_lock):
    streamer = MJPEGStreamer(width=FRAME_WIDTH, height=480, fps=30)
    streamer.start_stream()

    recognition_filter = FaceRecognitionFilter(buffer_size=7)
    frame_count = 0
    start_time = time.time()
    target_name = shared_data.get("main_target", None)

    try:
        while True:
            frame = streamer.get_frame()
            if frame is None:
                continue

            (h, w) = frame.shape[:2]
            recognized_faces = []
            target_found = False
            target_x = None

            # ============================
            # DETECÇÃO DE ROSTOS (DLIB)
            # ============================
            faces = detector(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), 1)
            for face in faces:
                x, y, x2, y2 = face.left(), face.top(), face.right(), face.bottom()
                x, y = max(0, x), max(0, y)
                x2, y2 = min(w, x2), min(h, y2)
                roi = frame[y:y2, x:x2]

                label, confidence = recognize_face(roi)
                face_id = f"{x//20}_{y//20}"
                recognition_filter.add_prediction(face_id, label, confidence)
                label_text, confidence = recognition_filter.get_filtered_prediction(face_id)
                is_recognized = label_text != "Unknown"

                recognized_faces.append((x, y, x2-x, y2-y, label_text, confidence, is_recognized))

            # ============================
            # TRACKING DO TARGET
            # ============================
            with data_lock:
                targets = shared_data.get("current_targets", [])

            for (x, y, w_, h_, label_text, confidence, is_recognized) in recognized_faces:
                if label_text == target_name and is_recognized:
                    center_x = x + w_ // 2
                    target_x = center_x
                    target_found = True
                    break

            with data_lock:
                shared_data["target_x"] = target_x if target_found else None
                shared_data["target_count"] = len(faces)

            # ============================
            # DESENHO NA TELA
            # ============================
            for (x, y, w_, h_, label_text, confidence, is_recognized) in recognized_faces:
                if is_recognized:
                    color = (0, 255, 0) if label_text == target_name else (255, 255, 0)
                    status = "RECONHECIDO"
                else:
                    color = (0, 0, 255)
                    status = "DESCONHECIDO"

                cv2.rectangle(frame, (x, y), (x + w_, y + h_), color, 2)
                cv2.putText(frame, f"{label_text} ({confidence:.2f}) {status}",
                            (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            # FPS
            frame_count += 1
            elapsed = time.time() - start_time
            if elapsed >= 1:
                fps = frame_count / elapsed
                frame_count = 0
                start_time = time.time()
                cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            if target_name:
                status_target = "ENCONTRADO" if target_found else "PROCURANDO"
                cv2.putText(frame, f"Target: {target_name} [{status_target}]", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            cv2.imshow("Face Tracking", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        streamer.stop()
        cv2.destroyAllWindows()
