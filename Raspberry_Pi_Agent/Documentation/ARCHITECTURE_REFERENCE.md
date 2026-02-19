"""
ARCHITECTURE AND DATA FLOW DOCUMENTATION

This document explains how MAVLink messages flow through the system and 
how the state machine makes decisions.
"""

# ============================================================================
# 1. MESSAGE FLOW ARCHITECTURE
# ============================================================================

"""
                    ┌─────────────────────────────────┐
                    │   ArduPilot Flight Controller   │
                    │   (on drone, running mission)   │
                    └──────────────┬──────────────────┘
                                   │
                        MAVLink Protocol (binary)
                         Serial @ 115200 baud
                                   │
                    ┌──────────────▼──────────────┐
                    │   Raspberry Pi              │
                    │   /dev/ttyS0                │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │ MAVLinkHandler Thread       │
                    │ - Reads socket/serial       │
                    │ - Parses MAVLink binary     │
                    │ - Routes to handlers        │
                    └──────────────┬──────────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                │                  │                  │
                ▼                  ▼                  ▼
        ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐
        │  HEARTBEAT      │ │  SYS_STATUS     │ │ BATTERY_     │
        │  Handler        │ │  Handler        │ │ STATUS       │
        │                 │ │                 │ │ Handler      │
        │ updates:        │ │ updates:        │ │              │
        │ - armed         │ │ - battery%      │ │ updates:     │
        │ - system_status │ │ - cpu_load      │ │ - voltage    │
        └────────┬────────┘ └────────┬────────┘ │ - capacity%  │
                 │                   │          └──────┬───────┘
                 └───────────────────┼─────────────────┘
                                     │
                    ┌────────────────▼────────────┐
                    │   DroneHealth Object        │
                    │                             │
                    │  battery_remaining: 75%     │
                    │  battery_voltage: 11.4V     │
                    │  armed: True                │
                    │  cpu_load: 45%              │
                    │  last_update: 1708123456.5  │
                    └────────────────┬────────────┘
                                     │
                    ┌────────────────▼────────────┐
                    │  SystemHealth.evaluate()    │
                    │  - Checks all thresholds    │
                    │  - Returns: state + issues  │
                    └────────────────┬────────────┘
                                     │
                    ┌────────────────▼────────────┐
                    │  MissionController.update() │
                    │  - Evaluates transitions    │
                    │  - Changes capture profile  │
                    └────────────────┬────────────┘
                                     │
                    ┌────────────────▼────────────┐
                    │ CaptureController.update()  │
                    │ - Captures frames at rate   │
                    │ - Saves to disk             │
                    └─────────────────────────────┘
"""

# ============================================================================
# 2. STATE MACHINE TRANSITION LOGIC
# ============================================================================

