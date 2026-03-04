import torch
import albumentations as A
from albumentations.pytorch import ToTensorV2
from torch.utils.data import DataLoader, Dataset
import segmentation_models_pytorch as smp
from dataset import RoboflowCocoDataset # This file does not need to change

# This is a small helper class to correctly apply transforms to our dataset splits
class TransformedSubset(Dataset):
    def __init__(self, subset, transform=None):
        self.subset = subset
        self.transform = transform

    def __getitem__(self, index):
        image, mask = self.subset[index]
        if self.transform:
            transformed = self.transform(image=image, mask=mask)
            image = transformed['image']
            mask = transformed['mask']
        return image, mask

    def __len__(self):
        return len(self.subset)

# --- CONFIGURATION ---
DATA_DIR = "./Crop-Field-Computer-Vision-Dataset-1"
ENCODER = "resnet50"
PRETRAINED_WEIGHTS = "imagenet"
NUM_CLASSES = 2   # 0: background, 1: crop
BATCH_SIZE = 4
EPOCHS = 50
LEARNING_RATE = 0.001
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# ---------------------

def main():
    # Define separate transformations for training (with augmentation) and validation
    train_transform = A.Compose([
        A.Resize(height=512, width=512),
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.5),
        A.RandomRotate90(p=0.5),
        A.RandomBrightnessContrast(p=0.2),
        A.Normalize(mean=(0.0, 0.0, 0.0), std=(1.0, 1.0, 1.0)),
        ToTensorV2(),
    ])

    val_transform = A.Compose([
        A.Resize(height=512, width=512),
        A.Normalize(mean=(0.0, 0.0, 0.0), std=(1.0, 1.0, 1.0)),
        ToTensorV2(),
    ])

    print("Loading and preparing dataset...")
    # Load the entire dataset from the 'train' folder without any transforms
    full_dataset = RoboflowCocoDataset(data_dir=DATA_DIR, split='train', transform=None)
    
    # Calculate split sizes (80% for training, 20% for validation)
    train_size = int(0.8 * len(full_dataset))
    valid_size = len(full_dataset) - train_size
    
    # Split the dataset randomly
    train_subset, valid_subset = torch.utils.data.random_split(full_dataset, [train_size, valid_size])
    
    # IMPORTANT: Apply the correct transform to each subset using our helper class
    train_dataset = TransformedSubset(train_subset, transform=train_transform)
    valid_dataset = TransformedSubset(valid_subset, transform=val_transform)
    
    print(f"Dataset split into {len(train_dataset)} training images and {len(valid_dataset)} validation images.")
    
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
            torch.save(model.state_dict(), 'best_roboflow_crop_model.pth')
            print("-> New best model saved!")

    print("--- Training finished! ---")

if __name__ == '__main__':
    main()
