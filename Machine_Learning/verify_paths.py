import yaml
from pathlib import Path

# This script will check the exact paths listed in your YAML file.

print("--- Verifying Dataset Paths ---")

try:
    # Define the path to your config file
    yaml_path = Path('cattle_config.yaml')

    if not yaml_path.exists():
        print(f"❌ ERROR: Cannot find the config file at '{yaml_path}'")
    else:
        # Load the YAML file
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        # --- Check the Training Path ---
        train_images_path = Path(data['train'])
        train_labels_path = train_images_path.parent.parent / 'labels' / 'train'

        print(f"\n1. Checking TRAIN path: {train_images_path}")
        print(f"   -> Image directory exists: {train_images_path.exists()}")
        if train_images_path.exists():
            num_images = len(list(train_images_path.glob('*.jpg')))
            print(f"   -> Found {num_images} images (.jpg)")

        print(f"   Corresponding LABEL path: {train_labels_path}")
        print(f"   -> Label directory exists: {train_labels_path.exists()}")
        if train_labels_path.exists():
            num_labels = len(list(train_labels_path.glob('*.txt')))
            print(f"   -> Found {num_labels} labels (.txt)")


        # --- Check the Validation Path ---
        val_images_path = Path(data['val'])
        val_labels_path = val_images_path.parent.parent / 'labels' / 'valid'

        print(f"\n2. Checking VALIDATION path: {val_images_path}")
        print(f"   -> Image directory exists: {val_images_path.exists()}")
        if val_images_path.exists():
            num_images = len(list(val_images_path.glob('*.jpg')))
            print(f"   -> Found {num_images} images (.jpg)")

        print(f"   Corresponding LABEL path: {val_labels_path}")
        print(f"   -> Label directory exists: {val_labels_path.exists()}")
        if val_labels_path.exists():
            num_labels = len(list(val_labels_path.glob('*.txt')))
            print(f"   -> Found {num_labels} labels (.txt)")

except Exception as e:
    print(f"\n❌ An error occurred: {e}")