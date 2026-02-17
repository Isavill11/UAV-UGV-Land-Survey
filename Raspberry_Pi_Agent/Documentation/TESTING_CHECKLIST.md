
# ===============================================================
# PHASE 1: ENVIRONMENT SETUP 
# ===============================================================

STEPS = """
□ 1. Install Python Dependencies
      $ pip install -r Raspberry_Pi_Agent/requirements_mavlink.txt
      
      Should see: Successfully installed pymavlink, pyyaml, opencv-python

□ 2. Verify Python Version
      $ python --version
      
      Required: Python 3.8+
      Recommended: Python 3.10 or higher

□ 3. Check Raspberry Pi Serial Port
      $ ls /dev/tty*
      
      Look for: /dev/ttyS0 or /dev/ttyUSB0
      (exact device name goes in config.yaml)

□ 4. Enable Serial Port on Raspberry Pi (if needed)
      $ sudo raspi-config
      → Interface Options → Serial Port → Enable
      
      Then reboot:
      $ sudo reboot

□ 5. Verify Config File
      Edit: Raspberry_Pi_Agent/config.yaml
      
      Check these values:
      ✓ camera.id: 0 (or correct device number)
      ✓ mavlink.connection_string: "/dev/ttyS0" (or your device)
      ✓ mavlink.baud: 115200
      ✓ platform.loop_rate_hz: 10
"""

# ================================================================
# PHASE 2: HARDWARE TESTING 
# ================================================================

HARDWARE_TEST = """
□ 1. Power On Flight Controller
      - Connect to USB or battery
      - LED should indicate power
      
□ 2. Connect Raspberry Pi Serial Port
      Flight Controller TELEM2 Port:
      ┌─────────────────────┐
      │ Pin 1 (GND) → GND   │
      │ Pin 2 (TX)  → RX    │  ← Note: TX to RX (crossed)
      │ Pin 3 (RX)  → TX    │  ← Note: RX to TX (crossed)
      │ Pin 4 (5V)  → N/C   │  ← Usually NOT connected
      └─────────────────────┘
      
      Raspberry Pi Serial Port (GPIO):
      GPIO 14 (TXD) connects to FC RX
      GPIO 15 (RXD) connects to FC TX
      GND connects to GND

□ 3. Power On Raspberry Pi
      Should see boot messages

□ 4. Test Serial Connection (Optional)
      $ sudo systemctl stop serial-getty@ttyS0.service
      $ screen /dev/ttyS0 115200
      
      You should see ArduPilot boot messages
      Press Ctrl-A then Ctrl-\ to exit
"""

# =============================================================
# PHASE 3: SOFTWARE TESTING
# =============================================================

