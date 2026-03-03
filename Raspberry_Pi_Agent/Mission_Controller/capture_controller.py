### takes the image from the camera and saves it to a file with metadata
import cv2

try: 
    from picamera2 import Picamera2
except ImportError:
    Picamera2 = None

import time
import os
import logging
from datetime import datetime
from enum import Enum
from typing import Optional
import io

logger = logging.getLogger(__name__)

class CaptureState(Enum):
    OFF = 0
    ACTIVE = 1
    DEGRADED = 2

### TODO: add new args to init from config file, such as resolution, file type, capture rate, camera type

class CaptureController:
    def __init__(self, config, image_manager=None, os="Windows"):
        camera_cfg = config["camera"]

        self.os = os
        self.camera_index = camera_cfg["id"]
        self.capture_profiles = camera_cfg["capture_profiles"]
        self.dimensions = camera_cfg["dimensions"]

        self.state = CaptureState.OFF
        self.active_profile = None 
        self.interval = 0.0
        self.jpeg_quality = 90
        self.save_dir = None
        self.last_capture = 0.0
        self.camera = None
        
        # Image manager for storage and transmission
        self.image_manager = image_manager
        
        # Track drone state for metadata
        self.current_altitude = 0.0
        
        logger.info(f"CaptureController initialized (camera index: {self.camera_index})")


    # lifecycle. Right now its only using cv2 to capture. we need to add py2cam or whatever for linux.
    def start(self):
        try:
            if self.os.lower() == "windows":
                logger.info("Starting camera using OpenCV backend (Windows)")
                self.backend = "opencv"
                self.camera = cv2.VideoCapture(self.camera_index)

                if not self.camera.isOpened():
                    logger.error(f"Could not open camera {self.camera_index}")
                    self.state = CaptureState.DEGRADED
                    return False

            elif self.os.lower() == "linux":
                if Picamera2 is None:
                    logger.error("Picamera2 not available on this system")
                    self.state = CaptureState.DEGRADED
                    return False

                logger.info("Starting camera using Picamera2 backend (Linux)")
                self.backend = "picamera2"
                self.camera = Picamera2()

                conf = self.camera.create_still_configuration(
                    main={
                        "size": (
                            self.dimensions["width"],
                            self.dimensions["height"]
                        ),
                        "format": "RGB888"
                    }
                )
                self.camera.configure(conf)
                self.camera.start()
                self.camera.stop()

            else:
                logger.error(f"Unsupported OS: {self.os}")
                return False

            self.state = CaptureState.ACTIVE
            return True

        except Exception as e:
            logger.error(f"Failed to start camera: {e}")
            self.state = CaptureState.DEGRADED
            return False



    def stop(self):
        try:
            if self.camera is not None:
                if self.backend == "opencv":
                    self.camera.release()

                elif self.backend == "picamera2":
                    self.camera.stop()
                    self.camera.close()

                self.camera = None

            self.state = CaptureState.OFF
            logger.info("Camera stopped")

        except Exception as e:
            logger.error(f"Error stopping camera: {e}")
        
    # state-based config 
    def apply_profile(self, profile_name: str) -> bool:
        try:
            if profile_name not in self.capture_profiles:
                logger.error(f"Unknown profile: {profile_name}")
                return False
            
            profile = self.capture_profiles[profile_name]
            self.interval = profile["interval"]
            self.jpeg_quality = profile["jpeg_quality"]
            self.save_dir = profile["save_dir"]
            self.active_profile = profile_name
            
            logger.debug(f"Applied profile {profile_name}: interval={self.interval}s, quality={self.jpeg_quality}%")
            return True
        except Exception as e:
            logger.error(f"Failed to apply profile {profile_name}: {e}")
            return False

    def update(self):
        if self.state == CaptureState.OFF:
            return

        now = time.time()
        if now - self.last_capture < self.interval:
            return

        self._capture_frame()
        self.last_capture = now

    def _capture_frame(self):
        try:
            if self.camera is None:
                logger.warning("Camera not initialized")
                return False

            if self.backend == "opencv":
                ret, frame = self.camera.read()
                self.camera.imshow('Live opencv video', cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                if not ret:
                    logger.error("Failed to capture frame (OpenCV)")
                    return False

            elif self.backend == "picamera2":
                frame = self.camera.capture_array()
                self.camera.imshow('Live picamera video', cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

                if frame is None:
                    logger.error("Failed to capture frame (Picamera2)")
                    return False

            else:
                logger.error("Unknown camera backend")
                return False

            success, jpg_data = cv2.imencode(
                ".jpg",
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
            )

            if not success:
                logger.error("Failed to encode image")
                return False

            image_bytes = jpg_data.tobytes()
                        
            if self.image_manager:
                filename = self.image_manager.save_captured_image(
                    image_bytes,
                    profile=self.active_profile or "CAPTURING",
                    altitude=self.current_altitude
                )
                if filename:
                    logger.debug(f"Captured and stored: {filename}")
                    return True
            
            # Fallback: save to local directory
            if self.save_dir:
                if not os.path.exists(self.save_dir):
                    os.makedirs(self.save_dir, exist_ok=True)

                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                path = os.path.join(self.save_dir, f"img_{ts}.jpg")

                with open(path, 'wb') as f:
                    f.write(image_bytes)
                
                logger.debug(f"Captured: {path}")
                return True
            
            return False
                
        except Exception as e:
            logger.error(f"Capture error: {e}")
            return False
    
    def set_altitude(self, altitude: float):
        self.current_altitude = altitude
