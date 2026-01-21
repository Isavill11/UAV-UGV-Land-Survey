### takes the image from the camera and saves it to a file with metadata
import cv2
import yaml
from picamera2 import Picamera2, Preview
import time
from datetime import datetime
import os


camera = cv2.VideoCapture(0)
if not camera.isOpened():
    raise RuntimeError("Could not open camera.")


def file_location():
    ##### code here
    save_directory = "captured_images"
    return save_directory

def picam2_setup():
    picam2 = Picamera2()
    
    config = picam2.create_preview_configuration(
        main={"size": (IMAGE_WIDTH, IMAGE_HEIGHT), "format": "RGB888"}
    )
    picam2.configure(config)
    picam2.start()
    print("Picamera2 started")




def capture_image(save_directory):
    # if not os.path.exists(save_directory):
    #     os.makedirs(save_directory)

    ret, frame = camera.read()
    if not ret:
        print("Failed to capture image")
        return None

    image = cv2.resize(frame, (640, 480))
    cv2.imshow("Captured Image", image)
    cv2.waitKey(1)   
    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # filename = f"image_{timestamp}.jpg"
    # filepath = os.path.join(save_directory, filename)

    # cv2.imwrite(filepath, frame)
    # print(f"Image saved to {filepath}")
    # return filepath