CONNECTION_TEST = """
□ 1. Test MAVLink Connection

      Create test_connection.py:
      ─────────────────────────────
      from Raspberry_Pi_Agent.mavlink_handler import MAVLinkHandler
      
      mavlink = MAVLinkHandler("/dev/ttyS0", 115200)
      
      if mavlink.connect():
          print("✓ Connected to flight controller!")
          print(f"System: {mavlink.master.target_system}")
      else:
          print("✗ Failed to connect")
      ─────────────────────────────
      
      Run:
      $ python test_connection.py
      
      Expected output:
      Connecting to /dev/ttyS0...
      Connected! System: 1, Component: 1
      ✓ Connected to flight controller!
      
      Troubleshooting:
      - "No heartbeat received" → Check cable connections
      - "Permission denied" → Run with sudo or fix permissions
      - "Connection refused" → Check baud rate matches FC

□ 2. Test Message Reception

      Create test_messages.py:
      ─────────────────────────────
      from Raspberry_Pi_Agent.mavlink_handler import MAVLinkHandler
      import time
      
      mavlink = MAVLinkHandler("/dev/ttyS0", 115200)
      mavlink.connect()
      
      def on_msg(msg):
          print(f"Received: {msg.get_type()}")
      
      mavlink.register_handler("HEARTBEAT", on_msg)
      mavlink.register_handler("SYS_STATUS", on_msg)
      
      mavlink.start_listening()
      
      for i in range(10):
          print(f"Waiting... {i+1}s")
          time.sleep(1)
      
      mavlink.stop_listening()
      mavlink.disconnect()
      ─────────────────────────────
      
      Run:
      $ python test_messages.py
      
      Expected output (every 1 second):
      Received: HEARTBEAT
      Received: SYS_STATUS
      
      Troubleshooting:
      - No output → Check heartbeat timeout or link quality

□ 3. Test Health Monitoring

      Create test_health.py:
      ─────────────────────────────
      from Raspberry_Pi_Agent.verify_config import SelfCheckPrelaunch
      from Raspberry_Pi_Agent.Mission_Controller.health import (
          DroneHealth, SystemHealth, PiHealth, LinkHealth
      )
      
      check = SelfCheckPrelaunch('config.yaml')
      check.run()
      config = check.config
      
      health = SystemHealth(
          drone=DroneHealth(),
          pi=PiHealth(),
          radio=LinkHealth()
      )
      
      # Simulate drone data
      health.drone.battery_remaining = 85
      health.drone.armed = True
      health.drone.battery_voltage = 11.4
      
      state, issues = health.evaluate(config)
      
      print(f"System State: {state}")
      print(f"Issues: {issues}")
      ─────────────────────────────
      
      Run:
      $ python test_health.py
      
      Expected output:
      System State: SystemState.OK
      Issues: []

□ 4. Test Capture Controller

      Create test_camera.py:
      ─────────────────────────────
      from Raspberry_Pi_Agent.verify_config import SelfCheckPrelaunch
      from Raspberry_Pi_Agent.Mission_Controller.capture_controller import CaptureController
      
      check = SelfCheckPrelaunch('config.yaml')
      check.run()
      config = check.config
      
      camera = CaptureController(config)
      
      try:
          camera.apply_profile("CAPTURING")
          camera.start()
          print("✓ Camera started")
          
          # Capture 5 frames
          for i in range(5):
              camera.update()
              time.sleep(1)
          
          camera.stop()
          print("✓ Camera stopped")
      except Exception as e:
          print(f"✗ Camera error: {e}")
      ─────────────────────────────
      
      Run:
      $ python test_camera.py
      
      Expected:
      - Creates captured_images/full directory
      - Saves 5 JPEG images
      - No errors
"""

# ==================================================================
# PHASE 4: DRY RUN TEST (WITH DRONE ON GROUND)
# ==================================================================

DRY_RUN = """
BEFORE STARTING:
- ⚠️  Keep drone on the ground
- ⚠️  Don't arm yet
- ⚠️  Have battery checker ready

□ 1. Start the Mission Code

      $ python -c "from Raspberry_Pi_Agent.notmain import main; main()"
      
      Expected output:
      ────────────────────────────────────
      Connecting to flight controller...
      Connected! System: 1, Component: 1
      Setting up MAVLink message handlers...
      Requesting flight controller messages...
      Running preflight checks...
      Preflight checks PASSED
      Waiting {N}s for drone initialization...
      Mission loop running at 10Hz
      ════════════════════════════════════════
      
      Status: Code is running! ✓

□ 2. Monitor Output for 5 Seconds
      
      You should see recurring logs like:
      ────────────────────────────────────
      Heartbeat - Armed: False, Status: 0
      SYS_STATUS - Battery: 100%, CPU: 35%
      Battery - 12.3V, 100%
      
      Status: Messages being received! ✓

□ 3. Now ARM the Drone (via RC or Mission Planner)
      
      Expected: Code should detect armed state
      ────────────────────────────────────
      Heartbeat - Armed: True, Status: 3
      Mission - Waiting for mission start conditions...
      
      Status: State machine working! ✓

□ 4. Set to AUTO Mode (via RC or Mission Planner)
      
      Expected: Mission should transition to CAPTURING
      ────────────────────────────────────
      State transition: READY → CAPTURING
      Camera started - profile: CAPTURING
      Captured: captured_images/full/img_20240217_HHMMSS_mmm.jpg
      
      Status: Camera activated! ✓

□ 5. Check Captured Images
      
      $ ls -la Raspberry_Pi_Agent/captured_images/full/
      
      Should see JPEG files created:
      img_20240217_123456_001.jpg
      img_20240217_123457_002.jpg
      
      Status: Image capture working! ✓

□ 6. Disarm the Drone (via RC or Mission Planner)
      
      Expected: Mission should gracefully shutdown
      ────────────────────────────────────
      Drone disarmed - mission complete!
      Shutting down mission...
      Mission shutdown complete
      
      Status: Graceful shutdown working! ✓
"""

