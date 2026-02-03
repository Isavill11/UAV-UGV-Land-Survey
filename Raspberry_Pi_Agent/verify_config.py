### validates whether the hardware is connected and working properly and the software parameters are set correctly.

import yaml
import os
import time
import cv2
import platform
from picamera2 import Picamera2 # The raspi camera library
from dataclasses import dataclass
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
        self.ready = False
        self.required_keys = [['platform', 'name', 'id'], ['camera', 'id', 'dimensions', 'capturing_profiles'], ['storage', 'local_path'],
                              ['batching'], ['thermal_management', 'thresholds_c', 'policies'], ['battery_status']]
        
    def run(self):
        issues = []

        config_error = self._check_config()
        if config_error: 
            self.ready = False
            return[config_error]

        required_keys = self._check_required_keys() ### maybe return dict with all the keys, and a 1 if the key is there and a 0 if it is not. then on the other checks, pass the required keys dict and it will determine whether to even check for it or not. 


        for check in [
        self._check_camera,
        self._check_network,
        self._check_power,
        self._check_storage,
        self._check_thermal,
        ]: 
            error = check()
            if error: 
                issues.append(error)
      
        fatal = [e for e in issues if e.severity == "ERROR"]
        self.ready = len(fatal) == 0


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
        os = platform.system()
        cam_res = self.config['camera']['dimensions']

        if os == 'Linux': 
            try: 
                picam2 = Picamera2()
                conf = picam2.create_preview_configuration(
                    main={"size": (cam_res), "format": "RGB888"}
                )
                picam2.configure(conf)
                picam2.start()
                frame = picam2.capture_array()
                picam2.stop()
                if frame == None: 
                    return PrecheckError(
                        'Camera', 
                        'Picam2 is not responding.', 
                        time.time())
                return None

            except Exception as e: 
                return PrecheckError(
                    'Camera', 
                    'Camera could not be found. Ensure proper connection. Try rebooting.', 
                    time.time())

        elif os == 'Windows': 
            cam = cv2.VideoCapture(0)
            if not cam.isOpened():
                return PrecheckError(
                    "Camera",
                    "Windows webcam checked instead of Picam2 (index = 0).",
                    time.time()
                )
            cam.release()
            print('Windows webcam checked instead of Picam.')
            return None

    
    def _check_storage(self):
        #### logic for checking if there is even enough storage on the pi and all the folder settings are in place

        self.config 


        print('storage ok')
        return True
        
    def _check_network(self):
        ### logic for checking that the raspberry pi is connected to the mission planner
        print('network connection ok')
        return True 
    
    def _check_thermal(self, required_keys):
        if required_keys['thermal' == 0]: 
            pass

        ### logic for checking that the pi is within a safe temperature range
        print('temp ok')
        return True 
    
    def _check_power(self):
        ### logic for checking the power of the flight controller and therefore the power of the raspberry pi
        print('battery full') 
        return True
    
    def _check_required_keys(self):
        print('i am checking if all the keys that are needed to run anything are there.')
    



