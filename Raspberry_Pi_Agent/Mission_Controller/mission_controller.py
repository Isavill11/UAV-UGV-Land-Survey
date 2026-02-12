from enum import Enum, auto
import time

from Raspberry_Pi_Agent.Mission_Controller.health import (
    SystemHealth,
    SystemState,
    BatteryState,
    LinkState
)



'''
case structure: 
Everything is good if: 


reduce capture rate if: 
- the battery is getting pretty low
- the raspberry pi is getting pretty hot.
- the raspberry pi is running out of storage in tx buffer. 
    (after sending the images to the ground station, delete the images in tx_buffer to maintain large storage.)
- OPTIONAL/IMPLEMENT LATER: if there seems to be NO animals or crops on screen. 

    

turn off capturing all together if: 
- we are preflight/barely taking off
- the system state is critical 
    the system state is critical if: 
    - there is NO link to the ground station
    - the drone battery is CRITICALLY low
    - the raspberry pi is SUPER hot

dont send images if:
- the link is not good
- battery too hot
'''

class MissionState(Enum):
    INIT = auto()
    PREFLIGHT = auto()
    READY = auto()
    CAPTURING = auto()
    DEGRADED = auto()
    FAILSAFE = auto()
    SHUTDOWN = auto()




class MissionController:
    def __init__(self, system_health, cfg, capture):
        self.state = MissionState.INIT
        self.health = system_health
        self.cfg = cfg
        self.capture = capture
        self.last_system_state = None
        self.current_system_state = None

    def update(self):
        
        
        if self.state == MissionState.INIT:
            if self.health.is_safe(self.cfg):
                self._transition(MissionState.PREFLIGHT)

        elif self.state == MissionState.PREFLIGHT:
            if self.health.drone.armed:
                self._transition(MissionState.READY)

        elif self.state == MissionState.READY:
            if self.health.drone.flight_mode == "AUTO":
                self._transition(MissionState.CAPTURING)

        elif self.state == MissionState.CAPTURING:
            if self.health.radio.evaluate(self.cfg["link_thresholds"]):
                self._transition(MissionState.DEGRADED)
            elif not self.health.is_safe(self.cfg):
                self._transition(MissionState.FAILSAFE)
                
            if self.health.drone.battery_state(self.cfg) == BatteryState.LOW:
                self._transition(MissionState.DEGRADED)

            if self.health.drone.is_critical(self.cfg):
                    self._transition(MissionState.FAILSAFE)

        elif self.state == MissionState.DEGRADED:
            if self.health.radio.is_bad(self.cfg["link_thresholds"]):
                self._transition(MissionState.FAILSAFE)
            elif not self.health.radio.is_degraded(self.cfg["link_thresholds"]):
                self._transition(MissionState.CAPTURING)

        elif self.state == MissionState.FAILSAFE:
            self._transition(MissionState.SHUTDOWN)


    def _transition(self, new_state):
        self._on_exit(self.state)
        self.state = new_state
        self._on_enter(new_state)


    def _on_enter(self, state):
        if state == MissionState.CAPTURING:
            self.capture.start()
            self.capture.apply_profile("CAPTURING")



        elif state == MissionState.DEGRADED:
            self.capture.start()
            self.capture.apply_profile("DEGRADED")



        elif state in (MissionState.FAILSAFE, MissionState.SHUTDOWN):
            self.capture.stop()



    def _on_exit(self, state):
        pass





