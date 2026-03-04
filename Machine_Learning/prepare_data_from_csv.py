import pandas as pd
import os
from sklearn.model_selection import train_test_split
from pathlib import Path
import shutil

# --- CONFIGURATION ---
image_dir = Path("train_images/train_images") 
csv_file = Path("Train.csv")
output_dir = Path("cattle_yolo_dataset")
# ---------------------

def convert_normalized_voc_to_yolo(box):
    """
    Converts a pre-normalized (xmin, ymin, xmax, ymax) box to 
    YOLO's (x_center, y_center, w, h) format.
    """
    xmin, ymin, xmax, ymax = box
    x_center = (xmin + xmax) / 2.0
    y_center = (ymin + ymax) / 2.0
    w = xmax - xmin
    h = ymax - ymin
    return (x_center, y_center, w, h)

def process_csv_data():
    """Main function to read CSV and create YOLO dataset."""
    print("Reading CSV file...")
    df = pd.read_csv(csv_file)
    # The column with the image name is 'ID'
    image_groups = df.groupby('ID')

    unique_image_ids = list(image_groups.groups.keys())
    print(f"Found {len(unique_image_ids)} unique images to process.")

    train_ids, valid_ids = train_test_split(unique_image_ids, test_size=0.2, random_state=42)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    for split in ["train", "valid"]:
        os.makedirs(output_dir / f"images/{split}", exist_ok=True)
        os.makedirs(output_dir / f"labels/{split}", exist_ok=True)

    for split, ids in [("train", train_ids), ("valid", valid_ids)]:
        print(f"\nProcessing {split} set...")
        for image_id in ids:
            image_path = image_dir / f"{image_id}.jpg"
            if not image_path.exists():
                continue

            annotations = image_groups.get_group(image_id)
            yolo_labels = []

            for _, row in annotations.iterrows():
                class_id = 0
                # Bounding box values are already normalized in the CSV
                box = (row['xmin'], row['ymin'], row['xmax'], row['ymax'])
                yolo_box = convert_normalized_voc_to_yolo(box)
                
                yolo_labels.append(f"{class_id} {yolo_box[0]} {yolo_box[1]} {yolo_box[2]} {yolo_box[3]}")

            label_path = output_dir / f"labels/{split}/{image_id}.txt"
            with open(label_path, "w") as f:
                f.write("\n".join(yolo_labels))
            
            shutil.copy(image_path, output_dir / f"images/{split}/")

    print(f"\nDataset processing complete! You can now start training.")

if __name__ == "__main__":
    process_csv_data()
