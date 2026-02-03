import cv2
import os
import random

# --- CONFIGURATION ---
IMAGE_DIR = '/Users/robert.esquivel/Documents/Programming_Stuff/PythonProject2/CowSpots.v2i.yolov8/train/images'
LABEL_DIR = '/Users/robert.esquivel/Documents/Programming_Stuff/PythonProject2/CowSpots.v2i.yolov8/train/labels'
OUTPUT_ANIMAL = 'images/animal'
OUTPUT_NO_ANIMAL = 'images/no_animal'

TARGET_SIZE = (224, 224)
PADDING_FACTOR = 0.3  # Adds 30% extra space for context
PATCHES_PER_EMPTY_IMG = 50
HARD_NEGATIVES_PER_IMG = 10

os.makedirs(OUTPUT_ANIMAL, exist_ok=True)
os.makedirs(OUTPUT_NO_ANIMAL, exist_ok=True)


def is_overlapping(new_box, existing_boxes):
    nx1, ny1, nx2, ny2 = new_box
    for (ex1, ey1, ex2, ey2) in existing_boxes:
        if not (nx2 < ex1 or nx1 > ex2 or ny2 < ey1 or ny1 > ey2):
            return True
    return False


def crop_cattle():
    img_files = [f for f in os.listdir(IMAGE_DIR) if f.endswith(('.jpg', '.png'))]
    print(f"🔍 Processing {len(img_files)} images with {PADDING_FACTOR * 100}% padding...")

    for img_name in img_files:
        img = cv2.imread(os.path.join(IMAGE_DIR, img_name))
        if img is None: continue
        h, w, _ = img.shape

        label_path = os.path.join(LABEL_DIR, img_name.rsplit('.', 1)[0] + '.txt')
        existing_boxes = []

        if os.path.exists(label_path) and os.path.getsize(label_path) > 0:
            with open(label_path, 'r') as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    parts = line.split()
                    if len(parts) < 5: continue

                    x_c, y_c, wb, hb = map(float, parts[1:5])

                    # Apply Padding to help the model see the cow's silhouette
                    wb_p, hb_p = wb * (1 + PADDING_FACTOR), hb * (1 + PADDING_FACTOR)

                    x1, y1 = max(0, int((x_c - wb_p / 2) * w)), max(0, int((y_c - hb_p / 2) * h))
                    x2, y2 = min(w, int((x_c + wb_p / 2) * w)), min(h, int((y_c + hb_p / 2) * h))
                    existing_boxes.append((x1, y1, x2, y2))

                    crop = img[y1:y2, x1:x2]
                    if crop.size > 0:
                        resized = cv2.resize(crop, TARGET_SIZE, interpolation=cv2.INTER_CUBIC)
                        cv2.imwrite(f"{OUTPUT_ANIMAL}/{i}_{img_name}", resized)

            for j in range(HARD_NEGATIVES_PER_IMG):
                rx, ry = random.randint(0, w - TARGET_SIZE[0]), random.randint(0, h - TARGET_SIZE[1])
                new_box = (rx, ry, rx + TARGET_SIZE[0], ry + TARGET_SIZE[1])
                if not is_overlapping(new_box, existing_boxes):
                    bg_crop = img[ry:ry + TARGET_SIZE[1], rx:rx + TARGET_SIZE[0]]
                    cv2.imwrite(f"{OUTPUT_NO_ANIMAL}/hard_neg_{j}_{img_name}", bg_crop)
        else:
            for k in range(PATCHES_PER_EMPTY_IMG):
                rx, ry = random.randint(0, w - TARGET_SIZE[0]), random.randint(0, h - TARGET_SIZE[1])
                bg_crop = img[ry:ry + TARGET_SIZE[1], rx:rx + TARGET_SIZE[0]]
                cv2.imwrite(f"{OUTPUT_NO_ANIMAL}/patch_{k}_{img_name}", bg_crop)

    print("✅ Cropping complete.")


if __name__ == "__main__":
    crop_cattle()
