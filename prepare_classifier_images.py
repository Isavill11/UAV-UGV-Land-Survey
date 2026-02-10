import cv2
import os
import glob
import random
import numpy as np
import shutil

# --- CONFIG ---
SOURCE_IMG_DIR = 'raw_images'
SOURCE_LABEL_DIR = 'labels'
OUTPUT_DIR = 'images'
IMG_SIZE = (224, 224)

def enhance_for_agriculture(img):
    """Uses CLAHE to force the cow silhouette to stand out from the grass."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    # This 'stretches' the contrast locally
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    enhanced = cv2.merge((cl,a,b))
    return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

def main():
    if os.path.exists(OUTPUT_DIR): shutil.rmtree(OUTPUT_DIR)
    os.makedirs(f"{OUTPUT_DIR}/no_animals", exist_ok=True)
    os.makedirs(f"{OUTPUT_DIR}/yes_animals", exist_ok=True)
    
    img_paths = glob.glob(os.path.join(SOURCE_IMG_DIR, "*.jpg"))
    print(f"Processing {len(img_paths)} source images...")

    for img_path in img_paths:
        base = os.path.splitext(os.path.basename(img_path))[0]
        label_path = os.path.join(SOURCE_LABEL_DIR, f"{base}.txt")
        img = cv2.imread(img_path)
        if img is None or not os.path.exists(label_path): continue
        
        # 1. Enhance the whole frame first
        img = enhance_for_agriculture(img)
        h, w, _ = img.shape

        # 2. Extract Animals
        with open(label_path, 'r') as f:
            for i, line in enumerate(f.readlines()):
                parts = line.split()
                if len(parts) < 5: continue
                cx, cy, nw, nh = map(float, parts[1:5])
                x1, y1 = int((cx - nw/2) * w), int((cy - nh/2) * h)
                x2, y2 = int((cx + nw/2) * w), int((cy + nh/2) * h)
                
                # Context padding (40%) helps the model see the grass/cow boundary
                pad = int(max(x2-x1, y2-y1) * 0.4)
                crop = img[max(0, y1-pad):min(h, y2+pad), max(0, x1-pad):min(w, x2+pad)]
                if crop.size > 0:
                    cv2.imwrite(f"{OUTPUT_DIR}/yes_animals/{base}_{i}.jpg", cv2.resize(crop, IMG_SIZE))

        # 3. Extract Background (Randomly but from the same image)
        for j in range(3):
            rx, ry = random.randint(0, w-300), random.randint(0, h-300)
            bg_crop = img[ry:ry+300, rx:rx+300]
            cv2.imwrite(f"{OUTPUT_DIR}/no_animals/{base}_bg_{j}.jpg", cv2.resize(bg_crop, IMG_SIZE))

    print("⚖️ Balancing folders...")
    # Quick 1:1 balance check
    yes_f = os.listdir(f"{OUTPUT_DIR}/yes_animals")
    no_f = os.listdir(f"{OUTPUT_DIR}/no_animals")
    target = min(len(yes_f), len(no_f))
    for f in yes_f[target:]: os.remove(os.path.join(f"{OUTPUT_DIR}/yes_animals", f))
    for f in no_f[target:]: os.remove(os.path.join(f"{OUTPUT_DIR}/no_animals", f))
    print(f"✅ Dataset ready: {target} images per class.")

if __name__ == "__main__":
    main()
