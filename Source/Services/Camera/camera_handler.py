import cv2
from Services.Camera.camera_stream import MJPEGStreamer

FRAME_WIDTH = 640

def camera_handler(shared_data, data_lock):
    """
    Thread que lê a câmera e atualiza shared_data com target_x
    """
    streamer = MJPEGStreamer(width=FRAME_WIDTH, height=480, fps=30)
    streamer.start_stream()
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    CENTER_X = FRAME_WIDTH // 2

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

                with data_lock:
                    shared_data["target_x"] = center_x
                    shared_data["target_count"] = len(faces)
                
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0,255,0), 2)
                cv2.putText(frame, f"x={center_x}", (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

            cv2.imshow("Tracking", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        streamer.stop()
        cv2.destroyAllWindows()
