###### LISTEN FOR MAVLINK MESSAGES

from pymavlink import mavutil
from health import DroneHealth, LinkHealth
import time

# Listen for MAVLink messages on UDP


def mavlink_listener(drone_health: DroneHealth, link_health: LinkHealth): 
    
    master = mavutil.mavlink_connection('udp:0.0.0.0:14550')

    print('waiting for heartbeat...')

    master.wait_heartbeat(timeout=15)

    print('heartbeat received!')

    while True: 
        msg = master.recv_match(blocking=True)
        if not msg: 
            continue
        

        msg_type = msg.get_type()

        if msg_type == 'SYS_STATUS': 
            drone_health.battery_remaining = msg.battery_remaining
            drone_health.battery_voltage = msg.voltage_battery / 1000
            drone_health.last_update = time.time()

        elif msg_type == 'HEARTBEAT': 
            drone_health.armed = msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
            drone_health.last_update = time.time()

        elif msg.get_type() == "RADIO_STATUS":
            link_health.rssi = msg.rssi
            link_health.remrssi = msg.remrssi
            link_health.rxerrors = msg.rxerrors
            link_health.fixed = msg.fixed
            link_health.last_update = time.time()