"""
The mission state machine controls what the system does based on:
  1. Health status (battery, temperature, link quality)
  2. Drone armed state
  3. Capture mode
  4. Time elapsed

DETAILED STATE TRANSITIONS:

┌─────────────────────────────────────────────────────────────────────────────┐
│ STATE: INIT                                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ WHAT IT DOES:                                                               │
│ - System initializing, config loaded, components created                    │
│ - Camera off, nothing being captured                                        │
│                                                                             │
│ CONDITIONS:                                                                 │
│ - ready = True → PREFLIGHT                                                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ STATE: PREFLIGHT                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ WHAT IT DOES:                                                               │
│ - Running health checks (battery, temperature, storage, link)               │
│ - Verifying camera is functional                                            │
│ - Waiting for user to arm drone                                             │
│                                                                             │
│ CONDITIONS:                                                                 │
│ - drone.armed=True AND start_requested=True → READY                         │
│ - health=CRITICAL → FAILSAFE                                                │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ STATE: READY                                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ WHAT IT DOES:                                                               │
│ - Drone is armed and awaiting AUTO mode mission start                       │
│ - Camera still off                                                          │
│ - Waiting for flight plan execution to begin                                │
│                                                                             │
│ CONDITIONS:                                                                 │
│ - drone.armed=True AND running=True → CAPTURING                             │
│ - drone.armed=False → SHUTDOWN                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ STATE: CAPTURING                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ WHAT IT DOES:                                                               │
│ - PRIMARY MISSION STATE: Capturing images at full resolution                │
│ - Camera on, 1 image per second (default)                                   │
│ - Mission timer started                                                     │
│                                                                             │
│ CONDITIONS (checked every loop ~100ms):                                     │
│ ┌─ health.state = CRITICAL                    → FAILSAFE                    │
│ │  (battery <25%, temp >80C, link lost, storage full)                       │
│ │                                                                           │
│ ├─ health.state = DEGRADED                    → DEGRADED                    │
│ │  (battery 25-40%, temp 75-80C, link poor, storage low)                    │
│ │                                                                           │
│ ├─ drone.armed = False                        → SHUTDOWN                    │
│ │  (user disarmed in Mission Planner or via RC)                             │
│ │                                                                           │
│ └─ health.state = OK                          → stay in CAPTURING           │
│    (all systems green, keep going!)                                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ STATE: DEGRADED                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ WHAT IT DOES:                                                               │
│ - FALLBACK MODE: Reduced capture rate to save resources                     │
│ - Camera on, 1 image per 5 seconds (default)                                │
│ - Lower JPEG quality (50% instead of 90%)                                   │
│ - Attempts to continue mission on limited resources                         │
│                                                                             │
│ CONDITIONS (checked every loop):                                            │
│ ┌─ health.state = CRITICAL                    → FAILSAFE                    │
│ │  (situation got worse)                                                    │
│ │                                                                           │
│ ├─ health.state = OK                          → CAPTURING                   │
│ │  (system recovered, resume normal operation)                              │
│ │                                                                           │
│ ├─ drone.armed = False                        → SHUTDOWN                    │
│ │  (user disarmed)                                                          │
│ │                                                                           │ 
│ └─ health.state = DEGRADED                    → stay in DEGRADED            │
│    (still degraded, continue with reduced rate)                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ STATE: FAILSAFE                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ WHAT IT DOES:                                                               │
│ - EMERGENCY MODE: Stop all captures immediately                             │
│ - Camera off                                                                │
│ - Wait for human intervention                                               │
│ - Log critical issues for debugging                                         │
│                                                                             │
│ CONDITIONS:                                                                 │
│ - Always transitions to → SHUTDOWN after brief wait                         │
│   (automatic full stop, human must decide next action)                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ STATE: SHUTDOWN                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ WHAT IT DOES:                                                               │
│ - Graceful termination of mission                                           │
│ - Camera off, capture stopped                                               │
│ - Close MAVLink connection                                                  │
│ - Write final logs                                                          │
│ - Exit mission loop                                                         │
│                                                                             │
│ CONDITIONS:                                                                 │
│ - END STATE: Mission terminated, system idle                                │
└─────────────────────────────────────────────────────────────────────────────┘


TYPICAL MISSION SCENARIO:

Time    Event                          State           Action
────    ─────                          ─────           ──────
0:00    System starts                  INIT            Load config
0:05    Preflight completes            PREFLIGHT       Waiting for arm
2:30    User arms drone                READY           Awaiting AUTO
2:35    User sets AUTO mode            CAPTURING       Camera on, capturing
15:00   Battery drops to 35%           DEGRADED        Reduce rate
20:00   Battery recovers               CAPTURING       Normal rate
30:00   User disarms (done)            SHUTDOWN        Save data, exit
"""

# ============================================================================
# 3. HEALTH EVALUATION LOGIC
# ============================================================================

"""
Every 100ms (in main loop), the system evaluates health using this logic:

1. DRONE HEALTH CHECK:
   └─ Is there a recent heartbeat? (within 2 seconds)
   └─ Battery remaining: 
      ├─ > 40%  → OK
      ├─ 25-40% → LOW (triggers DEGRADED state)
      └─ < 25%  → CRITICAL (triggers FAILSAFE)
   └─ Armed state (from HEARTBEAT message)

2. RASPBERRY PI HEALTH CHECK:
   └─ CPU Temperature:
      ├─ < 70°C  → OK
      ├─ 70-80°C → WARM (degraded state)
      └─ > 80°C  → HOT (failsafe)
   └─ Storage:
      ├─ > 500MB free  → OK
      └─ < 500MB free  → LOW (degraded state)

3. RADIO LINK QUALITY CHECK:
   └─ Is heartbeat being received?
      ├─ No heartbeat for >2s → STALE → CRITICAL
      └─ Yes, check RSSI signal strength:
         ├─ RSSI > 70dBm  → OK
         ├─ 70-85dBm      → DEGRADED
         └─ < 85dBm       → CRITICAL

4. COMBINE ALL CHECKS:
   └─ ANY CRITICAL issue → SystemState.CRITICAL → FAILSAFE
   └─ ANY DEGRADED issue → SystemState.DEGRADED → DEGRADED
   └─ All OK             → SystemState.OK       → CAPTURING

This happens inside: SystemHealth.evaluate(config)
"""