# ===================================================================
# PHASE 5: STRESS TESTING (Optional, 20 minutes)
# ===================================================================

STRESS_TEST = """
Test system behavior under degraded conditions:

□ 1. Simulate Low Battery
      - Use Mission Planner battery failsafe
      - Set it to trigger at 80% capacity
      - Watch system transition to DEGRADED
      - Verify capture rate reduces from 1fps to 0.2fps

□ 2. Simulate High Temperature  
      - Run CPU intensive task in background
      - $ stress --cpu 4 --timeout 60s
      - Monitor Pi temperature in health logs
      - Should see thermal warnings if > 70°C

□ 3. Simulate Poor Radio Link
      - Use RF signal attenuator (metal can)
      - Watch RSSI degrade in logs
      - System should transition to DEGRADED
      - Eventually FAILSAFE if signal lost

□ 4. Test Recovery
      - Remove attenuator
      - System should recover back to CAPTURING
      - Verify capture rate increases again
"""

# ==================================================================
# PHASE 6: FIRST FLIGHT (WITH SAFETY MEASURES)
# ==================================================================

FIRST_FLIGHT = """
SAFETY CHECKLIST:
☐ Arm the Raspberry Pi somewhere safe
☐ Use a freshly charged battery
☐ Fly in open area with no obstacles
☐ Have manual RTL mode ready on RC
☐ Monitor logs on connected laptop (optional)
☐ Be ready to land immediately if issues

PROCEDURE:
1. Power on flight controller
2. Power on Raspberry Pi agent
3. Connect to Mission Planner on laptop
4. Upload mission waypoints
5. Wait for GPS lock (green light)
6. Arm the drone
7. Switch to AUTO mode
8. Monitor:
   - Battery voltage (shouldn't drop >10%)
   - Radio link quality (good signal bars)
   - Camera capture (check after flight)
9. Disarm when done (lands drone)
10. Save logs from flight controller AND Pi

POST-FLIGHT ANALYSIS:
- Check captured_images/full/ for images
- Verify file timestamps and sizes
- Review logs for any warnings
- Check battery voltage curve
- Look for any RSSI anomalies

ITERATE:
- Adjust health thresholds based on observations
- Fine-tune capture intervals
- Add custom processing if needed
"""

# ================================================================
# PHASE 7: PRODUCTION DEPLOYMENT
# ================================================================

PRODUCTION = """
Before deploying for mission:

□ 1. Optimize Configuration
      - Set battery thresholds for your LiPo
      - Adjust capture quality based on storage
      - Set realistic mission duration
      - Configure thermal limits for Pi case

□ 2. Add Logging & Telemetry
      - Save mission logs to SD card
      - Optional: Send telemetry to ground station
      - Track mission statistics (battery curve, etc)

□ 3. Implement Auto-Recovery
      - Optional: Auto-restart on crash
      - Set up watchdog timer
      - Log recovery attempts

□ 4. Performance Tuning
      - Profile CPU usage
      - Monitor memory for leaks
      - Optimize capture resolution
      - Consider reduced loop rate for battery life

□ 5. Backup & Recovery
      - Daily backup of captured images
      - Keep log files for analysis
      - Have spare SD cards
      - Test recovery procedures

□ 6. Monitoring During Long Missions
      - Periodically check disk space
      - Monitor temperature trends
      - Watch for link quality degradation
      - Have abort procedure ready
"""

