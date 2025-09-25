import torch
from ultralytics import YOLO

def main():
    # Load a pre-trained YOLOv8 model
    model = YOLO('yolov8n.pt')

    # Set device to MPS for Apple Silicon GPU
    device = 'mps' if torch.backends.mps.is_available() else 'cpu'
    print(f"Using device: {device}")

    # Start training
    results = model.train(
        data='cattle_config.yaml', # <-- This now points to your new config file
        epochs=100,
        imgsz=640,
        device=device,
        batch=16
    )
    print("Training finished!")

if __name__ == '__main__':
    main()