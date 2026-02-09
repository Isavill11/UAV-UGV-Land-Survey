import cv2
import os
import glob
import random
import shutil

# --- CONFIGURATION ---
SOURCE_IMG_DIR = 'raw_images'
SOURCE_LABEL_DIR = 'labels'
OUTPUT_DIR = 'images'
IMG_SIZE = (224, 224)
PADDING_PERCENT = 0.30  # 30% padding around the cow

def prepare_folders():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(f"{OUTPUT_DIR}/yes_animals")
    os.makedirs(f"{OUTPUT_DIR}/no_animals")

def extract_crops():
    img_paths = glob.glob(os.path.join(SOURCE_IMG_DIR, "*.jpg"))
    animal_count = 0
    bg_count = 0

    for img_path in img_paths:
        base_name = os.path.basename(img_path).replace('.jpg', '')
        label_path = os.path.join(SOURCE_LABEL_DIR, f"{base_name}.txt")
        
        img = cv2.imread(img_path)
        if img is None: continue
        h, w, _ = img.shape

        # 1. Extract YES_ANIMALS (with padding)
        if os.path.exists(label_path):
            with open(label_path, 'r') as f:
                for i, line in enumerate(f.readlines()):
                    parts = line.split()
                    # YOLO format: class x_center y_center width height
                    cx, cy, nw, nh = map(float, parts[1:])
                    
                    # Convert to pixel coordinates
                    x1 = int((cx - nw/2) * w)
                    y1 = int((cy - nh/2) * h)
                    x2 = int((cx + nw/2) * w)
                    y2 = int((cy + nh/2) * h)

                    # Add Padding
                    pw, ph = int((x2-x1) * PADDING_PERCENT), int((y2-y1) * PADDING_PERCENT)
                    x1, y1 = max(0, x1-pw), max(0, y1-ph)
                    x2, y2 = min(w, x2+pw), min(h, y2+ph)

                    crop = img[y1:y2, x1:x2]
                    if crop.size > 0:
                        crop = cv2.resize(crop, IMG_SIZE)
                        cv2.imwrite(f"{OUTPUT_DIR}/yes_animals/{base_name}_{i}.jpg", crop)
                        animal_count += 1

        # 2. Extract NO_ANIMALS (Random Background Patches)
        # We start by taking 5 patches per image
        for j in range(5):
            rx = random.randint(0, w - IMG_SIZE[0])
            ry = random.randint(0, h - IMG_SIZE[1])
            bg_crop = img[ry:ry+IMG_SIZE[1], rx:rx+IMG_SIZE[0]]
            cv2.imwrite(f"{OUTPUT_DIR}/no_animals/{base_name}_bg_{j}.jpg", bg_crop)
            bg_count += 1

    return animal_count, bg_count

def balance_data():
    yes_dir = f"{OUTPUT_DIR}/yes_animals"
    no_dir = f"{OUTPUT_DIR}/no_animals"
    
    yes_files = os.listdir(yes_dir)
    no_files = os.listdir(no_dir)
    
    print(f"Initial Counts - Animals: {len(yes_files)}, Background: {len(no_files)}")

    if len(yes_files) > len(no_files):
        # Too many animals, delete the excess
        diff = len(yes_files) - len(no_files)
        to_delete = random.sample(yes_files, diff)
        for f in to_delete:
            os.remove(os.path.join(yes_dir, f))
    else:
        # Too much background, delete the excess
        diff = len(no_files) - len(yes_files)
        to_delete = random.sample(no_files, diff)
        for f in to_delete:
            os.remove(os.path.join(no_dir, f))

    print(f"⚖️ Final Balanced Counts: {len(os.listdir(yes_dir))} per class.")

if __name__ == "__main__":
    prepare_folders()
    print("✂️ Extracting crops...")
    extract_crops()
    balance_data()
    print("🚀 Data ready for balanced training.")
