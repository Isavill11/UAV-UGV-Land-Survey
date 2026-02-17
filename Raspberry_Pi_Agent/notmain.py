## MAIN LOOP DECISION MAKING FOR RASPI AGENT 
"""
Autonomous mission controller for Raspberry Pi agent connected to ArduPilot flight controller.
Manages MAVLink communication, health monitoring, and camera capture based on mission state.
"""

import logging
import time
import signal
import sys
from enum import Enum, auto

from Raspberry_Pi_Agent.verify_config import SelfCheckPrelaunch
from Raspberry_Pi_Agent.mavlink_handler import MAVLinkHandler
from Raspberry_Pi_Agent.Mission_Controller.mission_controller import MissionController
from Raspberry_Pi_Agent.Mission_Controller.capture_controller import CaptureController
from Raspberry_Pi_Agent.Mission_Controller.health import (
    DroneHealth, 
    LinkHealth, 
    PiHealth, 
    SystemHealth
)
from Raspberry_Pi_Agent.image_manager import ImageManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutonomousMission:
    """Main autonomous mission controller"""
    
    def __init__(self, config_path: str):
        """
        Initialize mission controller
        
        Args:
            config_path: Path to config.yaml file
        """
        # Load and verify config
        check = SelfCheckPrelaunch(config_path)
        check.run()
        self.config = check.config
        
        # Initialize health tracking
        self.system_health = SystemHealth(
            drone=DroneHealth(),
            pi=PiHealth(),
            radio=LinkHealth()
        )
        
        # Initialize image manager for storage and transmission
        self.image_manager = ImageManager(self.config)
        
        # Initialize controllers
        self.capture_controller = CaptureController(self.config, self.image_manager)
        self.mission_controller = MissionController(
            self.config,
            self.system_health,
            self.capture_controller
        )
        
        # Initialize MAVLink handler
        mavlink_cfg = self.config.get("mavlink", {})
        connection_string = mavlink_cfg.get("connection_string", "/dev/ttyS0")
        baud = mavlink_cfg.get("baud", 115200)
        
        self.mavlink = MAVLinkHandler(connection_string, baud)
        
        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = False
        logger.info(f"AutonomousMission initialized - {self.config['platform']['name']}")
    
    def _signal_handler(self, sig, frame):
        """Handle shutdown signals gracefully"""
        logger.info("Shutdown signal received")
        self.shutdown()
        sys.exit(0)
    
    def setup_mavlink_handlers(self):
        """Register MAVLink message handlers"""
        logger.info("Setting up MAVLink message handlers...")
        
        # HEARTBEAT - indicates drone is alive
        self.mavlink.register_handler("HEARTBEAT", self._handle_heartbeat)
        
        # SYS_STATUS - battery, load, drop rate
        self.mavlink.register_handler("SYS_STATUS", self._handle_sys_status)
        
        # BATTERY_STATUS - detailed battery info
        self.mavlink.register_handler("BATTERY_STATUS", self._handle_battery_status)
        
        # GPS_RAW_INT - GPS and altitude data
        self.mavlink.register_handler("GPS_RAW_INT", self._handle_gps_raw)
        
        # LOCAL_POSITION_NED - local position and altitude
        self.mavlink.register_handler("LOCAL_POSITION_NED", self._handle_local_position)
        
        # ATTITUDE - drone orientation
        self.mavlink.register_handler("ATTITUDE", self._handle_attitude)
    
    def _handle_heartbeat(self, msg):
        """Handle HEARTBEAT message"""
        self.system_health.drone.update_from_heartbeat(msg)
        logger.debug(f"Heartbeat - Armed: {self.system_health.drone.armed}, Status: {self.system_health.drone.system_status}")
    
    def _handle_sys_status(self, msg):
        """Handle SYS_STATUS message"""
        self.system_health.drone.update_from_sys_status(msg)
        logger.debug(f"SYS_STATUS - Battery: {self.system_health.drone.battery_remaining}%, CPU: {self.system_health.drone.cpu_load}%")
    
    def _handle_battery_status(self, msg):
        """Handle BATTERY_STATUS message"""
        self.system_health.drone.update_from_battery_status(msg)
        logger.debug(f"Battery - {self.system_health.drone.battery_voltage:.2f}V, {self.system_health.drone.battery_remaining}%")
    
    def _handle_gps_raw(self, msg):
        """Handle GPS_RAW_INT message"""
        self.system_health.drone.update_from_gps_raw(msg)
        logger.debug(f"GPS - Fix: {msg.fix_type}, Alt: {self.system_health.drone.altitude:.1f}m")
    
    def _handle_local_position(self, msg):
        """Handle LOCAL_POSITION_NED message"""
        self.system_health.drone.update_from_local_position(msg)
    
    def _handle_attitude(self, msg):
        """Handle ATTITUDE message"""
        logger.debug(f"Attitude - Roll: {msg.roll:.1f}, Pitch: {msg.pitch:.1f}, Yaw: {msg.yaw:.1f}")
    
    def run(self):
        """Run autonomous mission"""
        logger.info("="*60)
        logger.info("Starting Autonomous Mission")
        logger.info("="*60)
        
        # Connect to flight controller
        logger.info("Connecting to flight controller...")
        if not self.mavlink.connect():
            logger.error("Failed to connect to flight controller!")
            return False
        
        # Setup message handlers
        self.setup_mavlink_handlers()
        
        # Start listening for MAVLink messages
        self.mavlink.start_listening()
        time.sleep(0.5)  # Let listener thread start
        
        # Start image transmission thread
        self.image_manager.start_transmission()
        logger.info("Image transmission thread started")
        
        # Request important messages at regular intervals
        logger.info("Requesting flight controller messages...")
        self.mavlink.request_message_interval(0, 1000000)   # HEARTBEAT at 1Hz
        self.mavlink.request_message_interval(1, 1000000)   # SYS_STATUS at 1Hz
        self.mavlink.request_message_interval(24, 1000000)  # GPS_RAW_INT at 1Hz
        self.mavlink.request_message_interval(33, 500000)   # LOCAL_POSITION_NED at 2Hz
        
        try:
            # Preflight checks
            logger.info("Running preflight checks...")
            if not self.mission_controller.preflight_check():
                logger.error("Preflight checks failed!")
                return False
            
            # Wait for startup delay
            startup_delay = self.config["platform"].get("startup_delay_sec", 3)
            logger.info(f"Waiting {startup_delay}s for drone initialization...")
            time.sleep(startup_delay)
            
            # Request mission start (drone must be armed in AUTO mode)
            logger.info("Waiting for mission start conditions...")
            logger.info("  - Arm the drone")
            logger.info("  - Switch to AUTO mode")
            logger.info("  - Upload mission via Mission Planner")
            
            self.mission_controller.request_start()
            self.mission_controller.wait_for_start()
            
            # Main mission loop
            self.running = True
            loop_rate_hz = self.config["platform"]["loop_rate_hz"]
            loop_interval = 1.0 / loop_rate_hz
            
            logger.info(f"Mission loop running at {loop_rate_hz}Hz")
            logger.info("="*60)
            
            while self.running:
                loop_start = time.time()
                
                try:
                    # Update capture controller (handles timing automatically)
                    self.capture_controller.update()
                    
                    # Update mission controller state machine
                    self.mission_controller.update()
                    
                    # Update capture controller with current altitude for image metadata
                    self.capture_controller.set_altitude(self.system_health.drone.altitude)
                    
                    # Check if heartbeat is still alive
                    if not self.mavlink.is_heartbeat_alive(timeout=2.0):
                        logger.warning("No heartbeat received - connection may be lost!")
                        self.system_health.radio.connected = False
                    else:
                        self.system_health.radio.connected = True
                    
                    # Transmit pending images based on link quality
                    # RSSI threshold: lower dBm = better signal (more negative = better)
                    # -50 dBm = excellent, -70 dBm = good, -85 dBm = weak, -100+ = critical
                    rssi = getattr(self.system_health.radio, 'rssi', -100)  # Default to poor signal
                    if rssi < -50:  # Excellent signal
                        self.image_manager.transmit_batch(rssi)
                    elif rssi < -70:  # Good signal - transmit half batch
                        self.image_manager.transmit_batch(rssi)
                    elif rssi < -85:  # Weak signal - transmit single image
                        self.image_manager.transmit_batch(rssi)
                    # else: rssi < -100 (critical) - don't transmit, wait for better link
                    
                    # Control loop timing
                    elapsed = time.time() - loop_start
                    sleep_time = loop_interval - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    else:
                        logger.debug(f"Loop running slow: {elapsed:.3f}s (target: {loop_interval:.3f}s)")
                
                except Exception as e:
                    logger.error(f"Error in main loop: {e}", exc_info=True)
                    time.sleep(0.1)
            
            logger.info("Mission complete")
            return True
        
        except KeyboardInterrupt:
            logger.info("Mission interrupted by user")
            return False
        
        except Exception as e:
            logger.error(f"Mission error: {e}", exc_info=True)
            return False
        
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown of mission"""
        logger.info("Shutting down mission...")
        
        self.running = False
        self.mission_controller.request_stop()
        self.capture_controller.stop()
        self.image_manager.stop_transmission()
        self.mavlink.stop_listening()
        self.mavlink.disconnect()
        
        # Log final transmission statistics
        final_status = self.image_manager.get_status()
        logger.info(f"Images transmitted: {final_status.get('transmission_stats', {}).get('images_sent', 0)}")
        logger.info(f"Images pending: {final_status.get('storage_status', {}).get('pending_count', 0)}")
        
        logger.info("Mission shutdown complete")


def main():
    """Entry point for autonomous mission"""
    config_path = r'C:\Users\isav3\VSCode Projects\UAV-UGV-Land-Survey\Raspberry_Pi_Agent\config.yaml'
    
    mission = AutonomousMission(config_path)
    success = mission.run()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
