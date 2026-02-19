# UAV Raspberry Pi Agent – System Overview

## 1. Executive Summary

This system implements a fully autonomous Raspberry Pi agent onboard a UAV.  
It integrates MAVLink communication, health monitoring, mission state control, adaptive image capture, and adaptive image transmission to a ground station.

The agent:

- Connects to an ArduPilot flight controller via MAVLink
- Monitors drone and Raspberry Pi health
- Executes a mission state machine
- Captures images adaptively
- Stores and transmits images based on link quality
- Handles failsafe and shutdown conditions automatically

---

## 2. System Architecture

### High-Level Architecture

Flight Controller (ArduPilot)  
→ MAVLinkHandler  
→ Health System (DroneHealth, PiHealth, LinkHealth)  
→ SystemHealth Evaluation  
→ MissionController (State Machine)  
→ CaptureController  
→ ImageManager (Storage + Transmission)

---

## 3. Data Flow

1. Flight controller sends MAVLink messages (HEARTBEAT, SYS_STATUS, GPS, etc.).
2. MAVLinkHandler receives and routes messages.
3. Health objects update internal state.
4. SystemHealth evaluates thresholds.
5. MissionController determines mission state.
6. CaptureController adjusts capture profile.
7. ImageManager saves and transmits images.

This loop runs at ~10Hz.

---

## 4. Mission State Machine

### States

- INIT
- PREFLIGHT
- READY
- CAPTURING
- DEGRADED
- FAILSAFE
- SHUTDOWN

### Normal Flow

INIT → PREFLIGHT → READY → CAPTURING → SHUTDOWN

### Adaptive Transitions

| Condition | Transition |
|------------|------------|
| Battery 25–40% | CAPTURING → DEGRADED |
| Battery <25% | → FAILSAFE |
| Temp >80°C | → FAILSAFE |
| RSSI Critical | → FAILSAFE |
| Drone Disarmed | → SHUTDOWN |
| Recovery | DEGRADED → CAPTURING |

---

## 5. Health Evaluation Logic

Evaluated every loop cycle.

### Drone Health
- Battery percentage
- Voltage
- Armed state
- GPS lock
- Altitude

### Raspberry Pi Health
- CPU temperature
- Storage availability
- CPU load

### Radio Link Health
- RSSI
- Packet errors
- Heartbeat timeout

### Decision Rule

- Any CRITICAL issue → SystemState.CRITICAL
- Any DEGRADED issue → SystemState.DEGRADED
- All OK → SystemState.OK

---

## 6. Thread Architecture

### Main Thread
- Runs mission loop
- Updates state machine
- Triggers capture and transmission

### MAVLink Listener Thread
- Receives MAVLink messages
- Calls registered handlers
- Updates health objects

### Image Transmission Thread
- Sends image batches
- Adjusts based on RSSI
- Handles retries

Thread-safe locking ensures no race conditions.

---

## 7. File Structure
Raspberry_Pi_Agent/
│
├── notmain.py
├── mavlink_handler.py
├── image_manager.py
├── config.yaml
│
├── Mission_Controller/
│ ├── mission_controller.py
│ ├── capture_controller.py
│ └── health.py
│
└── mission_data/
├── images/
├── metadata/
├── tx_queue/
└── sent/



---

## 8. Performance Characteristics

- Loop Rate: 10 Hz
- CPU Usage: 15–30%
- Memory: ~50MB
- Image Size (90% JPEG): 100–150KB
- Storage Use: ~500MB/hour at 1 fps

---

## 9. Known Limitations

- OpenCV-compatible cameras only
- Storage limited by SD card
- No onboard ML processing yet
- Transmission depends on WiFi quality

---

## 10. Future Enhancements

- Real-time AI processing
- Telemetry uplink
- Web dashboard
- Multi-camera support
- Swarm coordination
