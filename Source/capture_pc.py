import cv2
import os

# ============================
# CONFIGURAÇÃO
# ============================
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
IMG_W, IMG_H = 300, 300

# ============================
# FUNÇÃO PRINCIPAL
# ============================
def capture_dataset():
    person_name = input("Digite o nome da pessoa: ").strip()
    if not person_name:
        print("Nome inválido!")
        return

    # Cria pasta do dataset
    dataset_path = os.path.join(os.path.dirname(__file__),"Services", "Camera", "Dataset", person_name)
    os.makedirs(dataset_path, exist_ok=True)

    # Inicializa câmera
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    if not cap.isOpened():
        print("Erro ao abrir a câmera!")
        return

    # Carrega o classificador de rosto
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    count = 0
    print("Pressione ESPAÇO para capturar, 'q' para sair")

    try:
        while count < 40:
            ret, frame = cap.read()
            if not ret:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4)

            # Desenha retângulos em todos os rostos detectados
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # Mostra informações
            cv2.putText(frame, f"Fotos: {count}/30 - {person_name}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("Capture Dataset", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):  # Captura com ESPAÇO
                if len(faces) == 1:
                    x, y, w, h = faces[0]
                    face_img = gray[y:y+h, x:x+w]
                    face_img = cv2.resize(face_img, (IMG_W, IMG_H))
                    filename = os.path.join(dataset_path, f"{person_name}_{count:03d}.jpg")
                    cv2.imwrite(filename, face_img)
                    count += 1
                    print(f"Capturada: {filename}")
                else:
                    print("Capture exatamente UM rosto!")
            elif key == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Captura finalizada.")

# ============================
# EXECUÇÃO
# ============================
if __name__ == "__main__":
    capture_dataset()
