from ultralytics import YOLO
from pathlib import Path

# 1. Load your custom-trained model
# The path will be in the 'runs/detect/train/' folder. If you have multiple train folders,
# use the latest one (e.g., train2, train3, etc.).
model_path = Path('runs/detect/train/weights/best.pt')
model = YOLO(model_path)

# 2. Define the path to your test image
image_to_test = Path('test_cow.jpg') # Or whatever you named your test image

# 3. Run inference on the image
results = model.predict(source=image_to_test)

# 4. Display the results
# The 'results' object contains all the detections. We can display the first one.
print("Displaying detection results...")
results[0].show() # This will open a window with the image and bounding boxes

# (Optional) Save the results to a file
# results[0].save(filename='result.jpg')
print("Inference complete. Check the pop-up window for results.")