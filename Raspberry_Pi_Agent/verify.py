### validates whether the hardware is connected and working properly and the software parameters are set correctly.


from logging import config
import yaml
import os
import cv2
from pathlib import Path

import yaml

class SystemState:
    def __init__(self):
        self.config_valid = self.check_config()
        
    def is_system_ready(self):
        config_ok = self.config_valid
        camera_check = self.check_camera()
        storage_ok = self.check_storage()
        network_ok = self.check_network()
        thermal_ok = self.check_thermal()
        power_ok = self.check_power()
        print(all([camera_ok, storage_ok, config_ok, network_ok, thermal_ok, power_ok]))
        
        
        
    def check_config(self):
        config_path = Path("config.yaml")

        if not config_path.is_file():
            print("Config file not found")
            return False
        try:
            with open(config_path, "r") as f:
                self.config = yaml.safe_load(f)

            print("Loaded config:")
            print(yaml.dump(self.config, sort_keys=False))
            return True

        except Exception as e:
            print(f"Error reading config file: {e}")
            return False

        
    def check_camera(self):
        print('ok')
    
    def check_storage(self):
        print('ok')
        
    def check_network(self):
        print('ok')
        
    def check_thermal(self):
        print('ok')
        
    def check_power(self):
        print('ok')    
        
        
        
SystemState().check_config()

