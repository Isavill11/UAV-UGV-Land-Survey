# START HERE – UAV Raspberry Pi Agent

Welcome to the UAV Raspberry Pi Autonomous Mission System documentation.

This project implements:

- MAVLink communication with ArduPilot
- Health monitoring (battery, thermal, link, storage)
- Mission state machine control
- Adaptive image capture
- Adaptive image storage and transmission
- Ground station receiver with MD5 verification

If you are new to the system, follow this reading order:

---

# Documentation Overview

## 1: [SYSTEM_OVERVIEW.md](Raspberry_Pi_Agent/Documentation/SYSTEM_OVERVIEW.md)

- Full system architecture diagram
- Message flow diagrams
- State machine diagrams
- Thread architecture diagram
- Health evaluation logic tables
- File structure diagram
- Performance characteristics

Read this first to understand how everything connects.

---

## 2: [CONFIGURATION_REFERENCE.md](Raspberry_Pi_Agent/Documentation/CONFIGURATION_REFERENCE.md)
- MAVLink connection settings
- Battery thresholds
- Thermal thresholds
- Capture profiles
- Storage configuration
- Transmission batching
- Example configurations (conservative, long mission, etc)

---

## 3: DEPLOYMENT_AND_TESTING.md  (Run the System Safely)

- Environment setup checklist
- Hardware wiring diagram
- MAVLink connection tests
- Camera tests
- Dry run procedure
- Stress testing
- First flight checklist
- Troubleshooting table

Follow this before flying.

---

## 4: IMAGE_STORAGE_AND_TRANSMISSION.md  (Image Subsystem)

- ImageManager architecture diagram
- Directory structure diagrams
- Transmission packet format
- RSSI adaptive batching table
- Ground station directory structure
- API reference
- Deployment checklist

---

# System Architecture Overview

┌─────────────────────────────────────────────────────────┐
│                Flight Controller (ArduPilot)            │
│                 (Connected via Serial/UDP)              │
└────────────────────────────┬────────────────────────────┘
                             │
                      MAVLink Messages
                             │
┌────────────────────────────▼─────────────┐
│      MAVLinkHandler (mavlink_handler.py) │
│      - Receives MAVLink messages         │
│      - Routes to message handlers        │
│      - Manages connection lifecycle      │
└────────────────────┬─────────────────────┘
                     │
┌────────────────────┴──────────────────────┐
│                                           │
▼                                           ▼
┌───────────────────────┐  ┌──────────────────────┐
│ Health Tracking       │  │ Mission Controller   │
│ - DroneHealth         │->│ - State Machine      │
│ - PiHealth            │  │ - State Transitions  │
│ - LinkHealth          │  │ - Capture Control    │
│ - SystemHealth        │  └──────────────────────┘
└───────────────────────┘            │
                                     ▼
                          ┌──────────────────────┐
                          │ CaptureController    │
                          │ - Camera management  │
                          │ - Image capture      │
                          └──────────────────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ ImageManager         │
                 │ - StorageManager     │
                 │ - ImageTransmitter   │
                 └──────────────────────┘
                     │
                     ▼
          ┌──────────────────────┐ 
          │ Ground Station       │
          │ Receiver             │
          └──────────────────────┘



---

# 🔄 Mission State Machine

INIT → PREFLIGHT → READY → CAPTURING ↔ DEGRADED → FAILSAFE → SHUTDOWN


### Detailed State Logic
 
| State     | Description           | Exit Condition       |
|-----------|-----------------------|----------------------|
| INIT      | System initialization |  Config loaded       |
| PREFLIGHT | Health checks running |  Drone armed         |
| READY     | Waiting for AUTO mode |  AUTO detected       |
| CAPTURING | Full rate capture     |  Degraded or critical|
| DEGRADED  | Reduced rate capture  |  Recovery or critical|
| FAILSAFE  | Emergency stop        |  Shutdown            |
| SHUTDOWN  | Clean exit            |  End state           |

---

# 📡 MAVLink Message Mapping

| Message | Handler | Updates | Frequency |
|----------|----------|---------|-----------|
| HEARTBEAT | `_handle_heartbeat()` | Armed state | 1 Hz |
| SYS_STATUS | `_handle_sys_status()` | Battery %, CPU | 1 Hz |
| BATTERY_STATUS | `_handle_battery_status()` | Voltage | 1 Hz |
| GPS_RAW_INT | `_handle_gps_raw()` | Altitude | 1 Hz |
| LOCAL_POSITION_NED | `_handle_local_position()` | Position | 2 Hz |
| ATTITUDE | `_handle_attitude()` | Orientation | 1 Hz |

---

# RSSI Transmission Table

| RSSI (dBm) | Signal Quality | Batch Size |
|------------|----------------|------------|
| > -50 | Excellent | Full batch |
| -50 to -70 | Good | Full batch |
| -70 to -85 | Degraded | Half batch |
| -85 to -100 | Weak | Single |
| < -100 | Critical | None |

---

# Image Storage Structure

mission_data/
├── images/
├── metadata/
├── tx_queue/
└── sent/

received_images/
├── verified/
├── unverified/
├── failed/
└── metadata/


---

# Testing Phases Overview

1. Environment Setup
2. Hardware Setup
3. MAVLink Test
4. Camera Test
5. Dry Run
6. Stress Test
7. First Flight
8. Production Deployment

Full details in `DEPLOYMENT_AND_TESTING.md`.

---

# Quick Start:

1. Install dependencies:

`pip install -r requirements_mavlink.txt `

2. Configure `config.yaml`.

3. Run mission:

`python -m Raspberry_Pi_Agent.notmain`


4. Arm drone.
5. Switch to AUTO.
6. Monitor logs.
7. Disarm to shutdown.