# =================================================================
# TROUBLESHOOTING TABLE
# =================================================================

TROUBLESHOOTING = """
╔════════════════════════════════════════════════════════════════════════════╗
║                        TROUBLESHOOTING GUIDE                              ║
╠════════════════════════════════════════════════════════════════════════════╣
║ PROBLEM                    │ CAUSES                    │ SOLUTIONS         ║
╠────────────────────────────┼───────────────────────────┼─────────────────╣
║ Can't connect              │ - Wrong serial port       │ Check /dev/tty* ║
║                            │ - Wrong baud rate        │ Verify 115200   ║
║                            │ - Cable disconnected     │ Check cable     ║
║                            │ - FC not powered         │ Power on FC     ║
╠────────────────────────────┼───────────────────────────┼─────────────────╣
║ No heartbeat received      │ - Link quality bad       │ Move closer/   ║
║                            │ - Message rate too low   │ different cable ║
║                            │ - Buffer overflow        │ Reduce loop rate║
╠────────────────────────────┼───────────────────────────┼─────────────────╣
║ Camera won't open          │ - Wrong camera ID        │ Check /dev/vid* ║
║                            │ - Camera not enabled     │ raspi-config    ║
║                            │ - USB camera unplugged   │ Check connection║
╠────────────────────────────┼───────────────────────────┼─────────────────╣
║ Images not saving          │ - Wrong save directory   │ Create dir first║
║                            │ - No storage space       │ Check df -h     ║
║                            │ - Permission denied      │ Check ownership ║
╠────────────────────────────┼───────────────────────────┼─────────────────╣
║ System goes to FAILSAFE    │ - Battery too low        │ Charge battery  ║
║ immediately                │ - Temperature too high   │ Cool Pi down    ║
║                            │ - Storage full           │ Delete old data ║
║                            │ - Link quality bad       │ Check antenna   ║
╠────────────────────────────┼───────────────────────────┼─────────────────╣
║ Capture rate very slow     │ - I/O bottleneck        │ Use faster SD   ║
║                            │ - CPU maxed out         │ Lower resolution║
║                            │ - Storage full          │ Clean up drive  ║
╠────────────────────────────┼───────────────────────────┼─────────────────╣
║ Weird health readings      │ - Sensor noise          │ Add hardware filt║
║                            │ - Stale data            │ Check data age  ║
║                            │ - Integration issue     │ Restart service ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

# =================================================================
# COMMAND REFERENCE
# =================================================================

COMMANDS = """
Useful Commands for Testing & Debugging:

# Test serial connection
$ screen /dev/ttyS0 115200

# Monitor Pi temperature
$ watch -n 1 'cat /sys/class/thermal/thermal_zone0/temp | xargs -I {} python3 -c "print(f\"{float({} )/1000:.1f}°C\")"'

# Check disk space
$ df -h /

# Monitor process resources
$ top

# View system logs
$ journalctl -u mission --follow

# Kill running mission
$ pkill -f "python.*notmain"

# Check USB devices
$ lsusb

# Check serial devices
$ ls -la /dev/tty*

# Monitor I/O
$ iostat -x 1

# Check camera
$ v4l2-ctl --list-devices

# Test camera
$ libcamera-hello --preview 0 --timeout 5000
"""

print(STEPS)
print(HARDWARE_TEST)
print(CONNECTION_TEST)
print(DRY_RUN)
print(STRESS_TEST)
print(FIRST_FLIGHT)
print(PRODUCTION)
print(TROUBLESHOOTING)
print(COMMANDS)