# ============================================================================
# 4. MESSAGE TYPES AND UPDATE FREQUENCY
# ============================================================================

"""
ArduPilot sends these MAVLink messages to the Raspberry Pi:

┌─────────────────────────────────────────────────────────────────┐
│ HEARTBEAT (MSG_ID=0)                                            │
├─────────────────────────────────────────────────────────────────┤
│ Rate: 1 Hz (every 1 second)                                     │
│ Critical: YES - loss indicates communication failure            │
│                                                                 │
│ Contains:                                                       │
│ - system_status: autopilot health (MAV_STATE)                   │
│ - armed: bit 7 of base_mode                                     │
│ - flight_mode: custom mode                                      │
│ - autopilot: autopilot type                                     │
│                                                                 │
│ Example: Can tell if drone is in AUTO vs LOITER vs RTL          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ SYS_STATUS (MSG_ID=1)                                           │
├─────────────────────────────────────────────────────────────────┤
│ Rate: 1 Hz                                                      │
│ Contains battery and system load info                           │
│                                                                 │
│ Contains:                                                       │
│ - battery_remaining: 0-100% capacity                            │
│ - load: CPU load 0-1000 (divide by 10 for %)                    │
│ - drop_rate_comm: packet loss %                                 │
│ - errors_count1/2/3/4: various error counts                     │
│                                                                 │
│ Updates: mission_controller battery threshold checks            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ BATTERY_STATUS (MSG_ID=147)                                     │
├─────────────────────────────────────────────────────────────────┤
│ Rate: 1 Hz                                                      │
│ Detailed battery info                                           │
│                                                                 │
│ Contains:                                                       │
│ - voltages[]: cell voltages in mV                               │
│ - battery_remaining: 0-100%                                     │
│ - current_battery: current draw in mA                           │
│ - temperature: battery temp (if sensor available)               │
│                                                                 │
│ Updates: voltage monitoring, can detect bad cells               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ GPS_RAW_INT (MSG_ID=24)                                         │
├─────────────────────────────────────────────────────────────────┤
│ Rate: 1 Hz                                                      │
│ GPS position and fix quality                                    │
│                                                                 │
│ Contains:                                                       │
│ - fix_type: 0=none, 1=GPS, 2=DGPS, 3=RTK_FIXED, 4=RTK_FLOAT     │
│ - lat/lon: position in degrees * 10^7                           │
│ - alt: altitude in mm                                           │
│ - eph/epv: horizontal/vertical error estimate                   │
│                                                                 │
│ Updates: drone altitude, GPS lock status                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ LOCAL_POSITION_NED (MSG_ID=33)                                  │
├─────────────────────────────────────────────────────────────────┤
│ Rate: 2+ Hz (can request higher)                                │
│ Position relative to home (NED = North-East-Down)               │
│                                                                 │
│ Contains:                                                       │
│ - x/y: position in meters north/east from home                  │
│ - z: altitude below home (negative = above ground)              │
│ - vx/vy/vz: velocity components                                 │
│                                                                 │
│ Updates: drone position for mission progress tracking           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ ATTITUDE (MSG_ID=30)                                            │
├─────────────────────────────────────────────────────────────────┤
│ Rate: 1+ Hz                                                     │
│ Drone orientation (roll, pitch, yaw angles)                     │
│                                                                 │
│ Contains:                                                       │
│ - roll/pitch/yaw: angles in radians (-π to π)                   │
│ - rollspeed/pitchspeed/yawspeed: angular velocities             │
│                                                                 │
│ Updates: Detect unusual flight attitudes (warning indicator)    │
└─────────────────────────────────────────────────────────────────┘
"""

# ====================================================================
# 5. DATA FLOW FOR MISSION EXAMPLE
# ====================================================================

