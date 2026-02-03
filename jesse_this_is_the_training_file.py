import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import matplotlib.pyplot as plt
import pathlib

# --- 1. CONFIGURATION ---
DATA_DIR = 'images'
MODEL_NAME = 'survey_animal_classifier'
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
# Increased epochs because EarlyStopping will cut it off when it's "done"
MAX_EPOCHS = 50 

def main():
    data_dir = pathlib.Path(DATA_DIR)
    
    # --- 2. LOAD DATA ---
    train_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir, validation_split=0.2, subset="training", seed=123,
        image_size=IMG_SIZE, batch_size=BATCH_SIZE, label_mode='binary'
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir, validation_split=0.2, subset="validation", seed=123,
        image_size=IMG_SIZE, batch_size=BATCH_SIZE, label_mode='binary'
    )

    AUTOTUNE = tf.data.AUTOTUNE
    train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
    val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)

    # --- 3. SURVEY-OPTIMIZED AUGMENTATION (Noise & Lighting) ---
    # This simulates real-world drone sensor noise and field shadows
    data_augmentation = keras.Sequential([
        layers.RandomFlip('horizontal_and_vertical'),
        layers.RandomRotation(0.2),
        layers.RandomZoom(0.1),
        layers.RandomBrightness(0.3),  # Sun vs. Clouds
        layers.RandomContrast(0.3),    # Harsh midday light
        layers.GaussianNoise(0.05),    # Sensor grain
    ])

    # --- 4. BUILD MODEL ---
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=IMG_SIZE + (3,), include_top=False, weights='imagenet'
    )
    base_model.trainable = False  # Phase 1: Frozen

    preprocess_input = tf.keras.applications.mobilenet_v2.preprocess_input

    inputs = keras.Input(shape=IMG_SIZE + (3,))
    x = data_augmentation(inputs)  # Noise applied here
    x = preprocess_input(x)
    x = base_model(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.3)(x) # Higher dropout to prevent overfitting to specific fields
    outputs = layers.Dense(1, activation='sigmoid')(x)
    model = keras.Model(inputs, outputs)

    # --- 5. CLASS WEIGHTS (The "Don't Miss" Factor) ---
    # 0: no_animal, 1: animal
    # We set '1' to 3.0 so missing a cow is 3x more "painful" for the model
    class_weights = {0: 1.0, 1: 3.0}

    # --- 6. CALLBACKS ---
    # Stops training when validation loss stops improving for 5 epochs
    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor='val_loss', patience=5, restore_best_weights=True
    )

    # --- 7. PHASE 1: HEAD TRAINING ---
    print("🚀 Phase 1: Training the classification head...")
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=0.0001),
                  loss='binary_crossentropy', metrics=['accuracy'])
    
    model.fit(train_ds, validation_data=val_ds, epochs=10, 
              class_weight=class_weights, callbacks=[early_stop])

    # --- 8. PHASE 2: FINE-TUNING (UNFREEZE) ---
    print("🔓 Phase 2: Unfreezing base for aerial texture adaptation...")
    base_model.trainable = True
    
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=1e-5),
                  loss='binary_crossentropy', metrics=['accuracy'])

    history = model.fit(train_ds, validation_data=val_ds, epochs=MAX_EPOCHS,
                        class_weight=class_weights, callbacks=[early_stop])

    # --- 9. EXPORT ---
    model.save(f"{MODEL_NAME}.keras")
    
    print("Converting to TFLite for Raspberry Pi...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()
    
    with open(f"{MODEL_NAME}.tflite", 'wb') as f:
        f.write(tflite_model)
    print(f"✅ Deployment-ready model saved: {MODEL_NAME}.tflite")

if __name__ == '__main__':
    main()
