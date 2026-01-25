## MAIN LOOP DECISION MAKING FOR RASPI AGENT 

from enum import Enum, auto
from verify_config import SelfCheckPrelaunch
from system_builder import SystemBuilder
import time



##### upon each instance ALWAYS self check

checker = SelfCheckPrelaunch('/Raspberry_Pi_Agent/config.yaml')

if not checker.run():
    raise RuntimeError('Prelaunch check failed.')

#### upon each instance, ALWAYS rebuild

mission, capture = SystemBuilder.build()




while True:
    mission.update()
    capture.update()
    time.sleep(0.05)

while True: 
    controller.update()
    capture.update()
    time.sleep(0.05) #### how do i dynamically change the intervals depending on the mission state? 
