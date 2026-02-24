
# Running a test mission: 
*Prepare Configuration*
Raspberry_Pi_Agent/config.yaml
mavlink:
  connection_string: "udp:127.0.0.1:14550"  # For simulator
  # OR: "/dev/ttyS0" for real Raspberry Pi
  baud: 115200

camera:
  enable_on_start: false  # Can be true or false for testing



*Step 2: Run the Mission*
From your workspace root:
# Activate environment

cd "<working_directory>UAV-UGV-Land-Survey"

.\.venv\Scripts\Activate.ps1

# Start the mission
python -m Raspberry_Pi_Agent.notmain



# Testing Step-by-Step guide
### Test 1: Basic Configuration Test

cd "c:\Users\isav3\VSCode Projects\UAV-UGV-Land-Survey"
python test_image_integration.py

Expected output:
✓ PASS: Files Exist
✓ PASS: Configuration
✓ PASS: ImageManager Import
✓ PASS: CaptureController Integration
✓ PASS: notmain.py Integration
✓ PASS: Directory Structure
✓ ALL TESTS PASSED
---
### Test 2: Run Mission (Simulator or Real)
Terminal 1: Start ground station receiver
python ground_station_receiver.py --port 9999 --protocol udp
Output: "UDP listening on 0.0.0.0:9999"

Terminal 2: Start mission
python -m Raspberry_Pi_Agent.notmain
Output: Mission logs including image captures and transmissions

Terminal 3: Monitor filesystem (optional)
Watch for files being created in:
   - mission_data/images/         (captured)
   - mission_data/sent/           (transmitted)
   - mission_data/metadata/       (metadata)

### Test 3: View Received Images
On ground station machine:
ls -lh received_images/verified/2026-02-*/
Shows all received and verified images



## Observations during testing: 
Key Observations During Testing
Terminal 1 (Mission - notmain.py):

2026-02-23 13:40:05 - Raspberry_Pi_Agent - INFO - AutonomousMission initialized
2026-02-23 13:40:05 - ImageManager - INFO - Image transmission thread started
2026-02-23 13:40:10 - CaptureController - INFO - Captured and stored: IMG_20260223_134005_123.jpg
2026-02-23 13:40:10 - ImageManager - DEBUG - Transmitting 10 images, 126 KB (RSSI: -65/)
2026-02-23 13:40:11 - ImageManager - INFO - ✓ Transmission successful: IMG_20260223_134005_123.jpg

Terminal 2 (Ground Station - ground_station_receiver.py):

2026-02-23 13:40:11 - ImageReceiver - INFO - ✓ Received: IMG_20260223_134005_123.jpg (12345 bytes)
2026-02-23 13:40:11 - ImageReceiver - DEBUG - Saved image: received_images/verified/2026-02-23/IMG_20260223_134005_123.jpg
2026-02-23 13:40:11 - ImageReceiver - DEBUG - Saved metadata: received_images/metadata/IMG_20260223_134005_123.jpg.json

Filesystem (mission_data/ after 30 seconds):

mission_data/
├─ images/               # Currently empty (all sent)
├─ sent/                 # 10+ images (transmitted successfully)
├─ metadata/
│  └─ index.json         # All image metadata entries
└─ logs/                 # Mission logs (if enabled)










# Data flow: 
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MISSION STARTUP SEQUENCE                            │
└─────────────────────────────────────────────────────────────────────────────┘

1. notmain.py MAIN INITIALIZATION (lines 34-71)
   ├─ Load config.yaml (SelfCheckPrelaunch)
   ├─ Initialize SystemHealth (DroneHealth, PiHealth, LinkHealth)
   ├─ Initialize ImageManager ← ImageManager.__init__()
   │   ├─ Create mission_data/ directory structure
   │   ├─ Initialize StorageManager
   │   └─ Initialize ImageTransmitter (but thread not started yet)
   ├─ Initialize CaptureController (with image_manager reference)
   ├─ Initialize MissionController
   └─ Initialize MAVLinkHandler

2. MAVLink Connection Setup (lines 139-175)
   ├─ Connect to flight controller (simulator or real)
   ├─ Start listening thread
   ├─ Register message handlers for: HEARTBEAT, SYS_STATUS, GPS_RAW_INT, etc.
   └─ Request message intervals from flight controller

3. Start Transmission Thread (line 156)
   ├─ image_manager.start_transmission().
   │   └─ ImageTransmitter starts background thread
   │       └─ Thread loops every 5 seconds checking for pending images
   └─ Ready to transmit when images arrive

4. Preflight Checks & Wait (lines 166-184)
   ├─ Run preflight_check()
   ├─ Wait for startup_delay
   ├─ Log: "Waiting for mission start conditions..."
   ├─ Log: "  - Arm the drone"
   ├─ Log: "  - Switch to AUTO mode"
   └─ Log: "  - Upload mission via Mission Planner"

5. MAIN MISSION LOOP STARTS (line 190, at ~10Hz)
   └─ Continuous cycle...

┌─────────────────────────────────────────────────────────────────────────────┐
│                      MISSION LOOP (10Hz = Every 0.1s)                       │
└─────────────────────────────────────────────────────────────────────────────┘

EVERY LOOP ITERATION:

