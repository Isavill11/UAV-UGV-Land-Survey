
from enum import Enum, auto
import time

class MissionState(Enum):
    INIT = auto()
    PREFLIGHT = auto()
    READY = auto()
    CAPTURING = auto()
    DEGRADED = auto()
    FAILSAFE = auto()
    SHUTDOWN = auto()

class MissionController:
    def __init__(self, system_health, cfg):
        self.state = MissionState.INIT
        self.health = system_health
        self.cfg = cfg


    def update(self, capture):
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
            capture.start()
            capture.configure(interval=1.0, jpeg_quality=90)
            
            if self.health.radio.is_bad(self.cfg["link_thresholds"]):
                self._transition(MissionState.DEGRADED)
            elif not self.health.is_safe(self.cfg):
                self._transition(MissionState.FAILSAFE)

        elif self.state == MissionState.DEGRADED:
            capture.start()
            capture.configure(interval=5.0, jpeg_quality=50)


            if self.health.radio.is_good(self.cfg):
                self._transition(MissionState.CAPTURING)
            elif not self.health.is_safe(self.cfg):
                self._transition(MissionState.FAILSAFE)

        elif self.state == MissionState.FAILSAFE: 
            capture.stop()



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



