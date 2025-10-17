#!/usr/bin/env python3

import cv2
import subprocess
import numpy as np
import time
import os
from threading import Thread
from queue import Queue, Empty

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

def main():
    print("=== CSI Camera - Python High FPS ===")
    
    streamer = MJPEGStreamer(640, 480, 30)
    streamer.start_stream()
    
    print("Stream iniciado. Pressione 'q' para sair.")
    
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            frame = streamer.get_frame()
            if frame is not None:
                frame_count += 1
                
                # Calcular FPS
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                
                # Overlay
                fps_text = f"FPS: {fps:.1f}"
                cv2.putText(frame, fps_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, "Press 'q' to quit", (10, frame.shape[0] - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                cv2.imshow("CSI Camera - Python", frame)
                
                # Reset counter a cada 2 segundos
                if elapsed >= 2:
                    frame_count = 0
                    start_time = time.time()
            
            # Verificar tecla
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    finally:
        streamer.stop()
        cv2.destroyAllWindows()
        print("Stream finalizado")

if __name__ == "__main__":
    main()