import pandas as pd
import os
from sklearn.model_selection import train_test_split
from pathlib import Path
import shutil
import cv2  # OpenCV for getting image dimensions

# --- CONFIGURATION ---
# The names of the folders and files you got after unzipping
image_dir = Path("train_images/train_images")
csv_file = Path("Train.csv")

# The name for our final, organized dataset folder
output_dir = Path("cattle_yolo_dataset")


# ---------------------

def convert_to_yolo(size, box):
    """Converts (xmin, ymin, xmax, ymax) box to YOLO's (x_center, y_center, w, h) format."""
    dw = 1.0 / size[0]
    dh = 1.0 / size[1]
    x_center = (box[0] + box[2]) / 2.0 * dw
    y_center = (box[1] + box[3]) / 2.0 * dh
    w = (box[2] - box[0]) * dw
    h = (box[3] - box[1]) * dh
    return (x_center, y_center, w, h)


def process_csv_data():
    """Main function to read CSV and create YOLO dataset."""
    print("Reading CSV file...")
    # Read the CSV and group bounding boxes by image ID
    df = pd.read_csv(csv_file)
    image_groups = df.groupby('ID')  # <-- THIS IS THE CORRECTED LINE

    unique_image_ids = list(image_groups.groups.keys())
    print(f"Found {len(unique_image_ids)} unique images to process.")

    # Split image IDs into training and validation sets
    train_ids, valid_ids = train_test_split(unique_image_ids, test_size=0.2, random_state=42)

    # Clean and create output directories
    if output_dir.exists():
        shutil.rmtree(output_dir)
    for split in ["train", "valid"]:
        os.makedirs(output_dir / f"images/{split}", exist_ok=True)
        os.makedirs(output_dir / f"labels/{split}", exist_ok=True)

    # Process each split
    for split, ids in [("train", train_ids), ("valid", valid_ids)]:
        print(f"\nProcessing {split} set...")
        for image_id in ids:
            # Get all annotations for this image
            annotations = image_groups.get_group(image_id)

            image_path = image_dir / f"{image_id}.jpg"
            if not image_path.exists():
                print(f"Warning: Image file not found for {image_id}. Skipping.")
                continue

            # Get image dimensions using OpenCV
            img = cv2.imread(str(image_path))
            height, width, _ = img.shape

            yolo_labels = []
            for _, row in annotations.iterrows():
                # The class is always 'cattle', so class_id is 0
                class_id = 0
                box = (row['xmin'], row['ymin'], row['xmax'], row['ymax'])
                yolo_box = convert_to_yolo((width, height), box)

                yolo_labels.append(f"{class_id} {yolo_box[0]} {yolo_box[1]} {yolo_box[2]} {yolo_box[3]}")

            # Write the YOLO label file
            label_path = output_dir / f"labels/{split}/{image_id}.txt"
            with open(label_path, "w") as f:
                f.write("\n".join(yolo_labels))

            # Copy the image file
            shutil.copy(image_path, output_dir / f"images/{split}/")

    print(f"\nDataset processing complete! Check the '{output_dir}' folder.")


if __name__ == "__main__":
    process_csv_data()