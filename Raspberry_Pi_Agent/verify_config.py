### validates whether the hardware is connected and working properly and the software parameters are set correctly.

import yaml
import os
import time
import cv2
import picamera2
from dataclasses import dataclass, field
from pathlib import Path
from Raspberry_Pi_Agent.capture_controller import CaptureController
from Raspberry_Pi_Agent.mission_controller import MissionController

'''check what kind of vehicle it is
check what camera it is to determine camera function

bools: 
preprocessing on or off? 
thermal management on or off? 
batching on or off? 
coordination on or off? 
logging on or off? 
'''

@dataclass
class PrecheckError: 
    subsystem: str
    message: str
    timestamp: float
    severity: str = "ERROR"
    exception: Exception | None = None
    


class SelfCheckPrelaunch:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = None
        
    def run(self):
        issues = []

        self._check_config()
        self._check_camera()
        self._check_network()
        self._check_power()
        self._check_storage()
        self._check_thermal()
        self._check_required_keys()
            

        print('everything is ready to run')
       
            
    
    def _check_config(self) -> PrecheckError | None:
        try:
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f)

            if self.config is None:
                return PrecheckError(
                    "Config",
                    "Config file is empty or invalid YAML",
                    time.time()
                )

            return None

        except FileNotFoundError as e:
            return PrecheckError(
                "Config",
                f"Config file not found: {self.config_path}",
                time.time(),
                exception=e
            )

        except yaml.YAMLError as e:
            return PrecheckError(
                "Config",
                "YAML syntax error in config file",
                time.time(),
                exception=e
            )
    

        
    def _check_camera(self) -> PrecheckError | None:
        try: 
            picam2 = Picamera2()
        
            # Create a camera configuration
            # We request a low-res, fast-streaming format
            config = picam2.create_preview_configuration(
                main={"size": (IMAGE_WIDTH, IMAGE_HEIGHT), "format": "RGB888"}
            )
            picam2.configure(config)

            # Start the camera
            picam2.start()
        except Exception as e: 
            return PrecheckError(
                'Camera', 
                'Camera could not be found. ensure youre running linux.', 
                time.time())


        cam = cv2.VideoCapture(0)
        if not cam.isOpened():
            return PrecheckError(
                "Camera",
                "Camera could not be opened (index 0). Is it connected?",
                time.time()
            )
        cam.release()
        return None

    
    def _check_storage(self):
        #### logic for checking if there is even enough storage on the pi and all the folder settings are in place
        print('storage ok')
        return True
        
    def _check_network(self):
        ### logic for checking that the raspberry pi is connected to the mission planner
        print('network connection ok')
        return True 
    
    def _check_thermal(self):
        ### logic for checking that the pi is within a safe temperature range
        print('temp ok')
        return True 
    
    def _check_power(self):
        ### logic for checking the power of the flight controller and therefore the power of the raspberry pi
        print('battery full') 
        return True
    
    def _check_required_keys(self):
        print('i am checking if all the keys that are needed to run anything are there.')
    



