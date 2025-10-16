import os
import json
from pathlib import Path
import cv2
import numpy as np
from torch.utils.data import Dataset

class RoboflowCocoDataset(Dataset):
    def __init__(self, data_dir, split='train', transform=None):
        self.data_dir = Path(data_dir) / split
        self.transform = transform

        # Load the COCO annotations file
        annotations_path = self.data_dir / "_annotations.coco.json"
        with open(annotations_path, 'r') as f:
            coco_data = json.load(f)

        # Store image info and create a map for annotations
        self.images = coco_data['images']
        self.annotations_map = {}
        for ann in coco_data['annotations']:
            image_id = ann['image_id']
            if image_id not in self.annotations_map:
                self.annotations_map[image_id] = []
            self.annotations_map[image_id].append(ann)

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        # Get image information
        image_info = self.images[idx]
        image_id = image_info['id']
        image_path = self.data_dir / image_info['file_name']

        # Load the image
        image = cv2.cvtColor(cv2.imread(str(image_path)), cv2.COLOR_BGR2RGB)

        # Create a blank mask
        height, width = image_info['height'], image_info['width']
        mask = np.zeros((height, width), dtype=np.uint8)

        # Find and draw all annotations (polygons) for this image
        if image_id in self.annotations_map:
            for ann in self.annotations_map[image_id]:
                # The category_id will be the color for the mask (e.g., 1)
                class_id = ann['category_id']

                # Polygons are stored as a list of points [x1, y1, x2, y2, ...]
                for polygon in ann['segmentation']:
                    # Reshape the polygon to the format cv2.fillPoly expects
                    points = np.array(polygon, dtype=np.int32).reshape(-1, 2)
                    cv2.fillPoly(mask, [points], color=class_id)

        # Apply transformations if they exist
        if self.transform:
            transformed = self.transform(image=image, mask=mask)
            image = transformed['image']
            mask = transformed['mask']

        return image, mask