1. UPDATE CAPTURE CONTROLLER (line 200)
   capture_controller.update()
   ├─ Check if It's time to capture (based on interval)
   ├─ If yes:
   │   └─ Call _capture_frame()
   │       ├─ Get image from camera (cv2.read)
   │       ├─ Encode to JPEG bytes
   │       └─ Call image_manager.save_captured_image()
   │           ├─ Generate filename: IMG_20260223_134522_123.jpg
   │           ├─ Calculate MD5 hash
   │           ├─ Create metadata JSON:
   │           │  {
   │           │    "filename": "IMG_...",
   │           │    "timestamp": "2026-02-23T13:45:22.123",
   │           │    "altitude": 45.7,          ← FROM LAST UPDATE
   │           │    "profile": "CAPTURING",
   │           │    "size_bytes": 12345,
   │           │    "md5_hash": "a1b2c3d4...",
   │           │  }
   │           ├─ Save image to: mission_data/images/IMG_20260223_134522_123.jpg
   │           ├─ Save metadata to: mission_data/metadata/index.json
   │           └─ Log: "Captured and stored: IMG_..."
   └─ Return True/False

2. UPDATE MISSION CONTROLLER STATE MACHINE (line 203)
   mission_controller.update()
   ├─ Check system health
   ├─ Evaluate battery, storage, thermal, link quality
   ├─ Transition between states: INIT → PREFLIGHT → READY → CAPTURING → DEGRADED/FAILSAFE
   ├─ Apply capture profile based on state:
   │   ├─ CAPTURING: Start capture at 1.0s intervals
   │   ├─ DEGRADED: Reduce to 5.0s intervals
   │   └─ FAILSAFE/SHUTDOWN: Stop capture
   └─ Log state transitions

3. RECEIVE MAVLink MESSAGES (handled by separate thread)
   (Messages arrive asynchronously from flight controller)
   ├─ HEARTBEAT (location: health.py update_from_heartbeat)
   │  └─ Updates: armed, system_status
   ├─ SYS_STATUS (location: health.py update_from_sys_status)
   │  └─ Updates: battery_remaining, cpu_load
   ├─ BATTERY_STATUS (location: health.py update_from_battery_status)
   │  └─ Updates: battery_voltage, battery_current
   ├─ GPS_RAW_INT (location: health.py update_from_gps_raw)
   │  └─ Updates: altitude, lat, lon, gps_fix_type
   └─ LOCAL_POSITION_NED (location: health.py update_from_local_position)
      └─ Updates: relative position

4. UPDATE ALTITUDE FOR NEXT CAPTURE (line 206)
   capture_controller.set_altitude(system_health.drone.altitude)
   └─ Sets: self.current_altitude = 45.7
       ↑ This gets used in NEXT image capture

5. CHECK HEARTBEAT (line 209-215)
   ├─ Is MAVLink connection alive?
   ├─ Set system_health.radio.connected = True/False
   └─ If no heartbeat → Mission will eventually go to FAILSAFE

6. TRIGGER IMAGE TRANSMISSION (line 217-224)
   ├─ Get RSSI (signal strength): rssi = -65 dBm (example)
   ├─ Call image_manager.transmit_batch(rssi)
   │   └─ Background ImageTransmitter thread:
   │       ├─ Calculate batch size based on RSSI:
   │       │   ├─ RSSI < -50: 10 images
   │       │   ├─ RSSI < -70: 10 images  ← (example: -65 fits here)
   │       │   ├─ RSSI < -85: 5 images
   │       │   └─ RSSI < -100: 0 images (don't send)
   │       ├─ Get pending images from mission_data/images/
   │       ├─ For each image:
   │       │   ├─ Create transmission packet:
   │       │   │  [Header(7B) | Filename | Metadata | Image | MD5]
   │       │   ├─ Send via UDP to ground_station_ip:9999
   │       │   ├─ If success:
   │       │   │   ├─ Move image to: mission_data/sent/
   │       │   │   └─ Update metadata: transmission_state = "sent"
   │       │   └─ If failed:
   │       │       ├─ Keep in: mission_data/images/
   │       │       ├─ Increment transmission_attempts
   │       │       └─ Retry later
   │       └─ Log transmission statistics
   └─ Note: This doesn't block - happens in background thread

7. MAINTAIN LOOP TIMING (line 227-232)
   ├─ Calculate elapsed time
   ├─ Sleep to maintain 10Hz (0.1s per loop)
   └─ If slow, log warning

THEN LOOP BACK TO STEP 1 (repeat every 100ms)

┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKGROUND THREADS                                  │
└─────────────────────────────────────────────────────────────────────────────┘

1. MAVLink Listening Thread (started at line 147)
   ├─ Continuously listens for messages from flight controller
   ├─ When message arrives:
   │   └─ Call registered handler (from setup_mavlink_handlers)
   │       ├─ _handle_heartbeat()
   │       ├─ _handle_sys_status()
   ├─ Update SystemHealth datatypes
   └─ All updates available in main loop via: system_health.drone.*

2. Image Transmission Thread (started at line 156)
   ├─ Started by: image_manager.start_transmission()
   ├─ Runs independently every 5 seconds
   ├─ Checks: Are there pending images? Is link quality OK?
   ├─ Sends batches based on RSSI
   └─ Runs until: image_manager.stop_transmission()

SHUTDOWN SEQUENCE (line 259-270):
├─ image_manager.stop_transmission()    ← Stop transmission thread
├─ mission_controller.request_stop()    ← Stop state machine
├─ capture_controller.stop()            ← Stop camera capture
├─ mavlink.stop_listening()             ← Stop MAVLink thread
├─ mavlink.disconnect()                 ← Close connection
└─ Log final statistics