from ultralytics.data.utils import check_det_dataset

# This script uses YOLO's official tool to check your dataset.

# Path to your YAML configuration file
data_yaml_path = 'cattle_config.yaml'

try:
    # Run the dataset checker
    results = check_det_dataset(data_yaml_path, autodownload=False)
    print("✅ YOLO dataset check complete.")
    # The tool will print out statistics if successful or an error if it fails.
except Exception as e:
    print(f"❌ An error occurred during the dataset check: {e}")