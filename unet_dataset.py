import os
from pathlib import Path
import cv2
from torch.utils.data import Dataset

class CropWeedDataset(Dataset):
    def __init__(self, data_dir, transform=None):
        self.image_dir = Path(data_dir) / 'images'
        self.mask_dir = Path(data_dir) / 'masks'
        self.transform = transform
        self.image_files = sorted(os.listdir(self.image_dir))

    def __len__(self):
        return len(self.image_files)

    def __getitem__(self, idx):
        image_name = self.image_files[idx]
        image_path = self.image_dir / image_name
        mask_name = image_name.replace('.jpg', '.png')
        mask_path = self.mask_dir / mask_name

        image = cv2.cvtColor(cv2.imread(str(image_path)), cv2.COLOR_BGR2RGB)
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)

        if self.transform:
            transformed = self.transform(image=image, mask=mask)
            image = transformed['image']
            mask = transformed['mask']

        return image, mask
