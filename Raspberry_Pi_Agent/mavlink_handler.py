"""
MAVLink Message Handler for Flight Controller Communication
Receives and processes MAVLink messages from ArduPilot flight controller
Updates health and mission controller with latest drone state
"""

import logging
import threading
import time
from typing import Optional, Callable, List
from collections import deque

try:
    from pymavlink.dialects.v10 import ardupilotmega as mavutil
    PYMAVLINK_AVAILABLE = True
except ImportError:
    PYMAVLINK_AVAILABLE = False
    logging.warning("pymavlink not installed. Install with: pip install pymavlink")


logger = logging.getLogger(__name__)


class MAVLinkHandler:
    """Manages MAVLink connection and message handling"""
    
    def __init__(self, connection_string: str, baud: int = 115200):
        """
        Initialize MAVLink handler
        
        Args:
            connection_string: Connection string (e.g., '/dev/ttyS0', 'COM3', 'udp:127.0.0.1:14550')
            baud: Baud rate for serial connections (default 115200)
        """
        self.connection_string = connection_string
        self.baud = baud
        self.master = None
        self.connected = False
        self.running = False
        
        # Message handlers registry
        self._message_handlers: dict[str, List[Callable]] = {}
        
        # Store recent messages for fallback
        self.message_buffer = deque(maxlen=1000)
        self.last_heartbeat = None
        
        # Thread management
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
    def connect(self) -> bool:
        """
        Connect to flight controller
        
        Returns:
            True if connection successful
        """
        if not PYMAVLINK_AVAILABLE:
            logger.error("pymavlink not available")
            return False
            
        try:
            self.master = mavutil.mavlink_connection(
                self.connection_string,
                baud=self.baud
            )
            
            # Wait for first heartbeat
            logger.info(f"Connecting to {self.connection_string}...")
            msg = self.master.wait_heartbeat(timeout=5)
            
            if msg:
                logger.info(f"Connected! System: {msg.get_srcSystem()}, Component: {msg.get_srcComponent()}")
                self.connected = True
                return True
            else:
                logger.error("No heartbeat received")
                return False
                
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from flight controller"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self.master:
            self.master.close()
            self.connected = False
            logger.info("Disconnected from flight controller")
    
    def start_listening(self):
        """Start message listening thread"""
        if self.running:
            logger.warning("Listener already running")
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._message_loop, daemon=True)
        self._thread.start()
        logger.info("MAVLink listener started")
    
    def stop_listening(self):
        """Stop message listening thread"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("MAVLink listener stopped")
    
    def register_handler(self, message_type: str, callback: Callable):
        """
        Register a callback for a specific message type
        
        Args:
            message_type: MAVLink message type (e.g., 'HEARTBEAT', 'SYS_STATUS', 'BATTERY_STATUS')
            callback: Function to call when message is received. Will receive the message object.
        """
        if message_type not in self._message_handlers:
            self._message_handlers[message_type] = []
        self._message_handlers[message_type].append(callback)
    
    def _message_loop(self):
        """Main message receiving loop (runs in separate thread)"""
        while self.running and self.connected:
            try:
                msg = self.master.recv_match(blocking=False, timeout=0.5)
                
                if msg:
                    msg_type = msg.get_type()
                    
                    # Store in buffer
                    with self._lock:
                        self.message_buffer.append((time.time(), msg_type, msg))
                    
                    # Track heartbeat
                    if msg_type == "HEARTBEAT":
                        self.last_heartbeat = time.time()
                    
                    # Call registered handlers
                    if msg_type in self._message_handlers:
                        for callback in self._message_handlers[msg_type]:
                            try:
                                callback(msg)
                            except Exception as e:
                                logger.error(f"Handler error for {msg_type}: {e}")
                
            except Exception as e:
                logger.error(f"Message receive error: {e}")
                time.sleep(0.1)
    
    def is_heartbeat_alive(self, timeout: float = 2.0) -> bool:
        """
        Check if heartbeat is still being received
        
        Args:
            timeout: Time without heartbeat to consider connection dead
            
        Returns:
            True if heartbeat received within timeout
        """
        if self.last_heartbeat is None:
            return False
        return (time.time() - self.last_heartbeat) < timeout
    
    def send_command(self, msg):
        """
        Send a MAVLink command
        
        Args:
            msg: MAVLink message to send
        """
        if not self.connected or not self.master:
            logger.warning("Not connected, cannot send command")
            return False
        
        try:
            self.master.mav.send(msg)
            return True
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            return False
    
    def arm_disarm(self, arm: bool) -> bool:
        """
        Arm or disarm the vehicle
        
        Args:
            arm: True to arm, False to disarm
            
        Returns:
            True if command sent successfully
        """
        if not self.connected:
            return False
        
        try:
            self.master.mav.command_long_send(
                self.master.target_system,
                self.master.target_component,
                400,  # MAV_CMD_COMPONENT_ARM_DISARM
                0,    # confirmation
                1 if arm else 0,  # param1
                0, 0, 0, 0, 0, 0  # other params
            )
            return True
        except Exception as e:
            logger.error(f"Arm/disarm failed: {e}")
            return False
    
    def set_mode(self, mode_name: str) -> bool:
        """
        Set flight mode
        
        Args:
            mode_name: Flight mode name (e.g., 'GUIDED', 'AUTO', 'LOITER')
            
        Returns:
            True if command sent successfully
        """
        if not self.connected or not self.master:
            return False
        
        try:
            # Mode mapping for common flight controllers
            mode_map = {
                'STABILIZE': 0,
                'ACRO': 1,
                'ALT_HOLD': 2,
                'AUTO': 3,
                'GUIDED': 4,
                'LOITER': 5,
                'RTL': 6,
                'CIRCLE': 7,
            }
            
            if mode_name not in mode_map:
                logger.error(f"Unknown mode: {mode_name}")
                return False
            
            mode_id = mode_map[mode_name]
            
            self.master.mav.set_mode_send(
                self.master.target_system,
                1,  # base_mode
                mode_id
            )
            return True
        except Exception as e:
            logger.error(f"Set mode failed: {e}")
            return False
    
    def request_message_interval(self, message_id: int, interval_us: int) -> bool:
        """
        Request a message at a specific interval
        
        Args:
            message_id: MAVLink message ID
            interval_us: Interval in microseconds (e.g., 100000 for 10Hz)
            
        Returns:
            True if command sent successfully
        """
        if not self.connected or not self.master:
            return False
        
        try:
            self.master.mav.command_long_send(
                self.master.target_system,
                self.master.target_component,
                511,  # MAV_CMD_REQUEST_MESSAGE
                0,
                message_id,
                interval_us,
                0, 0, 0, 0, 0
            )
            return True
        except Exception as e:
            logger.error(f"Request message interval failed: {e}")
            return False
    
    def get_last_message(self, message_type: str) -> Optional:
        """
        Get the most recent message of a specific type from buffer
        
        Args:
            message_type: Message type name
            
        Returns:
            Message object or None if not found
        """
        with self._lock:
            for timestamp, msg_type, msg in reversed(list(self.message_buffer)):
                if msg_type == message_type:
                    return msg
        return None
