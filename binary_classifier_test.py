import numpy as np
import tensorflow as tf
import cv2
import os
import glob

# --- CONFIGURATION ---
MODEL_PATH = 'survey_animal_classifier.tflite'
TEST_IMAGE_DIR = 'test_images' 
IMG_SIZE = (224, 224)

# THRESHOLD LOGIC:
# 1.0 = Certain Yes Animal | 0.0 = Certain No Animal
# We set this to 0.35 to ensure the drone doesn't miss any targets for the rover.
THRESHOLD = 0.35 

def load_and_preprocess(image_path):
    # Load image with OpenCV
    img = cv2.imread(image_path)
    if img is None:
        return None, None
    
    # Resize to the model's required input size
    img_resized = cv2.resize(img, IMG_SIZE)
    
    # CRITICAL: MobileNetV2 preprocessing (scale pixels to [-1, 1])
    # This MUST match the training script exactly.
    input_data = img_resized.astype(np.float32)
    input_data = (input_data / 127.5) - 1.0
    
    # Add batch dimension (1, 224, 224, 3)
    input_data = np.expand_dims(input_data, axis=0)
    return input_data, img

def main():
    # 1. Load the TFLite model and allocate tensors
    if not os.path.exists(MODEL_PATH):
        print(f"Error: {MODEL_PATH} not found. Run training first!")
        return

    interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()

    # Get input and output details
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    # 2. Get list of test images
    image_paths = glob.glob(os.path.join(TEST_IMAGE_DIR, "*.*"))
    if not image_paths:
        print(f"No images found in {TEST_IMAGE_DIR}. Add some drone crops to test!")
        return

    print(f"🛰️  Starting UAV/UGV Survey Test...")
    print(f"Sensitivity Threshold: {THRESHOLD} (Higher score = More likely Animal)")

    for path in image_paths:
        input_data, original_img = load_and_preprocess(path)
        if input_data is None: continue

        # 3. Run inference
        interpreter.set_tensor(input_details[0]['index'], input_data)
        interpreter.invoke()

        # 4. Get the result (Sigmoid output: 0 to 1)
        # Score near 1.0 = Animal | Score near 0.0 = Grass/Dirt
        prediction = interpreter.get_tensor(output_details[0]['index'])[0][0]
        
        # Determine status
        if prediction >= THRESHOLD:
            label = f"ANIMAL DETECTED ({prediction:.2f})"
            color = (0, 255, 0) # Green for detection
            status_msg = "✅ TARGET FOUND"
        else:
            label = f"NO ANIMAL ({prediction:.2f})"
            color = (0, 0, 255) # Red for clear
            status_msg = "❌ CLEAR FIELD"
        
        # 5. Visual Output
        cv2.putText(original_img, label, (10, 35), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        print(f"Image: {os.path.basename(path):<20} | Score: {prediction:.4f} | {status_msg}")
        
        cv2.imshow('Survey Model Test', original_img)
        # Press 'q' to quit, any other key for next image
        if cv2.waitKey(0) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
