from dataclasses import dataclass, field
import time
import os
from enum import Enum, auto


class BatteryState(Enum):
    OK = auto()
    LOW = auto()
    CRITICAL = auto()
    UNKNOWN = auto()


class SystemState(Enum): 
    OK = auto()
    DEGRADED = auto()
    CRITICAL = auto()


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

### removed the 'is_safe' function. when i ask for it, it should just give me its status, not decide 

@dataclass
class PiHealth:
    cpu_temp: float | None = None
    storage_ok: bool = True
    last_update: float = field(default_factory=time.time)

    def get_raspi_core_temp(self):
        temp = os.popen('cat /sys/class/thermal/thermal_zone0/temp').readline()
        return float(temp) / 1000.0

    def check_disk(self):
        st = os.statvfs("/")
        free = st.f_bavail * st.f_frsize
        return free > 100 * 1024 * 1024  # 100 MB minimum

    def update(self):
        self.cpu_temp = self.get_raspi_core_temp()
        self.storage_ok = self.check_disk()
        self.last_update = time.time()

@dataclass
class LinkHealth:
    rssi: int | None = None
    remrssi: int | None = None
    rxerrors: int | None = None
    fixed: int | None = None
    last_update: float = field(default_factory=time.time)

    def is_stale(self, timeout=2.0):
        return (time.time() - self.last_update) > timeout

    def is_degraded(self, cfg) -> bool:
        if self.is_stale():
            return True
        if self.rssi is None:
            return True
        return self.rssi < cfg["rssi_degraded"]

    def is_bad(self, cfg) -> bool:  #### if the link health is bad, this is a CRITICAL State.
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


### TODO: what should I classify as critical and degraded? when the drone health is bad, critical, when the radio is bad then alright? 

    def system_state(self, cfg) -> SystemState: 
        if self.drone.battery_state(cfg) == BatteryState.CRITICAL: 
            return SystemState.CRITICAL
        if self.drone.battery_state == BatteryState.LOW:
            return SystemState.DEGRADED
        if self.radio.is_bad(cfg) == True: 
            return SystemState.CRITICAL
        if self.radio.is_degraded == True: 
            return SystemState.DEGRADED
        if not self.pi.storage_ok: 
            return SystemState.DEGRADED
        
        
        #### in the main loop, check if the system_state.radio.is_stale or .is_degraded or .is_bad

        return SystemState.OK
    
