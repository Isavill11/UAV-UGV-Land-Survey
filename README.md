# UAV-UGV-Land-Survey

## Getting Started
### 1. Clone the Repository
git clone https://github.com/<your-username>/UAV-UGV-Land-Survey.git
cd UAV-UGV-Land-Survey

### 2. Open the Folder in Your IDE

Use any Python-compatible IDE (such as PyCharm, VS Code, or Jupyter Notebook).

##  Dataset Setup
### 1. Download Dataset

Download the dataset from Kaggle:
🔗 [Cattle Detection in Aerial Imagery](https://www.kaggle.com/datasets/magnusmakgasane/cattle-detection-in-aerial-imagery)

Unzip the dataset and save all folders directly in the main project directory.

## Data Preparation
### 1. Format the CSV Files

Run:
```
python prepare_data_from_csv.py
```

✅ This script organizes your dataset into the correct folder format for training and validation.

Tip: Ensure that your image and CSV file directories are correctly set within the script before running.

### 2. Verify Folder Paths

Next, verify that the data paths are valid:
```
python verify_paths.py
```

If you see no errors, everything is set up correctly!
If you do see errors, check:

- Folder names
- File paths in the script
- Directory structure

### 3. Update Configuration (if needed)

If you renamed folders or moved files, open:
```
cattle_config.yaml
```

and update the train and val dataset paths.
The file is in YAML format (like JSON, but cleaner).

### 4. Run Dataset Check

Finally, confirm your dataset integrity:
```
python check_dataset.py
```

If any issues appear, double-check your paths — most errors are path-related.

## Model Training

Once your dataset is ready and verified, run:
```
python train.py
```

This will start the model training process using your prepared data.

🧩 Folder Structure
```
UAV-UGV-Land-Survey/
│
├── prepare_data_from_csv.py
├── verify_paths.py
├── check_dataset.py
├── train.py
├── cattle_config.yaml
│
├── /images
│   ├── train/
│   └── valid/
│
├── /labels
│   ├── train/
│   └── valid/
│
└── README.md
```

## Authors

Isabella Villarreal

Jesse Fernandez

Roberto Esquivel

## License
