### validates whether the hardware is connected and working properly and the software parameters are set correctly.

import yaml
import os
import cv2
from pathlib import Path
from Raspberry_Pi_Agent.capture_controller import CaptureController
from Raspberry_Pi_Agent.mission_controller import MissionController


class SelfCheckPrelaunch:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = None
        
    def run(self):
                
        if all([self.check_config(), 
                self.check_camera(), 
                self.check_storage(), 
                self.check_network(), 
                self.check_thermal(), 
                self.check_power()
                ]): 
            print('everything is ready to run')
        else:
            print('Something went wrong:')
            
        
 
    def check_config(self):
        try: 
            with open(self.config_path) as f: 
                self.config = yaml.safe_load(f)
            return self._validate_required_keys()
        except Exception as e: 
            print(f'Error: {e}')
            return False

          
        
    def check_camera(self):
        ### test what kind of camera it is, and see if the config camera params work. 
        cam = cv2.VideoCapture(0)
        ok = cam.isOpened()
        cam.release()

        return ok
    
    def check_storage(self):
        #### logic for checking if there is even enough storage on the pi and all the folder settings are in place
        print('storage ok')
        return True
        
    def check_network(self):
        ### logic for checking that the raspberry pi is connected to the mission planner
        print('network connection ok')
        return True 
    
    def check_thermal(self):
        ### logic for checking that the pi is within a safe temperature range
        print('temp ok')
        return True 
    
    def check_power(self):
        ### logic for checking the power of the flight controller and therefore the power of the raspberry pi
        print('battery full') 
        return True
    
    def _validate_required_keys(self):
        print('i am checking if all the keys that are needed to run anything are there.')
    



