# Services/Camera/camera_stream_pc.py
import cv2
from threading import Thread
from queue import Queue, Empty
import time

class MJPEGStreamer:
    """
    Versão para PC usando webcam normal (OpenCV VideoCapture)
    """

    def __init__(self, width=640, height=480, fps=30, cam_index=0):
        self.width = width
        self.height = height
        self.fps = fps
        self.cam_index = cam_index
        self.running = False
        self.frame_queue = Queue(maxsize=10)
        self.cap = None
        self.thread = None

    def start_stream(self):
        if self.running:
            return
        self.running = True
        self.cap = cv2.VideoCapture(self.cam_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.thread = Thread(target=self._read_frames, daemon=True)
        self.thread.start()

    def _read_frames(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue
            if not self.frame_queue.full():
                self.frame_queue.put(frame)
            else:
                try:
                    self.frame_queue.get_nowait()
                except:
                    pass
                self.frame_queue.put(frame)

    def get_frame(self, timeout=0.1):
        try:
            return self.frame_queue.get(timeout=timeout)
        except Empty:
            return None

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        if self.cap:
            self.cap.release()
