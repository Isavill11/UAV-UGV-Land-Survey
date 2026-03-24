try:
    from picamera2 import Picamera2
except ImportError:
    Picamera2 = None

import yaml

with open('config.yaml', 'w') as f: 
    config = yaml.safe_load(f)
    



dims = config["camera"]["dimensions"]
cam_res = (dims["width"], dims["height"])
capture_profiles = config['camera']['capture_profiles']
cam_type = config["camera"]["type"]

print(f'Dimentions: {dims}, \nCamera Resolution: {cam_res}, \nCapture Profiles: {capture_profiles},\nCamera Type: {cam_type}')


if cam_type == "None":
    print("no camera")

picam2 = Picamera2()
conf = picam2.create_preview_configuration(
    main={"size": (cam_res), "format": "RGB888"}
)
picam2.configure(conf)
picam2.start()
frame = picam2.capture_array()
