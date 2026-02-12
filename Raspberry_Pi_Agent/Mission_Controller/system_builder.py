from Raspberry_Pi_Agent.Mission_Controller.capture_controller import CaptureController
from Raspberry_Pi_Agent.Mission_Controller.mission_controller import MissionController


class SystemBuilder: 
    def __init__(self, config):
        self.config = config

    def build(self): 
        capture = CaptureController(self.config['capture_profiles'])
        mission = MissionController(self.config, capture)

        return mission, capture