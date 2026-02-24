from dataclasses import dataclass, field
import time
import os
from enum import Enum, auto


class Severity(Enum):
    INFO = auto()
    DEGRADED = auto()
    CRITICAL = auto()

class BatteryState(Enum):
    OK = auto()
    LOW = auto()
    CRITICAL = auto()
    UNKNOWN = auto()

class SystemState(Enum): 
    OK = auto()
    DEGRADED = auto()
    CRITICAL = auto()

class LinkState(Enum): 
    OK = auto()
    STALE = auto()
    DEGRADED = auto()
    CRITICAL = auto()

class ThermalState(Enum): 
    GOOD = auto()
    WARM = auto()
    HOT = auto()

@dataclass
class HealthIssue:
    source: str          # "PI", "DRONE", "LINK"
    message: str         ## whats wrong
    severity: Severity
    timestamp: float



@dataclass
class DroneHealth:
    
    battery_remaining: int | None = None
    battery_voltage: float | None = None
    armed: bool = False
    flight_mode: str | None = None
    last_update: float = field(default_factory=time.time)
    gps_lock: bool = False
    altitude: float | None = None
    
    # Additional drone state from MAVLink
    system_status: int | None = None
    cpu_load: int | None = None
    motor_count: int | None = None

    def battery_state(self, cfg) -> BatteryState:
        if self.battery_remaining is None:
            return BatteryState.UNKNOWN

        critical = cfg["battery_status"]["critical_battery"]
        low = cfg["battery_status"]["low_battery"]

        if self.battery_remaining <= critical:
            return BatteryState.CRITICAL
        elif self.battery_remaining <= low:
            return BatteryState.LOW
        else:
            return BatteryState.OK
    
    def update_from_heartbeat(self, msg):
        """Update drone health from HEARTBEAT message"""
        self.armed = bool(msg.base_mode & 128)  # Check armed bit
        self.system_status = msg.system_status
        self.last_update = time.time()
    
    def update_from_sys_status(self, msg):
        """Update drone health from SYS_STATUS message"""
        self.battery_remaining = msg.battery_remaining  # 0-100
        self.cpu_load = msg.load  # CPU load in %
        self.last_update = time.time()
    
    def update_from_battery_status(self, msg):
        """Update drone health from BATTERY_STATUS message"""
        if msg.voltages and len(msg.voltages) > 0:
            self.battery_voltage = msg.voltages[0] / 1000.0  # Convert to volts
        self.battery_remaining = msg.battery_remaining if msg.battery_remaining >= 0 else None
        self.last_update = time.time()
    
    def update_from_gps_raw(self, msg):
        """Update drone health from GPS_RAW_INT message"""
        self.gps_lock = msg.fix_type >= 3  # 3+ is RTK fix or better
        self.altitude = msg.alt / 1000.0  # Convert to meters
        self.last_update = time.time()
    
    def update_from_local_position(self, msg):
        """Update drone health from LOCAL_POSITION_NED message"""
        # Negative z is altitude above origin
        self.altitude = max(-msg.z, 0) if msg.z else 0
        self.last_update = time.time()
    
    def is_healthy(self, cfg) -> bool:
        """Check if drone is in a healthy state"""
        if self._is_stale(cfg.get("mavlink_timeout", 2.0)):
            return False
        
        battery_state = self.battery_state(cfg)
        if battery_state == BatteryState.CRITICAL:
            return False
        
        # Drone must be armed and in a valid mode for mission
        if not self.armed:
            return False
        
        return True
    
    def _is_stale(self, timeout: float = 2.0) -> bool:
        """Check if health data is stale (no recent updates)"""
        return (time.time() - self.last_update) > timeout
    
    
    def evaluate(self, cfg) -> list[HealthIssue]:
        issues = []
        now = time.time()
        state = self.battery_state(cfg)

        if state == BatteryState.CRITICAL:
            issues.append(
                HealthIssue(
                    source="DRONE",
                    message=f"Battery critical: {self.battery_remaining}%",
                    severity=Severity.CRITICAL,
                    timestamp=now
                ))
        elif state == BatteryState.LOW:
            issues.append(
                HealthIssue(
                    source="DRONE",
                    message=f"Battery low: {self.battery_remaining}%",
                    severity=Severity.DEGRADED,
                    timestamp=now
                ))
        return issues

        


