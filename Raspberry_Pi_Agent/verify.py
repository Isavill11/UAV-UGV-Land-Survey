### validates whether the hardware is connected and working properly and the software parameters are set correctly.


import yaml
import os
import cv2
from pathlib import Path

import yaml

def load_config(path="config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)