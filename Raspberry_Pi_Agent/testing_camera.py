try:
    from picamera2 import Picamera2
except ImportError:
    Picamera2 = None

import os
import yaml
from pathlib import Path
import threading
import time

def start_stream_server(picam2, host='0.0.0.0', port=5000):
    from flask import Flask, Response
    import cv2

    app = Flask(__name__)

    def generate_frames():
        while True:
            frame = picam2.capture_array()
            bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            _, jpeg = cv2.imencode('.jpg', bgr, [cv2.IMWRITE_JPEG_QUALITY, 70])
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

    @app.route('/stream')
    def stream():
        return Response(generate_frames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    

    @app.route('/')
    def index():
        return '<img src="/stream" width="640" height="480">'
    
    print("Registered routes:", [str(rule) for rule in app.url_map.iter_rules()])
    
    # daemon=True so it dies when the main agent exits
    t = threading.Thread(target=lambda: app.run(host=host, port=port, threaded=True, use_reloader=False), daemon=True)
    t.start()
    print(f"[Stream] Live at http://{host}:{port}/stream")
    
    

if __name__ == "__main__":
    cwd = os.getcwd()
    config_path = Path(os.path.join(cwd, 'Raspberry_Pi_Agent', 'config.yaml'))


    with config_path.open('r') as f:
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
	
    start_stream_server(picam2)
    print("main server starting up")
    try: 
        while True: 
            time.sleep(1)
    except KeyboardInterrupt: 
        print("\n[Stream] Shutting down...")
        picam2.stop()
