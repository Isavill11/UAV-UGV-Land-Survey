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

### 1. **MAVLinkHandler** (`mavlink_handler.py`)
Manages all communication with the flight controller.

**Key Methods:**
- `connect()` - Connect to flight controller
- `start_listening()` - Start receiving messages in background thread
- `register_handler(message_type, callback)` - Register message handlers
- `arm_disarm(arm)` - Send arm/disarm commands
- `set_mode(mode_name)` - Change flight mode
- `request_message_interval(message_id, interval_us)` - Request message streams

**Common Message Types:**
- `HEARTBEAT` - Drone is alive (sent at ~1Hz)
- `SYS_STATUS` - Battery, CPU load, errors
- `BATTERY_STATUS` - Detailed battery info
- `GPS_RAW_INT` - GPS position and altitude
- `LOCAL_POSITION_NED` - Local position relative to home
- `ATTITUDE` - Roll, pitch, yaw angles

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

### 3. **Mission Controller** (`Mission_Controller/mission_controller.py`)
State machine that manages mission execution.

**Mission States:**
```
INIT → PREFLIGHT → READY → CAPTURING ↔ DEGRADED → SHUTDOWN
                              ↓
                           FAILSAFE
```

**State Transitions Based On:**
- Drone armed/disarmed
- Battery level
- System health (temperature, storage)
- Link quality
- Flight mode

### 4. **Capture Controller** (`Mission_Controller/capture_controller.py`)
Manages camera image capture with adaptive profiles.

**Capture Profiles:**
- `CAPTURING` - Normal operation (1 image/sec)
- `DEGRADED` - Reduced rate (1 image/5 sec)
- `CRITICAL` - No capture (saves resources)

## Setup Instructions

### 1. Install Dependencies

```bash
pip install pymavlink pyyaml opencv-python
```

### 2. Configure Connection

Edit `config.yaml` in the `mavlink` section:

```yaml
mavlink:
  # For Raspberry Pi serial connection (typical setup)
  connection_string: "/dev/ttyS0"    # Serial port
  baud: 115200                       # Standard ArduPilot baud rate
  mavlink_timeout: 2.0               # Timeout in seconds
```

**Common Connection Strings:**
- **Serial on Linux:** `/dev/ttyS0`, `/dev/ttyUSB0`, `/dev/ttyAMA0`
- **Serial on Windows:** `COM3`, `COM4`
- **UDP (for sitl/simulation):** `udp:127.0.0.1:14550`
- **TCP:** `tcp:192.168.1.100:5760`

### 3. Configure Health Thresholds

Edit `config.yaml` for your specific drone:

```yaml
battery_status:
  critical_battery: 25    # Stop mission at 25%
  low_battery: 40         # Reduce rate at 40%
  
pi:
  temp_warn: 70           # Warn at 70°C
  temp_critical: 80       # Failsafe at 80°C

communication:
  link_thresholds:
    rssi_degraded: 70     # dBm threshold for degraded
    rssi_critical: 85     # dBm threshold for critical
```

## Running an Autonomous Mission

### Step 1: Prepare Hardware
1. Connect Raspberry Pi serial port to flight controller (TELEM2 port recommended)
2. Connect Pi to power
3. Upload mission to flight controller via Mission Planner
4. Ensure GPS lock before starting

### Step 2: Run the Mission

```python
# In Python script or command line:
from Raspberry_Pi_Agent.notmain import main

if __name__ == "__main__":
    main()
```

### Step 3: Mission Sequence
1. **Preflight Checks** - Verify system health, camera, storage
2. **Waiting for Start** - Drone must be:
   - Armed
   - In AUTO mode
   - Mission uploaded to flight controller
3. **Mission Running** - Autonomous capture based on drone state:
   - **Capturing**: Full resolution, 1 fps
   - **Degraded**: Lower quality, reduced rate
   - **Failsafe**: Stop capture, await recovery
4. **Mission Complete** - Drone disarmed → graceful shutdown

## Message Handlers Reference

### How Message Handlers Work

When the MAVLink thread receives a message, it:
1. Calls all registered callbacks for that message type
2. Callbacks receive the message object directly
3. Update relevant health or controller state

### Example: Custom Handler

```python
def my_custom_handler(msg):
    """Called when HEARTBEAT received"""
    print(f"Armed: {bool(msg.base_mode & 128)}")
    print(f"Status: {msg.system_status}")

# Register it
mavlink.register_handler("HEARTBEAT", my_custom_handler)
```

### Built-in Message Handlers

The `AutonomousMission` class registers these automatically:

| Message | Handler | Updates |
|---------|---------|---------|
| HEARTBEAT | `_handle_heartbeat()` | Armed state, system status |
| SYS_STATUS | `_handle_sys_status()` | Battery %, CPU load |
| BATTERY_STATUS | `_handle_battery_status()` | Voltage, capacity |
| GPS_RAW_INT | `_handle_gps_raw()` | GPS fix, altitude |
| LOCAL_POSITION_NED | `_handle_local_position()` | Position, altitude |
| ATTITUDE | `_handle_attitude()` | Roll, pitch, yaw |

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

## Next Steps

1. **Test Connection**: Run `mavlink.connect()` and verify heartbeat
2. **Test Mission**: Run preflight and wait states without flying
3. **Deploy**: Arm drone in AUTO mode and monitor logs
4. **Iterate**: Adjust health thresholds based on real flight data
