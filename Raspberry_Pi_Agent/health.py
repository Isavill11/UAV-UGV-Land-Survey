from dataclasses import dataclass, field
import time
import os



@dataclass
class DroneHealth:
    battery_remaining: int | None = None
    battery_voltage: float | None = None
    armed: bool = False
    flight_mode: str | None = None
    system_ok: bool = True
    last_update: float = field(default_factory=time.time)

    def is_critical(self, cfg):
        return (
            self.battery_remaining is not None
            and self.battery_remaining < cfg["battery_critical"]
        )


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


    def is_bad(self, cfg) -> bool:
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

    def is_safe(self, cfg):
        if self.drone.is_critical(cfg):
            return False
        if self.pi.is_overheating(cfg):
            return False
        return True
