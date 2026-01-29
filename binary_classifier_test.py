import numpy as np
import tensorflow as tf
import cv2
import os
import glob

# --- CONFIGURATION ---
MODEL_PATH = 'animal_binary_classifier.tflite'
TEST_IMAGE_DIR = 'test_images'  # Create this folder and put some images in it
IMG_SIZE = (224, 224)
THRESHOLD = 0.5  # Confidence threshold for "Animal"

def load_and_preprocess(image_path):
    # Load image with OpenCV
    img = cv2.imread(image_path)
    if img is None:
        return None, None
    
    # Resize to the model's required input size
    img_resized = cv2.resize(img, IMG_SIZE)
    
    # MobileNetV2 preprocessing: scale pixels from [0, 255] to [-1, 1]
    input_data = img_resized.astype(np.float32)
    input_data = (input_data / 127.5) - 1.0
    
    # Add batch dimension (1, 224, 224, 3)
    input_data = np.expand_dims(input_data, axis=0)
    return input_data, img

def main():
    # 1. Load the TFLite model and allocate tensors
    interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()

    # Get input and output details
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    # 2. Get list of test images
    image_paths = glob.glob(os.path.join(TEST_IMAGE_DIR, "*.*"))
    if not image_paths:
        print(f"No images found in {TEST_IMAGE_DIR}. Please add some images to test!")
        return

    print(f"🚀 Testing {len(image_paths)} images...")

    for path in image_paths:
        input_data, original_img = load_and_preprocess(path)
        if input_data is None: continue

        # 3. Set the input tensor and run inference
        interpreter.set_tensor(input_details[0]['index'], input_data)
        interpreter.invoke()

        # 4. Get the result (Sigmoid output: 0 to 1)
        prediction = interpreter.get_tensor(output_details[0]['index'])[0][0]
        
        # Determine class based on threshold
        label = "Animal" if prediction >= THRESHOLD else "No Animal"
        color = (0, 255, 0) if label == "Animal" else (0, 0, 255)
        
        # 5. Display the result
        display_text = f"{label} ({prediction:.2f})"
        cv2.putText(original_img, display_text, (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        
        print(f"Image: {os.path.basename(path)} | Score: {prediction:.4f} | Label: {label}")
        
        cv2.imshow('TFLite Model Test', original_img)
        if cv2.waitKey(0) & 0xFF == ord('q'): # Press 'q' to move to next or quit
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
