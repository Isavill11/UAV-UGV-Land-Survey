import torch
import albumentations as A
from albumentations.pytorch import ToTensorV2
from torch.utils.data import DataLoader
import segmentation_models_pytorch as smp
from dataset import CropWeedDataset # Import our new dataset class

# --- CONFIGURATION ---
DATA_DIR = "./unet_dataset" # Points to the folder from Step 1
ENCODER = "resnet34"
PRETRAINED_WEIGHTS = "imagenet"
NUM_CLASSES = 3   # 0: background, 1: crop, 2: weed
BATCH_SIZE = 4    
EPOCHS = 25
LEARNING_RATE = 0.001
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# ---------------------

def main():
    transform = A.Compose([
        A.Resize(height=512, width=512),
        A.Normalize(mean=(0.0, 0.0, 0.0), std=(1.0, 1.0, 1.0)),
        ToTensorV2(),
    ])

    print("Loading and preparing datasets...")
    full_dataset = CropWeedDataset(data_dir=DATA_DIR, transform=transform)
    train_size = int(0.8 * len(full_dataset))
    valid_size = len(full_dataset) - train_size
    train_dataset, valid_dataset = torch.utils.data.random_split(full_dataset, [train_size, valid_size])

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    valid_loader = DataLoader(valid_dataset, batch_size=BATCH_SIZE, shuffle=False)

    print("Initializing U-Net model...")
    model = smp.Unet(
        encoder_name=ENCODER,
        encoder_weights=PRETRAINED_WEIGHTS,
        in_channels=3,
        classes=NUM_CLASSES,
    ).to(DEVICE)

    loss_fn = smp.losses.DiceLoss(mode='multiclass')
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

    print(f"--- Starting training on {DEVICE} for {EPOCHS} epochs ---")
    best_val_loss = float('inf')
    for epoch in range(EPOCHS):
        model.train()
        train_loss = 0.0
        for images, masks in train_loader:
            images = images.float().to(DEVICE)
            masks = masks.long().to(DEVICE)
            predictions = model(images)
            loss = loss_fn(predictions, masks)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        avg_train_loss = train_loss / len(train_loader)
        print(f"Epoch {epoch+1}/{EPOCHS}, Train Loss: {avg_train_loss:.4f}")

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for images, masks in valid_loader:
                images = images.float().to(DEVICE)
                masks = masks.long().to(DEVICE)
                predictions = model(images)
                loss = loss_fn(predictions, masks)
                val_loss += loss.item()

        avg_val_loss = val_loss / len(valid_loader)
        print(f"Validation Loss: {avg_val_loss:.4f}")

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            torch.save(model.state_dict(), 'best_crop_weed_model.pth')
            print("-> New best model saved!")

    print("--- Training finished! ---")

if __name__ == '__main__':
    main()
