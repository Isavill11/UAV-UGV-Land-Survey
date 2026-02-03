# 🛰️ Collaborative UAV/UGV Agricultural Survey System

This project implements a decentralized "Scout-and-Survey" pipeline designed for autonomous agricultural land monitoring. The system utilizes a **UAV (Drone)** to perform rapid aerial scouting and a **UGV (Rover)** for ground-level verification and detailed surveying.

---

## 🐄 How the Binary Classifier Works
The heart of the drone's scouting logic is a lightweight **MobileNetV2 Binary Classifier**. Unlike standard object detectors that require high computational power, this classifier is optimized to run in real-time on a **Raspberry Pi**.

### System Logic:
* **Presence Detection:** The drone scans its video feed in $224 \times 224$ patches.
* **Filtering:** The classifier determines if a patch is `yes_animal` or `no_animal`. 
* **Collaborative Handoff:** Only patches with a positive detection are flagged. The drone then transmits these coordinates to the **Rover**, which drives to the location to perform a high-resolution survey or sensor reading.



---

## 📊 Dataset & Processing
To achieve high accuracy in unpredictable field conditions, the dataset is processed using the following techniques:

* **Contextual Padding:** We add **30% extra space** around cattle crops. This allows the model to see the silhouette of the animal against the grass, which is critical for edge detection in low-resolution aerial views.
* **Data Augmentation (Noise & Lighting):** We inject random Gaussian noise, brightness shifts, and contrast changes during training. This simulates harsh sunlight, shadows from clouds, and drone vibration.
* **Hard Negative Mining:** We extract empty patches of grass, rocks, and dirt from images where cows are present to ensure the model doesn't get "tricked" by natural agricultural textures.



---

## 💻 Installation & Usage

### 1. Prerequisites
Ensure you have the following libraries installed:
```bash
pip install tensorflow opencv-python numpy matplotlib
```

### 2. Data Preparation
Organize your raw images and YOLO labels, then run the script to generate the training database:
```bash
python prepare_data.py
```

### 3. Model Training
The training script uses Two-Phase Fine-Tuning:
Phase 1: Trains the top classification layers while the base model is frozen.
Phase 2: Unfreezes the base model with a very low learning rate ($1 \times 10^{-5}$) to adapt the pre-trained weights to aerial agricultural textures.
```bash
python train_model.py
```
### 4. Model Testing
Test your model's confidence on a local folder of images before deployment:
```bash
python test_model.py
```
