import torch
import cv2
import albumentations as A
from albumentations.pytorch import ToTensorV2
import segmentation_models_pytorch as smp
import numpy as np

# --- CONFIGURATION ---
MODEL_PATH = 'best_roboflow_crop_model.pth'
TEST_IMAGE_PATH = 'test_field.jpg'
ENCODER = "resnet34"
NUM_CLASSES = 2  # 0: background, 1: crop
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# ---------------------

def main():
    # 1. Load the trained model
    print("Loading model...")
    model = smp.Unet(
        encoder_name=ENCODER,
        encoder_weights=None, # We are loading our own weights, so we don't need pre-trained ones
        in_channels=3,
        classes=NUM_CLASSES,
    )
    model.load_state_dict(torch.load(MODEL_PATH, map_location=torch.device(DEVICE)))
    model.to(DEVICE)
    model.eval() # Set the model to evaluation mode

    # 2. Load and preprocess the test image
    print("Loading and preprocessing test image...")
    original_image = cv2.cvtColor(cv2.imread(TEST_IMAGE_PATH), cv2.COLOR_BGR2RGB)

    # Apply the same transformations used during training
    transform = A.Compose([
        A.Resize(height=512, width=512),
        A.Normalize(mean=(0.0, 0.0, 0.0), std=(1.0, 1.0, 1.0)),
        ToTensorV2(),
    ])

    processed_image = transform(image=original_image)['image']
    # Add a "batch" dimension for the model
    input_tensor = processed_image.unsqueeze(0).to(DEVICE)

    # 3. Get the model's prediction
    print("Running inference...")
    with torch.no_grad():
        prediction = model(input_tensor)

    # The output is raw scores (logits), so we find the class with the highest score for each pixel
    predicted_mask = torch.argmax(prediction.squeeze(), dim=0).cpu().numpy()

    # 4. Visualize the result
    print("Visualizing results...")
    # Define colors for our classes (0: background, 1: crop)
    # We'll make the background black (transparent) and the crop green
    color_map = {0: (0, 0, 0), 1: (0, 255, 0)}

    # Create an RGB image from the mask
    height, width = predicted_mask.shape
    mask_rgb = np.zeros((height, width, 3), dtype=np.uint8)
    for class_id, color in color_map.items():
        mask_rgb[predicted_mask == class_id] = color

    # Resize the mask and original image to be the same size for overlay
    # We'll resize the mask to match the original image's dimensions
    original_h, original_w, _ = original_image.shape
    mask_resized = cv2.resize(mask_rgb, (original_w, original_h))

    # Overlay the mask on the original image with transparency
    overlayed_image = cv2.addWeighted(original_image, 1, mask_resized, 0.5, 0)

    # Display the result in a pop-up window
    cv2.imshow('Model Prediction', cv2.cvtColor(overlayed_image, cv2.COLOR_RGB2BGR))
    cv2.waitKey(0) # Wait for a key press to close the window
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
