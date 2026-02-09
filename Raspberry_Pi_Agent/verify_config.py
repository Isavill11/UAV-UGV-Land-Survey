### validates whether the hardware is connected and working properly and the software parameters are set correctly.

import yaml
import psutil
import time
import cv2
import os
import platform
from pymavlink import mavutil
try:
    from picamera2 import Picamera2
except ImportError:
    Picamera2 = None
from dataclasses import dataclass
from pathlib import Path




REQUIRED_KEYS = {
    "platform": {
        "name": str,
        "id": str,
        "location": str,
    },
    "camera": {
        "id": str,
        "type": str,
        "dimensions": {
            "width": int,
            "height": int,
        },
        "capture_profiles": {
            "CAPTURING": dict,
            "DEGRADED": dict,
            "CRITICAL": dict,
        },
    },
    "storage": {
        "local_path": str,
    },
    "battery_status": {
        "critical_battery": int,
        "low_battery": int,
    },
}


@dataclass
class PrecheckError: 
    subsystem: str
    message: str
    timestamp: float
    severity: str = "ERROR"
    exception: Exception | None = None
    


class SelfCheckPrelaunch:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = None
        self.ready = False
        self.endpoint = None

    def run(self):
        issues = []

        config_error = self._check_config() ### Done
        if config_error: 
            self.ready = False
            return[config_error]
        schema_errors = self._check_required_keys() ### Done
        if schema_errors: 
            return schema_errors
        

        for check in [
        self._check_camera, ### Done
        self._check_network, ### Done
        self._check_power, ### Done
        self._check_storage, ### Done
        self._check_thermal, ### Done
        ]: 
            error = check()
            if error: 
                issues.append(error)
                
        fatal = [e for e in issues if e.severity == "ERROR"]
        self.ready = len(fatal) == 0


    def _check_config(self) -> PrecheckError | None:
        
        try: 
            with open(self.config_path) as f: 
                self.config = yaml.safe_load(f)
                
            if not isinstance(self.config, dict):
                return PrecheckError(
                    "Config",
                    "Config root must be a YAML dictionary",
                    time.time()
                    )

            return None

        except FileNotFoundError as e:
            return PrecheckError(
                "Config",
                f"Config file not found: {self.config_path}",
                time.time(),
                exception=e
            )

        except yaml.YAMLError as e:
            return PrecheckError(
                "Config",
                "YAML syntax error in config file",
                time.time(),
                exception=e
            )
    

    def _check_camera(self) -> PrecheckError | None:
        os_name = platform.system()
        dims = self.config["camera"]["dimensions"]
        cam_res = (dims["width"], dims["height"])
        
        cam_type = self.config["camera"]["type"]
        
        if cam_type == "None":
            return None

        if os_name == 'Linux': 
            try: 
                picam2 = Picamera2()
                conf = picam2.create_preview_configuration(
                    main={"size": (cam_res), "format": "RGB888"}
                )
                picam2.configure(conf)
                picam2.start()
                frame = picam2.capture_array()
                picam2.stop()
                if frame == None: 
                    return PrecheckError(
                        'Camera', 
                        'Picam2 is not responding.', 
                        time.time())

            except Exception as e: 
                return PrecheckError(
                    'Camera', 
                    'Camera could not be found. Ensure proper connection. Try rebooting.', 
                    time.time())
            finally:
                picam2.stop()


        elif os_name == 'Windows': 
            cam = cv2.VideoCapture(0)
            if not cam.isOpened():
                return PrecheckError(
                    "Camera",
                    "Windows webcam checked instead of Picam2 (index = 0).",
                    time.time()
                )
            cam.release()
            print('Windows webcam checked instead of Picam.')
            
            ## TODO: Camera index, capture profiles to capture controller. default res and dimentions.
            
            return None

    
    def _check_storage(self):
        issue = []
        storage_path = self.config['storage']['local_path']
        MIN_STORAGE_MB_WARN = self.config['storage']['min_storage_mb_warn']
        MIN_STORAGE_MB_FATAL = self.config['storage']['min_storage_mb_fatal']
        
        if not storage_path:
            vehicle = self.config['platform']['name'] + '_' + str(self.config['platform']['id'])
            home_dir = os.path.expanduser('~')
            path = os.path.join(home_dir, f'{vehicle}_Mission')
            
            issue.append(PrecheckError(
                'Storage', 
                f"The local storage path {storage_path} didnt exist. Creating new one, {path}", 
                time.time(), 
                "WARNING"
                )
            )

            os.mkdir(path)
        else:
            path = Path(storage_path)

            if not path.exists() or not path.is_dir():
                return PrecheckError(
                    'Storage', 
                    f'the path "{path}" did not exist, ',
                    time.time(),
                    severity="ERROR"
                )
                    
        usage = psutil.disk_usage(path)
        amount_available_mb = usage.free // (1024 * 1024)
                
        ### we need at least 500MB to run 
        if amount_available_mb < MIN_STORAGE_MB_FATAL: 
            return PrecheckError(
                "Storage", 
                "Less than 500MB is insufficient to start a mission", 
                time.time(), 
                severity="ERROR",
            )
        if amount_available_mb < MIN_STORAGE_MB_WARN:
            return PrecheckError(
                "Storage", 
                f'Low storage warning: {amount_available_mb} MB free',
                time.time(), 
                severity="WARNING",
            )
            
        ## TODO: Put storage paths in capture controller and mission planner. 
        
        return None

        
    def _check_network(self):
        comms = self.config['communication']
        try:
            endpoint = f"{comms['protocol']}:{comms['ground_station_ip']}:{comms['ground_station_port']}"
        except KeyError as e: 
            return PrecheckError(
                'Network', 
                'Failed to recieve heartbeat from MAVLink', 
                time.time(), 
                exception=e
            )
        self.endpoint = endpoint
        
        try:
            master = mavutil.mavlink_connection(endpoint)
        except Exception as e: 
            return PrecheckError(
                'Network', 
                'Failed to create MAVLink connection', 
                time.time(),
                exception=e
            )
        try:
            hb = master.wait_heartbeat(timeout=15)
            if hb is None:
                return PrecheckError(
                    "Network",
                    "Timed out waiting for MAVLink heartbeat",
                    time.time()
                )
        finally:
            master.close()

        ### TODO: put network endpoints in DroneHealth in health.py to recieve and send mavlink packages.
        return None
    
    def _check_thermal(self):
        thermal_configs = self.config['thermal_management']       
        if not thermal_configs: 
            return PrecheckError(
                "Thermal", 
                'Thermal Configurations not found', 
                time.time(), 
                
            )
        
        read_interval = thermal_configs['read_interval_sec'] ###############
        temp = "/sys/class/thermal/thermal_zone0/temp"
    
        if os.path.exists(temp):
            with open(temp, "r") as f:
                temp_str = f.read().strip()
                temp_celsius = int(temp_str) / 1000.0
        else:
            return PrecheckError(
                'Thermal', 
                'Cant open raspis thermal temperature',
                time.time(), 
                severity='WARNING' 
            )
            
        
        thresholds = thermal_configs['thresholds_c']
        if not all(k in thresholds for k in ('cool', 'warm', 'hot')):
            return PrecheckError(
                'Thermal', 
                'There are no temperature thresholds to verify', 
                time.time()
            )
            
        warm, hot = thresholds['warm'], thresholds['hot']
        
        if warm < hot: 
            if temp_celsius < warm: 
                return None
            elif temp_celsius < hot: 
                return PrecheckError(
                    'Thermal',
                    f'The RasPi is {temp_celsius}°C, which is warm. consider cooling it.', 
                    time.time(),
                    'WARNING'
                )
            else: 
                return PrecheckError(
                    'Thermal', 
                    f'The RasPi CPU temperature, {temp_celsius}°C, is too hot to start the mission.', 
                    time.time(), 
                    "ERROR"
                )
        else: 
            return PrecheckError(
                'Thermal', 
                'The temperature thresholds are illogical', 
                time.time(),
                'ERROR'
            )
            
        ### TODO: read interval goes into health PiHealth for temp. and thresholds
        
    
    def _check_power(self):
        if not self.endpoint:
            return PrecheckError(
                'Power',
                'MAVLink endpoint not set; cannot check battery.',
                time.time()
        )

        try:
            master = mavutil.mavlink_connection(self.endpoint)
        except Exception as e:
            return PrecheckError(
                'Power',
                'Failed to create MAVLink connection for power check.',
                time.time(),
                exception=e
            )

        try:
            # wait for first heartbeat
            hb = master.wait_heartbeat(timeout=15)
            if hb is None:
                return PrecheckError(
                    "Power",
                    "Timed out waiting for MAVLink heartbeat",
                    time.time()
                )

            # try to get a battery message, timeout after a few seconds
            start = time.time()
            while time.time() - start < 5:  # max 5 seconds to get battery info
                msg = master.recv_match(type=['SYS_STATUS', 'BATTERY_STATUS'], blocking=True)
                if not msg:
                    continue

                if msg.get_type() == 'SYS_STATUS':
                    battery_pct = msg.battery_remaining
                    battery_voltage = msg.voltage_battery / 1000  # convert mV → V
                    battery_temp_c = getattr(msg, "temperature", None)
                    if battery_temp_c is not None:
                        battery_temp_c /= 100  # centi-degrees → °C
                    break
            else:
                return PrecheckError(
                    "Power",
                    "Could not get battery status from MAVLink.",
                    time.time()
                )

            # check against config thresholds
            battery_cfg = self.config.get('battery_status', {})
            low_thresh = battery_cfg.get('low_battery', 20)
            crit_thresh = battery_cfg.get('critical_battery', 10)
            
            ### TODO: battery config, low thresh, and crit thresh go into health controller.
            if battery_pct is None or battery_pct < 0:
                return PrecheckError(
                    'Power',
                    'Battery percentage unknown from autopilot.',
                    time.time(),
                    severity='WARNING'
                )
            elif battery_pct <= crit_thresh:
                return PrecheckError(
                    'Power',
                    f'Critical battery: {battery_pct}% remaining.',
                    time.time(),
                    severity='ERROR'
                )
            elif battery_pct <= low_thresh:
                return PrecheckError(
                    'Power',
                    f'Low battery: {battery_pct}% remaining.',
                    time.time(),
                    severity='WARNING'
                )

        finally:
            master.close()

        return None
    



    def _validate_keys(self, schema, config_section, path=""):
        errors = []

        for key, expected in schema.items():
            full_path = f"{path}.{key}" if path else key

            if key not in config_section:
                errors.append(
                    PrecheckError(
                        "Config",
                        f"Missing required key: {full_path}",
                        time.time()
                    )
                )
                continue

            value = config_section[key]

            if isinstance(expected, dict):
                if not isinstance(value, dict):
                    errors.append(
                        PrecheckError(
                            "Config",
                            f"Expected {full_path} to be a dictionary",
                            time.time()
                        )
                    )
                else:
                    errors.extend(
                        self._validate_keys(expected, value, full_path)
                    )
            else:
                if not isinstance(value, expected):
                    errors.append(
                        PrecheckError(
                            "Config",
                            f"{full_path} must be of type {expected.__name__}",
                            time.time()
                        )
                    )
                try:
                    value.strip == ''
                except Exception as e: 
                    errors.append(PrecheckError('Config', 
                                                'no idea what kind of file this is', 
                                                time.time(), 
                                                e))
                    if expected == str:
                        errors.append(
                            PrecheckError(
                                "Config",
                                f"{full_path} cannot be empty",
                                time.time()
                            )
                        )
                
        return errors



    def _check_required_keys(self) -> PrecheckError | None:
        errors = self._validate_keys(REQUIRED_KEYS, self.config)

        if errors:
            return errors[0]

        return None




