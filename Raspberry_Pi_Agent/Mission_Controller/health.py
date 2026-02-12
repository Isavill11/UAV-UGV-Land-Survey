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
    storage_amt: bool = True
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
    
    def _get_raspi_core_temp(self): 
        temp = os.popen('cat /sys/class/thermal/thermal_zone0/temp').readline() 
        return float(temp) / 1000.0 
    
    def _check_disk(self): 
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

        if self.is_stale():
            issues.append(
                HealthIssue(
                    source="LINK",
                    message="Radio link stale (no updates)",
                    severity=Severity.CRITICAL,
                    timestamp=now
                ))
            return issues

        if self.is_bad(cfg):
            issues.append(
                HealthIssue(
                    source="LINK",
                    message=f"Radio RSSI critical: {self.rssi}",
                    severity=Severity.CRITICAL,
                    timestamp=now
                ))
        elif self.is_degraded(cfg):
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
        if self.is_stale():
            return True
        if self.rssi is None:
            return True
        return self.rssi < cfg["rssi_degraded"]

    def _is_bad(self, cfg) -> bool:  #### if the link health is bad, this is a CRITICAL State.
        if self.is_stale():
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
