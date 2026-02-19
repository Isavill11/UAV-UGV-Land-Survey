## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Flight Controller (ArduPilot)        │
│                    (Connected via Serial/UDP)           │
└────────────────────────────┬────────────────────────────┘
                             │
                    MAVLink Messages
                             │
        ┌────────────────────▼─────────────────────┐
        │      MAVLinkHandler (mavlink_handler.py) │
        │  - Receives MAVLink messages             │
        │  - Routes to message handlers            │
        │  - Manages connection lifecycle          │
        └────────────────────┬─────────────────────┘
                             │
        ┌────────────────────┴──────────────────────┐
        │                                           │
        ▼                                           ▼
┌───────────────────────┐            ┌──────────────────────┐
│  Health Tracking      │            │ Mission Controller   │
│  - DroneHealth        │            │ - State Machine      │
│  - PiHealth           │            │ - State Transitions  │
│  - LinkHealth         │            │ - Capture Control    │
│  - SystemHealth       │            └──────────────────────┘
└───────────────────────┘                       │
                                                 ▼
                                    ┌──────────────────────┐
                                    │ CaptureController    │
                                    │ - Camera management  │
                                    │ - Image capture      │
                                    └──────────────────────┘
```

## Key Components

## 1. **MAVLinkHandler** (`mavlink_handler.py`)
Manages all communication with the flight controller.

### Message Handler Mapping

| Message Type | Handler Method | Updates | Frequency |
|---|---|---|---|
| HEARTBEAT | `_handle_heartbeat()` | armed, system_status | 1 Hz |
| SYS_STATUS | `_handle_sys_status()` | battery%, cpu_load | 1 Hz |
| BATTERY_STATUS | `_handle_battery_status()` | voltage, capacity | 1 Hz |
| GPS_RAW_INT | `_handle_gps_raw()` | gps_lock, altitude | 1 Hz |
| LOCAL_POSITION_NED | `_handle_local_position()` | altitude | 2 Hz |
| ATTITUDE | `_handle_attitude()` | roll, pitch, yaw | 1 Hz |


## Message Parameter meanings:

### These features are the battery and overall system sensor health
SYS_STATUS: 

    battery_remaining    ->     > 40% = normal
    voltage_battery    ->      20-40% = reduce camera capture rate
    current_battery    ->      < 15% or when the state of the drone is critical = stop the capture rate completely and flush the buffers.
    onboard_control_sensors_health
    onboard_control_sensors_enabled
    temperature (cdeg)


### These features are the link quality
RADIO_STATUS: 
    rssi
    - Signal strength of local radio
    - Use to decide image transmit rate

    remrssi
    - Remote (GCS) signal strength
    - Confirms downlink health

    rxerrors
    - Packet corruption indicator
    - Rising trend = back off bandwidth

    fixed
    - How many errors were corrected
    - High value = link struggling but alive

### note to self :
    Good link:
    rssi > -70
    rxerrors stable

    Degraded:
    rssi -70 to -85
    rxerrors rising

    Bad:
    rssi < -85
    rxerrors rapidly increasing


### These features are the flight state
HEARTBEAT:

    base_mode    ->     armed vs disarmed vs rtl vs land, lets you know what mode the drone is in. stop capturing images when rtl or landing. 
    custom_mode    ->   auto mission, manual mission. start full image capture on auto missions
    system_status    ->     LOITER, HOVER, etc, reduce capture rate. 

---


### 2. **Health System** (`Mission_Controller/health.py`)
Tracks health of drone, Raspberry Pi, and radio link.

**DroneHealth Class:**
```python
# Updated from MAVLink messages
drone_health.update_from_heartbeat(msg)        # Gets armed state
drone_health.update_from_sys_status(msg)       # Gets battery %
drone_health.update_from_battery_status(msg)   # Gets voltage
drone_health.update_from_gps_raw(msg)          # Gets altitude
```

**Health States:**
- `BatteryState`: OK, LOW, CRITICAL, UNKNOWN
- `LinkState`: OK, STALE, DEGRADED, CRITICAL
- `ThermalState`: GOOD, WARM, HOT
- `SystemState`: OK, DEGRADED, CRITICAL




## Troubleshooting

### Connection Issues

**"Failed to connect to flight controller"**
- Check serial connection: `ls /dev/tty*` (Linux) or Device Manager (Windows)
- Verify baud rate matches flight controller (usually 115200)
- Test with `mavproxy` first: `mavproxy.py --master=/dev/ttyS0 --baudrate=115200`

**"No heartbeat received"**
- Ensure flight controller is powered on
- Check cable connections
- Verify flight controller is running ArduPilot firmware

### Message Rate Issues

**"Not receiving messages at expected rate"**
- Check CPU on Raspberry Pi isn't overloaded
- Ensure storage isn't full (fills up buffer)
- Verify network connection if using UDP

**"Getting stale data warnings"**
- Increase timeout in config: `mavlink_timeout: 3.0`
- Or reduce loop rate: `loop_rate_hz: 5`

### Camera Issues

**"Could not open camera"**
- Check camera ID in config: `camera.id: 0`
- Ensure camera is connected and detected: `ls /dev/video*`
- On Raspberry Pi, enable camera in `raspi-config`

## Advanced Configuration

### Custom State Transitions

Modify `mission_controller.py` `_evaluate_state_transitions()` to add custom logic:

```python
elif self.state == MissionState.CAPTURING:
    # Custom: Stop if no animals detected in 5 minutes
    if self.no_motion_time > 300:
        self._transition(MissionState.SHUTDOWN)
