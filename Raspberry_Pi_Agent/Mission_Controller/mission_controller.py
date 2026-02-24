from enum import Enum, auto
import time
import logging

from .health import (
    SystemHealth,
    SystemState,
    BatteryState,
    LinkState,
    Severity
)

logger = logging.getLogger(__name__)



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
    def __init__(self, config, system_health, capture_controller):
        self.config = config

        self.state = MissionState.INIT
        self.health = system_health
        self.capture_controller = capture_controller

        self.ready = False
        self.running = False
        self.start_requested = False

        self.platform_name = config["platform"]["name"]
        self.platform_id = config["platform"]["id"]

        self.last_system_state = None
        self.current_system_state = None

        self.state_start_time = time.time()
        self.mission_start_time = None
        self.loop_interval = 1.0 / config["platform"]["loop_rate_hz"]
        
        logger.info(f"MissionController initialized for {self.platform_name}")

    def preflight_check(self) -> bool:
        """
        Run preflight checks
        
        Returns:
            True if all checks pass
        """
        logger.info("Running preflight checks...")
        
        # Check system health
        system_state, issues = self.health.evaluate(self.config)
        
        if system_state == SystemState.CRITICAL:
            logger.error("System health check FAILED - Critical issues:")
            for issue in issues:
                logger.error(f"  [{issue.source}] {issue.message}")
            return False
        
        if system_state == SystemState.DEGRADED:
            logger.warning("System health DEGRADED - Issues found:")
            for issue in issues:
                if issue.severity == Severity.DEGRADED:
                    logger.warning(f"  [{issue.source}] {issue.message}")
        
        logger.info("Preflight checks PASSED")
        self._transition(MissionState.PREFLIGHT)
        return True

    def wait_for_start(self):
        """Wait for start signal (drone armed and in AUTO mode)"""
        logger.info("Waiting for mission start signal...")
        
        while not self.start_requested and self.health.drone.is_healthy(self.config):
            if self.health.drone.armed:
                logger.info("Drone armed and ready!")
                self.start_requested = True
                break
            time.sleep(self.loop_interval)
        
        if self.start_requested:
            logger.info("Mission start signal received!")
            self._transition(MissionState.READY)

    def update(self):
        """Main mission update loop - call this regularly (at loop_rate_hz)"""
        # Evaluate current system health
        self.current_system_state, issues = self.health.evaluate(self.config)
        
        # Log critical issues
        critical_issues = [i for i in issues if i.severity == Severity.CRITICAL]
        if critical_issues:
            logger.error(f"CRITICAL issues detected:")
            for issue in critical_issues:
                logger.error(f"  [{issue.source}] {issue.message}")
        
        # Perform state machine transitions
        self._evaluate_state_transitions()
        
        # Update controllers based on current state
        self._on_state_update()
    
    def _evaluate_state_transitions(self):
        """Evaluate and perform state transitions based on health and drone state"""
        
        if self.state == MissionState.INIT:
            if self.ready:
                self._transition(MissionState.PREFLIGHT)
        
        elif self.state == MissionState.PREFLIGHT:
            if self.health.drone.armed and self.start_requested:
                self._transition(MissionState.READY)
        
        elif self.state == MissionState.READY:
            if self.health.drone.armed and self.running:
                self._transition(MissionState.CAPTURING)
        
        elif self.state == MissionState.CAPTURING:
            # Check for failure conditions (highest priority)
            if self.current_system_state == SystemState.CRITICAL:
                logger.critical("FAILSAFE TRIGGERED - Critical system state")
                self._transition(MissionState.FAILSAFE)
            
            # Check for degraded conditions
            elif self.current_system_state == SystemState.DEGRADED:
                logger.warning("Mission degraded - reducing capture rate")
                self._transition(MissionState.DEGRADED)
            
            # Check if mission is complete or aborted
            elif not self.health.drone.armed:
                logger.info("Drone disarmed - mission complete")
                self._transition(MissionState.SHUTDOWN)
        
        elif self.state == MissionState.DEGRADED:
            # Try to recover to normal operation
            if self.current_system_state == SystemState.OK:
                logger.info("System recovered - resuming normal capture")
                self._transition(MissionState.CAPTURING)
            
            # Fall back to failsafe if gets worse
            elif self.current_system_state == SystemState.CRITICAL:
                logger.critical("Degraded mode failed - FAILSAFE")
                self._transition(MissionState.FAILSAFE)
            
            # Check if mission aborted
            elif not self.health.drone.armed:
                self._transition(MissionState.SHUTDOWN)
        
        elif self.state == MissionState.FAILSAFE:
            # Attempt graceful recovery or shutdown
            logger.info("In failsafe - stopping capture and awaiting manual intervention")
            self._transition(MissionState.SHUTDOWN)
        
        elif self.state == MissionState.SHUTDOWN:
            self.running = False
            logger.info("Mission shutdown complete")
    
    def _on_state_update(self):
        """Update controllers based on current mission state"""
        
        if self.state == MissionState.CAPTURING:
            self.capture_controller.apply_profile("CAPTURING")
            self.capture_controller.start()
        
        elif self.state == MissionState.DEGRADED:
            self.capture_controller.apply_profile("DEGRADED")
            if self.capture_controller.state.name == "OFF":
                self.capture_controller.start()
        
        elif self.state in (MissionState.FAILSAFE, MissionState.SHUTDOWN):
            self.capture_controller.stop()
        
        elif self.state == MissionState.INIT:
            self.capture_controller.stop()
    
    def _transition(self, new_state: MissionState):
        """Perform state transition with entry/exit handlers"""
        if new_state == self.state:
            return
        
        logger.info(f"State transition: {self.state.name} → {new_state.name}")
        
        self._on_exit(self.state)
        self.state = new_state
        self.state_start_time = time.time()
        self._on_enter(new_state)
    
    def _on_enter(self, state: MissionState):
        """Handle state entry"""
        if state == MissionState.READY:
            logger.info("Waiting for AUTO mode and mission start...")
        
        elif state == MissionState.CAPTURING:
            self.running = True
            self.mission_start_time = time.time()
            logger.info(f"Mission started at {time.ctime()}")
        
        elif state == MissionState.DEGRADED:
            logger.warning("Operating in degraded mode")
        
        elif state == MissionState.FAILSAFE:
            logger.critical("ENTERING FAILSAFE MODE")
        
        elif state == MissionState.SHUTDOWN:
            logger.info("Shutting down mission")
    
    def _on_exit(self, state: MissionState):
        """Handle state exit"""
        pass
    
    def request_start(self):
        """Signal that mission should start"""
        self.start_requested = True
        self.ready = True
    
    def request_stop(self):
        """Signal that mission should stop"""
        self.running = False
        logger.info("Mission stop requested")
        
