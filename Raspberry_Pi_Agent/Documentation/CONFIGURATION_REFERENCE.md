# Configuration Reference

All parameters are defined in config.yaml.

---

## MAVLink
mavlink:
    connection_string: "/dev/ttyS0"
    baud: 115200
    mavlink_timeout: 2.0


---

## Platform
platform:
    loop_rate_hz: 10
    startup_delay_sec: 3


---

## Battery Thresholds



battery_status:
    critical_battery: 25
    low_battery: 40
    voltage_critical: 9.5


---

## Raspberry Pi Thermal
pi:
    temp_warn: 70
    temp_critical: 80


---

## Communication Thresholds
communication:
    rssi_thresholds:
    excellent: -50
    good: -70
    degraded: -85
    critical: -100

---

## Capture Profiles
capture_profiles:
    CAPTURING:
    interval: 1.0
    jpeg_quality: 90
    DEGRADED:
    interval: 5.0
    jpeg_quality: 50


---

## Image Storage
image_storage:
    max_storage_mb: 2000
    min_storage_mb_critical: 100


---

## Transmission
batching:
    batch_size: 10
    time_threshold_sec: 30

---

## Recommended Configurations

### Conservative (Safe Flight)

- critical_battery: 30
- temp_critical: 75
- lower capture rate

### Long Mission

- lower JPEG quality
- larger storage limit

### Poor Link Environment

- use TCP
- smaller batch_size
- longer transmission interval
