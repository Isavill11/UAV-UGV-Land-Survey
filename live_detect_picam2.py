import cv2
from picamera2 import Picamera2 # The new library
from ultralytics import YOLO
import time

# --- CONFIGURATION ---
model_path = 'best.pt' # Your trained YOLO model
IMAGE_WIDTH = 640  # Request a 640x480 frame from the camera
IMAGE_HEIGHT = 480
MODEL_IMG_SIZE = 320 # But run inference at 320 for speed
CONFIDENCE_THRESHOLD = 0.40
# ---------------------

def main():
    # 1. Initialize the Picamera2
    picam2 = Picamera2()
    
    # Create a camera configuration
    # We request a low-res, fast-streaming format
    config = picam2.create_preview_configuration(
        main={"size": (IMAGE_WIDTH, IMAGE_HEIGHT), "format": "RGB888"}
    )
    picam2.configure(config)

    # Start the camera
    picam2.start()
    print("--- Picamera2 started. Loading YOLO model... ---")

    # 2. Load the YOLO model
    try:
        model = YOLO(model_path)
    except Exception as e:
        print(f"Error loading model: {e}")
        picam2.stop()
        return

    print("--- Model loaded. Starting live detection. Press 'q' to quit. ---")
    
    # Loop for performance tracking
    frame_count = 0
    start_time = time.time()

    while True:
        # 3. Capture a frame
        # This is the new, fast way to get a frame
        frame_rgb = picam2.capture_array()

        # 4. Run inference on the frame
        # We pass the RGB frame directly to the model
        results = model.predict(frame_rgb, imgsz=MODEL_IMG_SIZE, conf=CONFIDENCE_THRESHOLD, verbose=False)

        # 5. Process the results and draw boxes
        # results[0].plot() is a super-fast way to draw all boxes and labels
        # It annotates the frame_rgb numpy array in place
        annotated_frame = results[0].plot()

        # 6. Display the frame
        # We must convert from RGB (YOLO/picam2) to BGR (OpenCV) for display
        cv2.imshow('Live YOLOv8 Detection', cv2.cvtColor(annotated_frame, cv2.COLOR_RGB2BGR))

        # Performance calculation
        frame_count += 1
        elapsed_time = time.time() - start_time
        if elapsed_time > 1.0:
            fps = frame_count / elapsed_time
            print(f"FPS: {fps:.2f}")
            frame_count = 0
            start_time = time.time()

        # Check for 'q' key press to exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Clean up
    cv2.destroyAllWindows()
    picam2.stop()
    print("--- Stopped live detection. ---")

if __name__ == '__main__':
    main()
