## MAIN LOOP DECISION MAKING FOR RASPI AGENT 
import logging
from enum import Enum, auto

from Raspberry_Pi_Agent.verify_config import SelfCheckPrelaunch
from Raspberry_Pi_Agent.Mission_Controller.mission_controller import MissionController
from Raspberry_Pi_Agent.Mission_Controller.capture_controller import CaptureController
from Raspberry_Pi_Agent.Mission_Controller.health import (
    DroneHealth, 
    LinkHealth, 
    PiHealth, 
    SystemHealth
)

def main():
    
    check = SelfCheckPrelaunch('C:\Users\isav3\VSCode Projects\UAV-UGV-Land-Survey\Raspberry_Pi_Agent\config.yaml')
    check.run()
    config = check.config

    system_health = SystemHealth(
        drone=DroneHealth(),
        pi=PiHealth(),
        radio=LinkHealth()
    )

    capture_controller = CaptureController(config)

    mission = MissionController(
        config,
        system_health,
        capture_controller
    )

    mission.preflight_check()
    mission.wait_for_start()
