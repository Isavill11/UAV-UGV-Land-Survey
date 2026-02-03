from capture_controller import CaptureController
from mission_controller import MissionController


class SystemBuilder: 
    def __init__(self, config):
        self.config = config

    def build(self): 
        capture = CaptureController(self.config['capture_profiles'])
        mission = MissionController(self.config, capture)

        return mission, capture