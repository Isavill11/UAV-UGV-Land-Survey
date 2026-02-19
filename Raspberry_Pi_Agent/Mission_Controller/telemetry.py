from pymavlink import mavutil
import time


class Telemetry:

    def __init__(self, connection_string, drone_health, link_health):
        self.connection_string = connection_string
        self.drone = drone_health
        self.link = link_health

        self.master = None

    def connect(self):
        print("Connecting to MAVLink...")
        self.master = mavutil.mavlink_connection(self.connection_string)
        self.master.wait_heartbeat()
        print("Heartbeat received.")

    def update(self):

        msg = self.master.recv_match(blocking=False)

        if not msg:
            return

        msg_type = msg.get_type()

        # ============================
        # DRONE HEALTH
        # ============================

        if msg_type == "HEARTBEAT":
            self.drone.armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
            self.drone.flight_mode = mavutil.mode_string_v10(msg)
            self.drone.last_update = time.time()

        elif msg_type == "SYS_STATUS":
            self.drone.battery_remaining = msg.battery_remaining
            self.drone.last_update = time.time()

        elif msg_type == "BATTERY_STATUS":
            if msg.voltages:
                self.drone.battery_voltage = msg.voltages[0] / 1000.0

        elif msg_type == "GLOBAL_POSITION_INT":
            self.drone.altitude = msg.relative_alt / 1000.0

        elif msg_type == "GPS_RAW_INT":
            self.drone.gps_lock = msg.fix_type >= 3

        # ============================
        # LINK HEALTH
        # ============================

        elif msg_type == "RADIO_STATUS":
            self.link.rssi = msg.rssi
            self.link.remrssi = msg.remrssi
            self.link.rxerrors = msg.rxerrors
            self.link.fixed = msg.fixed
            self.link.last_update = time.time()
