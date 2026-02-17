"""
Quick Start Example - Running an Autonomous Mission

This example shows how to quickly set up and run an autonomous drone mission
with MAVLink integration on a Raspberry Pi.
"""

# ============================================================================
# OPTION 1: Simple - Run mission with default config
# ============================================================================

if __name__ == "__main__":
    from Raspberry_Pi_Agent.notmain import main
    main()


# ============================================================================
# OPTION 2: Advanced - Custom setup with tweaks
# ============================================================================

from Raspberry_Pi_Agent.notmain import AutonomousMission
import logging

# Setup logging to see what's happening
logging.basicConfig(
    level=logging.DEBUG,  # Change to INFO for less verbose output
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_custom_mission():
    """Run mission with custom configuration"""
    
    # Initialize mission controller
    config_path = r'C:\Users\isav3\VSCode Projects\UAV-UGV-Land-Survey\Raspberry_Pi_Agent\config.yaml'
    mission = AutonomousMission(config_path)
    
    # Optional: Override config settings before running
    # mission.config["platform"]["startup_delay_sec"] = 5
    # mission.config["camera"]["id"] = 1  # Use different camera
    
    # Run the mission
    # This will:
    # 1. Connect to flight controller via MAVLink
    # 2. Run preflight checks
    # 3. Wait for drone to be armed in AUTO mode
    # 4. Monitor and capture images until mission complete
    success = mission.run()
    
    return 0 if success else 1


# ============================================================================
# OPTION 3: Manual Control - Step-by-step mission management
# ============================================================================

from Raspberry_Pi_Agent.mavlink_handler import MAVLinkHandler
from Raspberry_Pi_Agent.Mission_Controller.mission_controller import MissionController
from Raspberry_Pi_Agent.Mission_Controller.capture_controller import CaptureController
from Raspberry_Pi_Agent.Mission_Controller.health import SystemHealth, DroneHealth, PiHealth, LinkHealth
import time

def run_manual_mission():
    """Run mission with step-by-step control"""
    
    # Load config
    from Raspberry_Pi_Agent.verify_config import SelfCheckPrelaunch
    config_path = r'C:\Users\isav3\VSCode Projects\UAV-UGV-Land-Survey\Raspberry_Pi_Agent\config.yaml'
    check = SelfCheckPrelaunch(config_path)
    check.run()
    config = check.config
    
    # Initialize components
    system_health = SystemHealth(
        drone=DroneHealth(),
        pi=PiHealth(),
        radio=LinkHealth()
    )
    capture_controller = CaptureController(config)
    mission_controller = MissionController(config, system_health, capture_controller)
    
    # Setup MAVLink connection
    mavlink_cfg = config.get("mavlink", {})
    mavlink = MAVLinkHandler(
        mavlink_cfg.get("connection_string", "/dev/ttyS0"),
        mavlink_cfg.get("baud", 115200)
    )
    
    # --- Step 1: Connect ---
    print("Step 1: Connecting to flight controller...")
    if not mavlink.connect():
        print("ERROR: Failed to connect!")
        return 1
    
    # --- Step 2: Setup message handlers ---
    print("Step 2: Setting up MAVLink handlers...")
    
    def on_heartbeat(msg):
        system_health.drone.update_from_heartbeat(msg)
        print(f"  Heartbeat - Armed: {system_health.drone.armed}")
    
    def on_battery(msg):
        system_health.drone.update_from_battery_status(msg)
        print(f"  Battery: {system_health.drone.battery_remaining}% ({system_health.drone.battery_voltage:.1f}V)")
    
    mavlink.register_handler("HEARTBEAT", on_heartbeat)
    mavlink.register_handler("BATTERY_STATUS", on_battery)
    
    # --- Step 3: Start listening ---
    print("Step 3: Starting message listener...")
    mavlink.start_listening()
    time.sleep(1)
    
    # --- Step 4: Run preflight checks ---
    print("Step 4: Running preflight checks...")
    if not mission_controller.preflight_check():
        print("ERROR: Preflight checks failed!")
        mavlink.disconnect()
        return 1
    
    # --- Step 5: Wait for mission start ---
    print("Step 5: Waiting for mission start...")
    print("  - Arm the drone")
    print("  - Switch to AUTO mode")
    print("  - Waiting for heartbeat for next 30 seconds...")
    
    start_time = time.time()
    while time.time() - start_time < 30:
        state, issues = system_health.evaluate(config)
        
        if system_health.drone.armed:
            print("  ✓ Drone armed - mission can start!")
            break
        
        time.sleep(1)
    
    if not system_health.drone.armed:
        print("  Timeout: Drone not armed. Aborting.")
        mavlink.disconnect()
        return 1
    
    # --- Step 6: Start mission ---
    print("Step 6: Starting mission!")
    mission_controller.request_start()
    mission_controller.wait_for_start()
    
    # --- Step 7: Main mission loop ---
    print("Step 7: Mission running - capture until disarm...")
    loop_rate = config["platform"]["loop_rate_hz"]
    loop_interval = 1.0 / loop_rate
    
    mission_time = time.time()
    max_mission_time = 600  # 10 minutes
    
    while (time.time() - mission_time) < max_mission_time:
        # Check if heartbeat is alive
        if not mavlink.is_heartbeat_alive(timeout=2.0):
            print("ERROR: Heartbeat lost!")
            break
        
        # Check if drone is still armed
        if not system_health.drone.armed:
            print("Drone disarmed - mission complete!")
            break
        
        # Update mission and capture
        mission_controller.update()
        capture_controller.update()
        
        # Throttle loop
        time.sleep(loop_interval)
    
    # --- Step 8: Cleanup ---
    print("Step 8: Cleaning up...")
    capture_controller.stop()
    mavlink.stop_listening()
    mavlink.disconnect()
    
    return 0


# ============================================================================
# OPTION 4: Just Connect and Listen
# ============================================================================

def connect_and_listen_example():
    """Connect to drone and listen to messages for 30 seconds"""
    
    from Raspberry_Pi_Agent.mavlink_handler import MAVLinkHandler
    import time
    
    # Connect
    mavlink = MAVLinkHandler("/dev/ttyS0", 115200)
    
    if not mavlink.connect():
        print("Failed to connect")
        return
    
    # Setup simple handler
    def on_heartbeat(msg):
        print(f"Heartbeat! System: {msg.get_srcSystem()}, Status: {msg.system_status}")
    
    mavlink.register_handler("HEARTBEAT", on_heartbeat)
    
    # Listen
    print("Listening for 30 seconds...")
    mavlink.start_listening()
    
    for i in range(30):
        print(f"  {i+1}s...", end=' ', flush=True)
        time.sleep(1)
    
    print("\nDone!")
    mavlink.stop_listening()
    mavlink.disconnect()


# ============================================================================
# RUN ONE OF THE OPTIONS
# ============================================================================

if __name__ == "__main__":
    # Uncomment the one you want to run:
    
    # run_custom_mission()
    # run_manual_mission()
    # connect_and_listen_example()
    pass
