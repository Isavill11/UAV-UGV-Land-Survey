import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import pathlib

# --- 1. CONFIGURATION ---
DATA_DIR = 'images'
MODEL_NAME = 'mini_survey_classifier'
IMG_SIZE = (224, 224)
BATCH_SIZE = 16  # Smaller batches help the model focus on noisy agricultural details
MAX_EPOCHS = 50

def main():
    data_dir = pathlib.Path(DATA_DIR)
    
    # --- 2. LOAD BALANCED DATA ---
    train_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=0.2,
        subset="training",
        seed=123,
        image_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        label_mode='binary'
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=0.2,
        subset="validation",
        seed=123,
        image_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        label_mode='binary'
    )

    # --- 3. AUGMENTATION ---
    # We keep this simple so we don't distort the animal's texture too much
    data_augmentation = keras.Sequential([
        layers.RandomFlip("horizontal_and_vertical"),
        layers.RandomRotation(0.1),
    ])

    # --- 4. THE MINIATURIZED MODEL ---
    # This 3-block structure is much easier for a small dataset to optimize
    model = keras.Sequential([
        keras.Input(shape=(224, 224, 3)),
        data_augmentation,
        layers.Rescaling(1./255),  # Normalizes pixel values to [0, 1]
        
        # Block 1: Low-level edges and color transitions
        layers.Conv2D(16, (3, 3), activation='relu', padding='same'),
        layers.MaxPooling2D(),
        
        # Block 2: Mid-level texture detection (fur vs. grass patterns)
        layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
        layers.MaxPooling2D(),
        
        # Block 3: High-level shape/silhouette consolidation
        layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
        layers.MaxPooling2D(),
        
        layers.Flatten(),
        layers.Dense(64, activation='relu'),
        layers.Dropout(0.5),  # Prevents the model from memorizing specific grass patches
        layers.Dense(1, activation='sigmoid')  # Output: 0 (No Animal) to 1 (Yes Animal)
    ])

    # --- 5. COMPILATION ---
    # Using a slightly higher learning rate to "kick" it out of the 0.5 stagnation
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )

    # --- 6. CALLBACKS ---
    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor='val_loss', 
        patience=8, 
        restore_best_weights=True
    )

    # --- 7. TRAINING ---
    print(f"🚀 Starting Mini-Surveyor Training...")
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=MAX_EPOCHS,
        callbacks=[early_stop]
    )

    # --- 8. SAVE & EXPORT ---
    model.save(f"{MODEL_NAME}.keras")
    
    # TFLite conversion for Raspberry Pi deployment
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    with open(f"{MODEL_NAME}.tflite", 'wb') as f:
        f.write(tflite_model)
    
    print(f"✅ Training Complete. Model saved as {MODEL_NAME}.tflite")

if __name__ == "__main__":
    main()