"""
Example Mission Timeline with Data Flow:

TIME: 0:00 - Flight Controller Connects
════════════════════════════════════════════════════════════════
Flight Controller → [HEARTBEAT, SYS_STATUS]
                 ↓
            MAVLinkHandler processes
                 ↓
        DroneHealth.update_from_heartbeat()
        DroneHealth.update_from_sys_status()
                 ↓
        DroneHealth.armed = False ✓
        DroneHealth.battery_remaining = 100% ✓
                 ↓
        SystemHealth.evaluate() → SystemState.OK
                 ↓
        MissionController: Preflight PASSED ✓


TIME: 2:30 - User Arms Drone and Sets AUTO
════════════════════════════════════════════════════════════════
Flight Controller → [HEARTBEAT with armed=True, AUTO mode]
                 ↓
        DroneHealth.armed = True ✓
        DroneHealth.system_status = IN_FLIGHT ✓
                 ↓
        MissionController._evaluate_state_transitions()
        Condition met: armed=True → start CAPTURING
                 ↓
        CaptureController.apply_profile("CAPTURING")
        CaptureController.start()
                 ↓
        ⚫ Camera turns on, begins capturing


TIME: 5:00 - Flight in Progress
════════════════════════════════════════════════════════════════
Every 100ms (10Hz loop):
  
  1. Flight Controller → [HEARTBEAT, SYS_STATUS, BATTERY_STATUS, etc]
  
  2. MAVLinkHandler routes to handlers
  
  3. DroneHealth updated with latest values:
     - battery_remaining: 95%
     - altitude: 50m
     - armed: True
  
  4. SystemHealth.evaluate():
     - Drone battery 95% → OK
     - Pi temperature 65°C → OK
     - Link quality RSSI -60dBm → OK
     - Result: SystemState.OK
  
  5. CaptureController.update():
     - Check: elapsed time since last capture?
     - Yes: 1.0 seconds elapsed
     - Capture frame → write to disk
     - timestamp: 20240217_123456_123.jpg
  
  6. MissionController.update():
     - Check state transitions
     - No issues → stay in CAPTURING


TIME: 15:00 - Battery Drops Low
════════════════════════════════════════════════════════════════
Flight Controller → [HEARTBEAT, SYS_STATUS]
                 ↓
        DroneHealth.battery_remaining = 35%
                 ↓
        SystemHealth.evaluate():
        battery=35% is in DEGRADED range (25-40%)
        → SystemState.DEGRADED
                 ↓
        MissionController._evaluate_state_transitions():
        if state=CAPTURING and health=DEGRADED:
            → transition to DEGRADED
                 ↓
        MissionController._on_enter(DEGRADED):
        CaptureController.apply_profile("DEGRADED")
        ↓
        Profile change:
        interval: 1.0s → 5.0s
        quality: 90% → 50%
                 ↓
        ⚫ Camera still on but capturing 5x slower


TIME: 20:00 - Battery Recovers (plugged in during RTL?)
════════════════════════════════════════════════════════════════
Flight Controller → [SYS_STATUS]
                 ↓
        DroneHealth.battery_remaining = 85%
                 ↓
        SystemHealth.evaluate():
        battery=85% → OK
        → SystemState.OK
                 ↓
        MissionController._evaluate_state_transitions():
        if state=DEGRADED and health=OK:
            → transition back to CAPTURING
                 ↓
        CaptureController.apply_profile("CAPTURING")
        interval: 5.0s → 1.0s
        quality: 50% → 90%
                 ↓
        ⚫ Resume full rate capture


TIME: 30:00 - Mission Complete
════════════════════════════════════════════════════════════════
Flight Controller → [HEARTBEAT with armed=False]
                 ↓
        DroneHealth.armed = False ✓
                 ↓
        MissionController._evaluate_state_transitions():
        if state=CAPTURING and armed=False:
            → transition to SHUTDOWN
                 ↓
        MissionController._on_enter(SHUTDOWN):
        CaptureController.stop()
        → Camera closes
                 ↓
        running = False
        Loop exits
                 ↓
        MAVLinkHandler.disconnect()
        Logs saved
        Mission complete ✓
"""

# ============================================================================
# 6. THREAD ARCHITECTURE
# ============================================================================

"""
The system uses threads to prevent blocking:

Main Thread (blocking on loop):
├─ Initialize components
├─ Run preflight checks
├─ Start MAVLink listener (launches worker thread)
├─ Main mission loop (repeats 10x per second):
│  ├─ capture_controller.update()
│  ├─ mission_controller.update()
│  ├─ sleep until next iteration
│  └─ repeat
└─ Shutdown


MAVLink Listener Thread (background, daemon):
├─ Runs in while self.running loop
├─ recv_match() blocks waiting for messages
├─ When message arrives:
│  ├─ Store in message_buffer (thread-safe)
│  ├─ Update last_heartbeat timestamp
│  ├─ Call all registered handlers
│  └─ Continue waiting
└─ Stops when self.running = False


Thread Safety:
- Message buffer protected by self._lock (threading.Lock)
- Message handlers called with copies of data
- No race conditions because:
  - MAVLink thread only READS config (no changes)
  - Main thread only READS from message_buffer
  - Health objects updated atomically (single assignment)
"""

print("See MAVLINK_INTEGRATION_GUIDE.md and MISSION_EXAMPLES.py for practical examples")
