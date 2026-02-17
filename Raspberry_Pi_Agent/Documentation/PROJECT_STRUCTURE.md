
## Data Flow Architecture

```
MAVLink Message (from flight controller)
        ↓
    mavlink_handler.py (MAVLinkHandler class)
        ↓
    Handler function (in notmain.py)
        ├─ _handle_heartbeat()
        ├─ _handle_sys_status()
        ├─ _handle_battery_status()
        ├─ _handle_gps_raw()
        ├─ _handle_local_position()
        └─ _handle_attitude()
        ↓
    health.py (DroneHealth, PiHealth, LinkHealth)
        ├─ update_from_heartbeat()
        ├─ update_from_sys_status()
        ├─ update_from_battery_status()
        └─ evaluate()
        ↓
    mission_controller.py (MissionController.update())
        ├─ _evaluate_state_transitions()
        └─ _on_state_update()
        ↓
    capture_controller.py (CaptureController.update())
        ├─ apply_profile()
        ├─ start() / stop()
        └─ _capture_frame()
        ↓
    Captured Image Files
    (captured_images/full/ or captured_images/degraded/)
```

## State Machine Flow

```
System Startup
    ↓
[INIT] - Initialize config & components
    ↓
Mission.preflight_check() passes
    ↓
[PREFLIGHT] - Wait for arm signal
    ↓
Drone armed & ready
    ↓
[READY] - Wait for AUTO mode
    ↓
User switches to AUTO mode
    ↓
┌───────────────────────────────────────┐
│ [CAPTURING] - PRIMARY STATE           │
│ - Camera on (1 fps, 90% quality)      │
│ - Monitoring health continuously      │
│ - Main mission loop running           │
│                                       │
│ If battery LOW (40-25%) or            │
│ temp WARN (70-80°C) or                │
│ link POOR (70-85 dBm)                 │
│   ↓                                   │
│   └─→ [DEGRADED]                      │
│                                       │
│ If battery CRITICAL (<25%) or         │
│ temp CRITICAL (>80°C) or              │
│ link LOST (>85 dBm) or                │
│ storage full or cpu maxed             │
│   ↓                                   │
│   └─→ [FAILSAFE]                      │
│                                       │
│ If recovered from DEGRADED            │
│   ↓                                   │
│   └─→ back to [CAPTURING]             │
│                                       │
│ If drone disarmed                     │
│   ↓                                   │
│   └─→ [SHUTDOWN]                      │
└───────────────────────────────────────┘

[DEGRADED] - FALLBACK STATE
  - Camera on (0.2 fps, 50% quality)
  - Attempt mission with reduced resource usage
  - Monitor for recovery
  - Can return to CAPTURING if improved
  - Or go to FAILSAFE if worse
    ↓
[FAILSAFE] - EMERGENCY STATE
  - Camera off
  - Stop all capture
  - Log critical issues
  - Wait for recovery or manual intervention
  - Automatically transition to SHUTDOWN
    ↓
[SHUTDOWN] - FINAL STATE
  - Clean up resources
  - Save data
  - Close connections
  - Exit mission loop
```

## Message Handler Mapping

| Message Type | Handler Method | Updates | Frequency |
|---|---|---|---|
| HEARTBEAT | `_handle_heartbeat()` | armed, system_status | 1 Hz |
| SYS_STATUS | `_handle_sys_status()` | battery%, cpu_load | 1 Hz |
| BATTERY_STATUS | `_handle_battery_status()` | voltage, capacity | 1 Hz |
| GPS_RAW_INT | `_handle_gps_raw()` | gps_lock, altitude | 1 Hz |
| LOCAL_POSITION_NED | `_handle_local_position()` | altitude | 2 Hz |
| ATTITUDE | `_handle_attitude()` | roll, pitch, yaw | 1 Hz |

## Configuration Sections

### `platform`
```
name: uav
id: (unique identifier)
location: (mission location)
startup_delay_sec: 3
loop_rate_hz: 10 (updates per second)
```

### `mavlink`
```
connection_string: /dev/ttyS0 (or COM3, UDP, TCP)
baud: 115200
mavlink_timeout: 2.0 (heartbeat timeout)
```

### `battery_status`
```
critical_battery: 25 (%)
low_battery: 40 (%)
voltage_critical: 9.5 (V)
```

### `pi`
```
temp_warn: 70 (°C)
temp_critical: 80 (°C)
```

### `communication`
```
link_thresholds:
  rssi_degraded: 70 (dBm)
  rssi_critical: 85 (dBm)
```

## Usage Patterns

### Pattern 1: Autonomous Mission (Simple)
```python
from Raspberry_Pi_Agent.notmain import main
main()  # Runs complete mission autonomously
```

### Pattern 2: Custom Setup
```python
from Raspberry_Pi_Agent.notmain import AutonomousMission
mission = AutonomousMission('config.yaml')
mission.run()
```

### Pattern 3: Custom Handlers
```python
mission = AutonomousMission('config.yaml')
mission.mavlink.register_handler("CUSTOM_MSG", my_function)
mission.run()
```

### Pattern 4: Manual Control
```python
mission = AutonomousMission('config.yaml')
mission.mavlink.connect()
mission.mavlink.start_listening()

# Do custom things
while mission.running:
    mission.mission_controller.update()
    mission.capture_controller.update()

mission.shutdown()
```

## File Dependencies

```
notmain.py
├── requires: verify_config.py
├── requires: mavlink_handler.py
├── requires: Mission_Controller/mission_controller.py
│   └── requires: Mission_Controller/health.py
├── requires: Mission_Controller/capture_controller.py
└── requires: config.yaml

mavlink_handler.py
└── requires: pymavlink (external package)

Mission_Controller/mission_controller.py
├── requires: Mission_Controller/health.py
└── requires: Mission_Controller/capture_controller.py

Mission_Controller/health.py
└── (no internal dependencies)

Mission_Controller/capture_controller.py
├── requires: cv2 (external package)
└── requires: config.yaml for camera settings
```

## Deployment Checklist

- [ ] Install Python dependencies (`requirements_mavlink.txt`)
- [ ] Configure `config.yaml` with connection settings
- [ ] Test MAVLink connection (`test_connection.py`)
- [ ] Test camera functionality (`test_camera.py`)
- [ ] Run dry run on ground (`TESTING_CHECKLIST.md` Phase 4)
- [ ] Fly first test mission in safe area
- [ ] Analyze logs and captured images
- [ ] Adjust health thresholds based on real data
- [ ] Deploy for production missions

