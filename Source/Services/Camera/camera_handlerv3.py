import cv2
import os
import numpy as np
import time
from facenet_pytorch import MTCNN, InceptionResnetV1
import torch
from Services.Camera.camera_stream_pc import MJPEGStreamer

# Configurações
FRAME_WIDTH = 640
DATASET_PATH = os.path.join(os.path.dirname(__file__), "Dataset")

IMG_W = 500
IMG_H = 500

# Inicializando a MTCNN (detecção de rostos) e o InceptionResnetV1 (FaceNet)
mtcnn = MTCNN(keep_all=True)
facenet = InceptionResnetV1(pretrained='vggface2').eval()

# Verifica se há GPU disponível e move o modelo para a GPU, caso exista
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
mtcnn = mtcnn.to(device)
facenet = facenet.to(device)

def preprocess_face(img_gray):
    """Pré-processamento simples"""
    img = cv2.resize(img_gray, (IMG_W, IMG_H))
    img = cv2.GaussianBlur(img, (3, 3), 0)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    img = clahe.apply(img)
    img = cv2.equalizeHist(img)
    return img

def load_face_recognizer():
    """Carregar e preparar embeddings do FaceNet"""
    face_embeddings = []
    name_map = {}

    for person_name in os.listdir(DATASET_PATH):
        person_dir = os.path.join(DATASET_PATH, person_name)
        if not os.path.isdir(person_dir):
            continue

        images = [f for f in os.listdir(person_dir) if f.endswith((".png", ".jpg", ".jpeg"))]
        if not images:
            continue

        # Extrair o embedding de cada imagem do dataset
        embeddings = []
        for image_name in images:
            img_path = os.path.join(person_dir, image_name)
            img = cv2.imread(img_path)
            if img is None:
                continue
            faces = mtcnn(img)  # Detecta os rostos na imagem
            if faces is not None:
                for face in faces:
                    embedding = facenet(face.unsqueeze(0))  # Adiciona a dimensão de batch

                    # Agora, separa o tensor do gráfico de computação e converte para numpy
                    embedding = embedding.detach().cpu().numpy()  # Desvincula e move para a CPU
                    embeddings.append(embedding)

        if embeddings:
            face_embeddings.append(np.array(embeddings))  # Adiciona os embeddings da pessoa
            name_map[len(face_embeddings)-1] = person_name  # Mapeia o índice da pessoa
        print(f"[INFO] {person_name}: {len(images)} imagens válidas")

    if not face_embeddings:
        print("[ERROR] Nenhuma imagem válida no dataset.")
        return None, {}

    print(f"[INFO] {len(face_embeddings)} pessoas carregadas com sucesso.")
    return face_embeddings, name_map

def camera_handler(shared_data, data_lock):
    streamer = MJPEGStreamer(width=FRAME_WIDTH, height=480, fps=30)
    streamer.start_stream()

    # Carregar embeddings do dataset
    face_embeddings, name_map = load_face_recognizer()
    if not face_embeddings:
        print("[ERROR] Reconhecedor não inicializado. Saindo...")
        return

    target_name = shared_data.get("main_target", None)

    try:
        while True:
            frame = streamer.get_frame()
            if frame is None:
                continue  # Se o quadro for None, pule para o próximo

            # Detecção de rostos com MTCNN
            faces = mtcnn(frame)  # Detecta rostos no quadro
            if faces is None or len(faces) == 0:
                # Se não houver rostos detectados, continue para o próximo quadro
                with data_lock:
                    shared_data["target_x"] = None
                    shared_data["target_count"] = 0
                continue

            recognized_faces = []
            target_x = None
            target_found = False

            for face in faces:
                # Extrai o rosto da imagem e gera o embedding
                embedding = facenet(face.unsqueeze(0))  # Adiciona a dimensão de batch

                # Comparando o embedding do rosto com os embeddings do dataset
                label_text = "Unknown"
                min_distance = float("inf")

                for idx, person_embeddings in enumerate(face_embeddings):
                    for db_embedding in person_embeddings:
                        if isinstance(db_embedding, torch.Tensor):
                            db_embedding = db_embedding.detach().cpu().numpy()  # Converte db_embedding para numpy

                        distance = np.linalg.norm(embedding.detach().cpu().numpy() - db_embedding)
                        if distance < min_distance:
                            min_distance = distance
                            label_text = name_map[idx]  # A pessoa com a menor distância

                # Se a distância for suficientemente baixa, consideramos o rosto como reconhecido
                is_recognized = min_distance < 0.9  # Ajuste o valor para melhorar a precisão
                confidence = min_distance  # A confiança é inversamente proporcional à distância

                recognized_faces.append((label_text, confidence, is_recognized))

                if target_name and label_text == target_name and is_recognized:
                    target_x = face[0, 0]  # Posição do rosto detectado
                    target_found = True

            # Atualizar dados compartilhados
            with data_lock:
                shared_data["target_x"] = target_x if target_found else None
                shared_data["target_count"] = len(faces)

            # Mostrar as informações de reconhecimento na tela
            for label_text, confidence, is_recognized in recognized_faces:
                color = (0, 255, 0) if is_recognized else (0, 0, 255)
                status = "RECONHECIDO" if is_recognized else "DESCONHECIDO"
                print(f"[DEBUG] Label: {label_text}, Confidence: {confidence}")

            # Exibir as informações na tela do OpenCV
            cv2.imshow("Face Tracking DEBUG", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break


    finally:
        streamer.stop()
        cv2.destroyAllWindows()