```

### Custom Message Handlers

Add new handlers in `notmain.py` `setup_mavlink_handlers()`:

```python
self.mavlink.register_handler("VIBRATION", self._handle_vibration)

def _handle_vibration(self, msg):
    """Handle high vibrations"""
    if msg.vibration_x > 50:
        logger.warning("High vibration detected!")
```

### Adaptive Capture Rates

Modify `capture_controller.py` to adjust capture rate based on conditions:

```python
def adaptive_update(self, health_state):
    """Adjust capture rate based on system state"""
    if health_state == SystemState.DEGRADED:
        self.apply_profile("DEGRADED")
    elif health_state == SystemState.CRITICAL:
        self.apply_profile("CRITICAL")
    else:
        self.apply_profile("CAPTURING")
```

## MAVLink Message IDs Reference

Common message IDs for requesting streams:

```python
HEARTBEAT = 0
SYS_STATUS = 1
BATTERY_STATUS = 147
GPS_RAW_INT = 24
LOCAL_POSITION_NED = 33
ATTITUDE = 30
```

Request at specific rates (in Hz):
```python
# Request at 1 Hz (1,000,000 microseconds)
mavlink.request_message_interval(24, 1000000)

# Request at 10 Hz (100,000 microseconds)
mavlink.request_message_interval(24, 100000)
```

## Performance Tuning

### For Better Stability
- Lower loop rate: `loop_rate_hz: 5` (instead of 10)
- Increase timeouts: `mavlink_timeout: 3.0`
- Reduce capture quality: `jpeg_quality: 70`

### For Better Data Collection
- Higher loop rate: `loop_rate_hz: 20`
- Faster captures: `interval: 0.5`
- Increase quality: `jpeg_quality: 95`

### For Limited Storage
- Lower capture interval: `interval: 5.0` (capture every 5 seconds)
- Compress aggressively: `jpeg_quality: 60`
- Enable auto cleanup in config


## Logging

All components use Python logging. View logs:

```python
import logging
logging.basicConfig(level=logging.DEBUG)  # Verbose
logging.basicConfig(level=logging.INFO)   # Normal
logging.basicConfig(level=logging.WARNING) # Errors only
```


