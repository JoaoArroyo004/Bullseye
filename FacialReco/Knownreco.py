#!/usr/bin/env python3

import cv2
import subprocess
import numpy as np
import time
import os
import numpy as np
from threading import Thread, Lock
from queue import Queue, Empty

data_path = 'dataset' # Folder containing subfolders for each person

faces = []
labels = []
name_map = {}
label_counter = 0

frame_count = 0
start_time = 0.0
running = True

# Prepare training data
for person_name in os.listdir(data_path):
    person_dir = os.path.join(data_path, person_name)
    if os.path.isdir(person_dir):
        name_map[label_counter] = person_name
        for image_name in os.listdir(person_dir):
            image_path = os.path.join(person_dir, image_name)
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                faces.append(img)
                labels.append(label_counter)
        label_counter += 1

# Train the LBPH Face Recognizer
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.train(faces,np.array(labels))

# Face detection cascade (for detecting faces in new images)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')


class MJPEGStreamer:
    def __init__(self, width=640, height=480, fps=30):
        self.width = width
        self.height = height
        self.fps = fps
        self.running = False
        self.frame_queue = Queue(maxsize=10)
        
    def start_stream(self):
        self.running = True
        
        # Comando libcamera-vid
        cmd = [
            'libcamera-vid', '-t', '0',
            '--width', str(self.width),
            '--height', str(self.height),
            '--framerate', str(self.fps),
            '--codec', 'mjpeg',
            '--quality', '90',
            '--output', '-'
        ]
        
        # Iniciar processo
        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=0)
        
        # Thread para ler frames
        self.thread = Thread(target=self._read_frames)
        self.thread.start()
        
    def _read_frames(self):
        buffer = b''
        frame_count = 0
        
        while self.running and self.process.poll() is None:
            # Ler dados
            data = self.process.stdout.read(4096)
            if not data:
                time.sleep(0.01)
                continue
                
            buffer += data
            
            # Procurar por frames JPEG
            start_marker = b'\xff\xd8'
            end_marker = b'\xff\xd9'
            
            while len(buffer) > 0:
                start_pos = buffer.find(start_marker)
                if start_pos == -1:
                    buffer = b''
                    break
                    
                end_pos = buffer.find(end_marker, start_pos)
                if end_pos == -1:
                    break
                    
                # Frame completo encontrado
                jpeg_data = buffer[start_pos:end_pos + 2]
                buffer = buffer[end_pos + 2:]
                
                # Decodificar JPEG
                frame = cv2.imdecode(np.frombuffer(jpeg_data, np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    if not self.frame_queue.full():
                        self.frame_queue.put(frame)
                    frame_count += 1

    def get_frame(self, timeout=0.1):
        try:
            return self.frame_queue.get(timeout=timeout)
        except Empty:
            return None
            
    def stop(self):
        self.running = False
        if hasattr(self, 'process'):
            self.process.terminate()
            self.process.wait()
        if hasattr(self, 'thread'):
            self.thread.join()

# Shared frame for display
display_frame = None
frame_lock = Lock()

def detect_bounding_box(streamer):
    global display_frame, running
    while running:
        frame = streamer.get_frame()
        if frame is not None:
            gray_image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray_image, 1.1, 10, minSize=(40, 40))
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 4)
                face_roi = gray_image[y:y+h, x:x+w]
                label, confidence = recognizer.predict(face_roi)

                if confidence < 50:
                    recognized_name = name_map[label]
                    print(f"Recognized: {recognized_name} with confidence {confidence}")
                    # Add name to frame
                    cv2.putText(frame, recognized_name, (x, y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                else:
                    print(f"Unknown face with confidence {confidence}")
                    cv2.putText(frame, "Unknown", (x, y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            
            # Update display frame
            with frame_lock:
                display_frame = frame.copy()

def main():
    global running, frame_count, start_time, display_frame
    
    print("=== CSI Camera - Python High FPS ===")
    
    streamer = MJPEGStreamer(640, 480, 60)
    streamer.start_stream()
    
    print("Stream iniciado. Pressione 'q' para sair.")
    
    frame_count = 0
    start_time = time.time()
    running = True
    
    # Start only the detection thread
    thread_detect = Thread(target=detect_bounding_box, args=(streamer,))
    thread_detect.start()
    
    try:
        # Main thread handles OpenCV display
        while running:
            frame_to_show = None
            
            # Get the latest processed frame
            with frame_lock:
                if display_frame is not None:
                    frame_to_show = display_frame.copy()
            
            if frame_to_show is not None:
                frame_count += 1

                # Calculate FPS
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                
                # Add FPS overlay
                fps_text = f"FPS: {fps:.1f}"
                cv2.putText(frame_to_show, fps_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame_to_show, "Press 'q' to quit", (10, frame_to_show.shape[0] - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # Display in main thread
                cv2.imshow("CSI Camera - Python", frame_to_show)
                
                # Reset counter every 2 seconds
                if elapsed >= 2:
                    frame_count = 0
                    start_time = time.time()
            
            # Check for 'q' key press
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                running = False
                break
                
    except KeyboardInterrupt:
        running = False
        print("Interrupted by user")
    finally:
        running = False
        streamer.stop()
        cv2.destroyAllWindows()
        thread_detect.join(timeout=2.0)
        print("Stream finalizado")

if __name__ == "__main__":
    main()