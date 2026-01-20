import cv2
import numpy as np
import time
import os
from picamera2 import Picamera2
try:
    # Try the lightweight runtime first
    import tflite_runtime.interpreter as tflite
except ImportError:
    # Fallback to full tensorflow if runtime isn't installed
    import tensorflow.lite as tflite

# --- CONFIGURATION ---
MODEL_PATH = "animal_classifier.tflite"
SAVE_FOLDER = "detected_images"
THRESHOLD = 0.70  # Only save if the "Yes" confidence is above 70%
IMG_SIZE = (160, 160) # Must match the size used in training

# Create save folder if it doesn't exist
if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER)

def main():
    # 1. Initialize TFLite Interpreter
    interpreter = tflite.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    # 2. Initialize Camera
    picam2 = Picamera2()
    # We grab 640x480 for the preview, but we'll resize for the AI
    config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"})
    picam2.configure(config)
    picam2.start()

    print(f"--- Spotter Started. Saving 'Yes' hits to {SAVE_FOLDER} ---")

    try:
        while True:
            # A. Capture frame from camera
            frame = picam2.capture_array()
            
            # B. Preprocess for the Model
            # Resize to (160, 160) and add a batch dimension
            small_frame = cv2.resize(frame, IMG_SIZE)
            input_data = np.expand_dims(small_frame, axis=0).astype(np.float32)
            
            # Normalize pixels to [-1, 1] (Standard for MobileNetV2)
            input_data = (input_data / 127.5) - 1.0

            # C. Run Inference
            interpreter.set_tensor(input_details[0]['index'], input_data)
            interpreter.invoke()
            prediction = interpreter.get_tensor(output_details[0]['index'])[0][0]

            # D. The Decision Logic
            # If prediction > 0.5, it's the "Yes" class (usually index 1)
            # We use a higher threshold (0.7) to avoid false positives
            if prediction > THRESHOLD:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                filename = f"{SAVE_FOLDER}/hit_{timestamp}_{prediction:.2f}.jpg"
                
                # Save the high-res version of the frame
                # Convert RGB to BGR for OpenCV saving
                cv2.imwrite(filename, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                print(f"📸 Detected! Confidence: {prediction:.2f} | Saved to {filename}")

            # E. Local Preview (Optional)
            # Show the live feed with the current confidence score
            display_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            cv2.putText(display_frame, f"Conf: {prediction:.2f}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("Drone Spotter Feed", display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        picam2.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()