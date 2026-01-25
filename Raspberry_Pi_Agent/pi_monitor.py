###### OS HEALTH


from health import PiHealth
import time
import os


def get_raspi_core_temp(): 
    temp = os.popen('cat /sys/class/thermal/thermal_zone0/temp').readline()
    return float(temp) / 1000.0


def check_disk():
    st = os.statvfs_result

def update_pi_health(pi_health: PiHealth):
    pi_health.cpu_temp = get_raspi_core_temp()
    pi_health.storage_ok = check_disk()
    pi_health.last_update = time.time()