@dataclass
class PiHealth:
    cpu_temp: float | None = None
    storage_remaining_mb: float | None = None
    last_update: float = field(default_factory=time.time)

    def update(self): 
        self.cpu_temp = self.get_raspi_core_temp() 
        self.storage_amt = self.check_disk() 
        self.last_update = time.time()


    def evaluate(self, cfg) -> list[HealthIssue]:
        issues = []
        now = time.time()
        self.update()

        if self.cpu_temp is not None:
            if self.cpu_temp >= cfg["pi"]["temp_critical"]:
                issues.append(
                    HealthIssue(
                        source="PI",
                        message=f"CPU temperature critical: {self.cpu_temp:.1f}C",
                        severity=Severity.CRITICAL,
                        timestamp=now
                    )
                )
            elif self.cpu_temp >= cfg["pi"]["temp_warn"]:
                issues.append(
                    HealthIssue(
                        source="PI",
                        message=f"CPU temperature high: {self.cpu_temp:.1f}C",
                        severity=Severity.DEGRADED,
                        timestamp=now
                    )
                )

        if not self.storage_amt:
            issues.append(
                HealthIssue(
                    source="PI",
                    message="Low disk space",
                    severity=Severity.DEGRADED,
                    timestamp=now
                )
            )

        return issues
    
    def _is_stale(self, timeout=5.0):
        return (time.time() - self.last_update) > timeout
    
    def get_raspi_core_temp(self): 
        temp = os.popen('cat /sys/class/thermal/thermal_zone0/temp').readline() 
        return float(temp) / 1000.0 
    
    def check_disk(self): 
        st = os.statvfs("/") 
        free = st.f_bavail * st.f_frsize 
        return free > 100 * 1024 * 1024 



@dataclass
class LinkHealth:
    rssi: int | None = None
    remrssi: int | None = None
    rxerrors: int | None = None
    fixed: int | None = None
    last_update: float = field(default_factory=time.time)

    packet_loss_percent: float | None = None
    connected: bool = False

    def link_state(self, cfg) -> LinkState:
        if self._is_stale(): 
            return LinkState.STALE
        if self._is_degraded(cfg): 
            return LinkState.DEGRADED
        if self._is_bad(cfg): 
            return LinkState.CRITICAL
        return LinkState.OK
    
    
    def evaluate(self, cfg) -> list[HealthIssue]:
        issues = []
        now = time.time()

        if self._is_stale():
            issues.append(
                HealthIssue(
                    source="LINK",
                    message="Radio link stale (no updates)",
                    severity=Severity.CRITICAL,
                    timestamp=now
                ))
            return issues

        if self._is_bad(cfg):
            issues.append(
                HealthIssue(
                    source="LINK",
                    message=f"Radio RSSI critical: {self.rssi}",
                    severity=Severity.CRITICAL,
                    timestamp=now
                ))
        elif self._is_degraded(cfg):
            issues.append(
                HealthIssue(
                    source="LINK",
                    message=f"Radio RSSI degraded: {self.rssi}",
                    severity=Severity.DEGRADED,
                    timestamp=now
                ))

        return issues
        
    def _is_stale(self, timeout=2.0):
            return (time.time() - self.last_update) > timeout

    def _is_degraded(self, cfg) -> bool:
        if self._is_stale():
            return True
        if self.rssi is None:
            return True
        return self.rssi < cfg["rssi_degraded"]

    def _is_bad(self, cfg) -> bool:  #### if the link health is bad, this is a CRITICAL State.
        if self._is_stale():
            return True
        if self.rssi is None:
            return True
        return self.rssi < cfg["rssi_critical"]
            



@dataclass
class SystemHealth:
    drone: DroneHealth
    pi: PiHealth
    radio: LinkHealth

    def evaluate(self, cfg) -> tuple[SystemState, list[HealthIssue]]:
        issues = []
        issues.extend(self.drone.evaluate(cfg))
        issues.extend(self.pi.evaluate(cfg))
        issues.extend(self.radio.evaluate(cfg))

        # determine system state
        if any(i.severity == Severity.CRITICAL for i in issues):
            return SystemState.CRITICAL, issues

        if any(i.severity == Severity.DEGRADED for i in issues):
            return SystemState.DEGRADED, issues

        return SystemState.OK, issues
