## MAIN LOOP DECISION MAKING FOR RASPI AGENT 

from enum import Enum, auto
from verify_config import SelfCheckPrelaunch
from system_builder import SystemBuilder
from health import SystemHealth, PiHealth, LinkHealth
import time



##### upon each instance ALWAYS self check

checker = SelfCheckPrelaunch('/Raspberry_Pi_Agent/config.yaml')

if not checker.run():
    raise RuntimeError('Prelaunch check failed.')

#### upon each instance, ALWAYS rebuild

mission, capture = SystemBuilder.build()
system_health = SystemHealth()


while True:
    
### TODO: Check if the heartbeat is receiving things, only then do we update everything else. 
### TODO: We need to keep track of time to determine when to start capturing images. 

    system_health.pi.update()
    capture.update()
    mission.update()
    time.sleep(0.05)

