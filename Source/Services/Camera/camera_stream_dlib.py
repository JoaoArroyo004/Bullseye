#!/usr/bin/env python3
import cv2
import subprocess
import numpy as np
import time
from threading import Thread
from queue import Queue, Empty

class MJPEGStreamer:
    """
    Classe para capturar vídeo MJPEG usando libcamera-vid.
    Usa subprocess e decodifica frames em tempo real com OpenCV.
    """

    def __init__(self, width=640, height=480, fps=30):
        self.width = width
        self.height = height
        self.fps = fps
        self.running = False
        self.frame_queue = Queue(maxsize=10)
        self.process = None
        self.thread = None

    def start_stream(self):
        """Inicia o stream de vídeo"""
        if self.running:
            return

        self.running = True
        cmd = [
            'libcamera-vid', '-t', '0',
            '--width', str(self.width),
            '--height', str(self.height),
            '--framerate', str(self.fps),
            '--codec', 'mjpeg',
            '--quality', '90',
            '--output', '-'
        ]

        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=0)
        self.thread = Thread(target=self._read_frames, daemon=True)
        self.thread.start()

    def _read_frames(self):
        """Thread que lê os frames MJPEG e os decodifica"""
        buffer = b''

        while self.running and self.process.poll() is None:
            data = self.process.stdout.read(65536)
            if not data:
                time.sleep(0.01)
                continue

            buffer += data
            start_marker = b'\xff\xd8'
            end_marker = b'\xff\xd9'

            while True:
                start_pos = buffer.find(start_marker)
                end_pos = buffer.find(end_marker, start_pos + 2)

                if start_pos == -1 or end_pos == -1:
                    break

                jpeg_data = buffer[start_pos:end_pos + 2]
                buffer = buffer[end_pos + 2:]

                frame = cv2.imdecode(np.frombuffer(jpeg_data, np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    if not self.frame_queue.full():
                        self.frame_queue.put(frame)
                    else:
                        try:
                            self.frame_queue.get_nowait()
                        except:
                            pass
                        self.frame_queue.put(frame)

    def get_frame(self, timeout=0.1):
        """Retorna o frame mais recente, ou None se não houver"""
        try:
            return self.frame_queue.get(timeout=timeout)
        except Empty:
            return None

    def stop(self):
        """Encerra o stream e libera recursos"""
        self.running = False
        if self.process:
            self.process.terminate()
            self.process.wait()
        if self.thread:
            self.thread.join()
