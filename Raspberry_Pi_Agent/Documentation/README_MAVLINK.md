
## How It Works - Quick Overview

```
┌─────────────────────────────────────────────┐
│ Flight Controller (ArduPilot)              │
│ Sends MAVLink messages continuously       │
└─────────────┬───────────────────────────────┘
              │ Serial/UDP/TCP
              ▼
┌─────────────────────────────────────────────┐
│ MAVLinkHandler                             │
│ - Connects to flight controller            │
│ - Receives and parses messages            │
│ - Calls registered handler functions      │
└─────────────┬───────────────────────────────┘
              │
    ┌─────────┴──────────┐
    ▼                    ▼
DroneHealth         MissionController
Updates with:       Uses health to:
- battery %         - Decide state
- armed state       - Control camera
- altitude          - Handle failsafe
- temperature       - Manage mission
    │                    │
    └────────┬───────────┘
             ▼
    CaptureController
    - Adjust capture rate
    - Save images
    - Compress if degraded
```

## Quick Start

### 1. Install Dependencies
```bash
pip install pymavlink pyyaml opencv-python
```

### 2. Configure Connection
Edit `config.yaml` - set your connection string:
```yaml
mavlink:
  connection_string: "/dev/ttyS0"  # Serial on Linux
  # OR "/dev/ttyUSB0" (USB serial)
  # OR "udp:127.0.0.1:14550" (UDP/simulation)
  baud: 115200
```

### 3. Set Health Thresholds
Edit `config.yaml` - adjust for your drone:
```yaml
battery_status:
  critical_battery: 25    # Land at 25%
  low_battery: 40         # Reduce rate at 40%
```

### 4. Run Mission
```python
from Raspberry_Pi_Agent.notmain import main
main()
```

## What Happens During Mission

1. **Preflight** (5-30 seconds)
   - Connect to flight controller
   - Verify all systems healthy
   - Request message streams
   - Wait for drone to be armed

2. **Waiting for Start** (0-60 seconds)
   - Drone must be armed
   - Drone must be in AUTO mode
   - Mission must be uploaded to flight controller

3. **Capturing** (during flight)
   - Camera captures at configured rate (1 fps default)
   - Monitor health constantly
   - If battery low → reduce rate
   - If any critical issue → stop capture

4. **Graceful Shutdown**
   - Drone disarmed or critical issue
   - Stop capture immediately
   - Save data
   - Close connections

## Important Configuration Points

### Connection String
- **Serial (most common):** `/dev/ttyS0` or `/dev/ttyUSB0`
- **UDP (simulation):** `udp:127.0.0.1:14550`
- **TCP:** `tcp:192.168.1.100:5760`

### Baud Rate
- **Standard ArduPilot:** 115200
- **MAVProxy:** 57600 (older systems)

### Health Thresholds
Adjust based on your drone's characteristics:
```yaml
# Aggressive (stop mission early to be safe)
critical_battery: 30
low_battery: 50
temp_critical: 75

# Conservative (fly until very low)
critical_battery: 15
low_battery: 30
temp_critical: 85
```

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| "Failed to connect" | Wrong serial port or baud rate | Check `ls /dev/tty*` and config |
| "No heartbeat received" | Flight controller offline | Power on drone, check cables |
| "Stale data" | Heartbeat not arriving | Check link quality, increase timeout |
| "Camera not opening" | Wrong camera ID | Change `camera.id` in config |
| "Permission denied /dev/ttyS0" | Serial port permissions | Run as root or add user to `dialout` group |

## Next Steps

1. **Test Connection:**
   ```python
   from Raspberry_Pi_Agent.mavlink_handler import MAVLinkHandler
   mavlink = MAVLinkHandler("/dev/ttyS0")
   mavlink.connect()  # Should say "Connected!"
   ```

2. **Test Mission Dry Run:**
   - Arm drone but stay on ground
   - Switch to AUTO mode
   - Run mission code
   - Should see capture controller output

3. **First Real Flight:**
   - Short flight over safe area
   - Monitor logs
   - Adjust thresholds as needed

4. **Production Deployment:**
   - Fine-tune health thresholds
   - Add custom event handlers
   - Implement image processing
   - Add telemetry uplink

---
## Support for ArduPilot Flight Modes

The system supports these common flight modes:
- STABILIZE - Manual with attitude hold
- ACRO - Manual acrobatic
- ALT_HOLD - Manual altitude lock
- AUTO - Automated waypoint mission
- GUIDED - Ground station commands
- LOITER - Hold position
- RTL - Return to launch
- CIRCLE - Circle around location

## Monitoring During Flight

Watch these logs during mission:
```
Connected! System: 1, Component: 1
Heartbeat - Armed: True, Status: IN_FLIGHT
SYS_STATUS - Battery: 95%, CPU: 45%
Battery - 11.4V, 95%
GPS - Fix: 3, Alt: 50.5m
Attitude - Roll: 2.3°, Pitch: -1.5°, Yaw: 45.2°
```

## Performance Notes

- Loop rate: 10Hz (100ms per iteration)
- Message processing: <5ms per message
- Capture overhead: ~10ms (depends on camera)
- Memory footprint: ~50MB (minimal on Pi)
- CPU usage: 15-30% (single core)


