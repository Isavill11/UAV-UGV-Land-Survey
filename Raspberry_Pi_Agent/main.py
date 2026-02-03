## MAIN LOOP DECISION MAKING FOR RASPI AGENT 
import logging
from enum import Enum, auto
from verify_config import SelfCheckPrelaunch
from system_builder import SystemBuilder
from health import SystemHealth, PiHealth, LinkHealth
import time

logging.basicConfig(
    level=logging.INFO,  # or DEBUG
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)



##### upon each instance ALWAYS self check
checker = SelfCheckPrelaunch('/Raspberry_Pi_Agent/config.yaml')

issues = checker.run()

if checker.ready: 
    cfg = checker.config
else: 
    logger.error("❌ Preflight checks failed")

    for issue in issues:
        logger.error(
            "[%s] %s",
            issue.subsystem,
            issue.message
        )
    raise SystemExit(1)


############# self check complete, continue!!!


mission, capture = SystemBuilder.build()
system_health = SystemHealth()
mission_running = True


while mission_running:
    
### TODO: Check if the heartbeat is receiving things, only then do we update everything else. 
### TODO: We need to keep track of time to determine when to start capturing images. 

    system_health.pi.update()
    capture.update()
    mission.update()
    time.sleep(0.05)



    #update health inputs
    system_health.drone.battery_remaining = fc.get_battery_percent()
    drone_health.last_update = time.time()

    # evaluate
    bat_state = drone_health.battery_state(cfg)

    if bat_state == BatteryState.CRITICAL:
        self.abort_mission()

    elif bat_state == BatteryState.LOW:
        self.enter_degraded_mode()

    time.sleep(0.5)
