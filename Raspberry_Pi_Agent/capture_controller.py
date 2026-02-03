### takes the image from the camera and saves it to a file with metadata
import cv2
import time
import os
from datetime import datetime
from enum import Enum
from Raspberry_Pi_Agent.main import MissionController

class CaptureState(Enum):
    OFF = 0
    ACTIVE = 1
    DEGRADED = 2

### TODO: add new args to init from config file, such as resolution, file type, capture rate, camera type

class CaptureController:
    def __init__(self, capture_profiles, camera_index=0):
        self.camera_index = camera_index
        self.camera = None
        self.state = CaptureState.OFF
        self.last_capture = 0.0

        self.capture_profiles = capture_profiles
        self.active_profile = None

        self.interval = 1.0
        self.jpeg_quality = 90
        self.save_dir = "captured_images"

    # lifecycle. Right now its only using cv2 to capture. we need to add py2cam or whatever for linux.
    def start(self):
        if self.camera is None:
            self.camera = cv2.VideoCapture(self.camera_index)
            if not self.camera.isOpened():
                raise RuntimeError("Could not open camera")
        self.state = CaptureState.ACTIVE

    def stop(self):
        if self.camera is not None:
            self.camera.release()
            self.camera = None
        self.state = CaptureState.OFF

    # state-based config 
    def apply_profile(self, state_name: str):
        profile = self.capture_profiles[state_name]
        self.interval = profile["interval"]
        self.jpeg_quality = profile["jpeg_quality"]
        self.save_dir = profile["save_dir"]
        os.makedirs(self.save_dir, exist_ok=True)

    def update(self):
        if self.state == CaptureState.OFF:
            return

        now = time.time()
        if now - self.last_capture < self.interval:
            return

        self._capture_frame()
        self.last_capture = now

    def _capture_frame(self):
        ret, frame = self.camera.read()
        if not ret:
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.save_dir, f"img_{ts}.jpg")

        cv2.imwrite(
            path,
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
        )
