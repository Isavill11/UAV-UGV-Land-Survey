### takes the image from the camera and saves it to a file with metadata
import cv2
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
    def __init__(self, config, image_manager=None):
        camera_cfg = config["camera"]

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
        """Start capturing images"""
        try:
            if self.camera is None:
                self.camera = cv2.VideoCapture(self.camera_index)
                if not self.camera.isOpened():
                    logger.error(f"Could not open camera {self.camera_index}")
                    return False
            
            self.state = CaptureState.ACTIVE
            logger.info(f"Camera started - profile: {self.active_profile}")
            return True
        except Exception as e:
            logger.error(f"Failed to start camera: {e}")
            return False

    def stop(self):
        """Stop capturing images"""
        try:
            if self.camera is not None:
                self.camera.release()
                self.camera = None
            self.state = CaptureState.OFF
            logger.info("Camera stopped")
        except Exception as e:
            logger.error(f"Error stopping camera: {e}")

    # state-based config 
    def apply_profile(self, profile_name: str) -> bool:
        """Apply a capture profile (CAPTURING, DEGRADED, CRITICAL)"""
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
        """Update capture controller - call regularly to capture frames"""
        if self.state == CaptureState.OFF:
            return

        now = time.time()
        if now - self.last_capture < self.interval:
            return

        self._capture_frame()
        self.last_capture = now

    def _capture_frame(self):
        """Capture and save a single frame"""
        try:
            if self.camera is None:
                logger.warning("Camera not initialized")
                return False
            
            ret, frame = self.camera.read()
            if not ret:
                logger.error("Failed to capture frame")
                return False

            # Encode to JPEG bytes
            success, jpg_data = cv2.imencode('.jpg', frame, 
                                            [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality])
            
            if not success:
                logger.error("Failed to encode image")
                return False
            
            image_bytes = jpg_data.tobytes()
            
            # Save via image manager if available
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
        """Update current drone altitude for image metadata"""
        self.current_altitude = altitude
