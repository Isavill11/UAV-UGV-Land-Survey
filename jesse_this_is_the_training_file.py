import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import pathlib

# --- 1. CONFIGURATION ---
DATA_DIR = 'images'
MODEL_NAME = 'survey_animal_classifier'
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
MAX_EPOCHS = 50 

def main():
    data_dir = pathlib.Path(DATA_DIR)
    
    # --- 2. LOAD DATA WITH EXPLICIT CLASS NAMES ---
    # We force 'no_animals' to be Index 0 and 'yes_animals' to be Index 1
    # This ensures 1.0 = YES ANIMAL in all mathematical calculations.
    load_args = {
        "directory": data_dir,
        "validation_split": 0.2,
        "seed": 123,
        "image_size": IMG_SIZE,
        "batch_size": BATCH_SIZE,
        "label_mode": 'binary',
        "class_names": ['no_animals', 'yes_animals'] 
    }
    
    train_ds = tf.keras.utils.image_dataset_from_directory(subset="training", **load_args)
    val_ds = tf.keras.utils.image_dataset_from_directory(subset="validation", **load_args)

    # Double-check labels in console
    print(f"✅ Verified: Index 0 is {train_ds.class_names[0]}")
    print(f"✅ Verified: Index 1 is {train_ds.class_names[1]}")

    AUTOTUNE = tf.data.AUTOTUNE
    train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
    val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)

    # --- 3. AUGMENTATION FOR AERIAL VARIETY ---
    # Adding RandomZoom and Contrast to handle different heights and sun glare
    data_augmentation = keras.Sequential([
        layers.RandomFlip('horizontal_and_vertical'),
        layers.RandomRotation(0.2),
        layers.RandomZoom(0.3),       # Handles different drone altitudes
        layers.RandomBrightness(0.3), # Handles shadows/glare
        layers.RandomContrast(0.3),   # Makes cow silhouettes pop
        layers.GaussianNoise(0.05),   # Handles drone sensor grain
    ])

    # --- 4. BUILD MODEL ---
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=IMG_SIZE + (3,), include_top=False, weights='imagenet'
    )
    base_model.trainable = False 

    preprocess_input = tf.keras.applications.mobilenet_v2.preprocess_input

    inputs = keras.Input(shape=IMG_SIZE + (3,))
    x = data_augmentation(inputs)
    x = preprocess_input(x)
    x = base_model(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.4)(x) # Slightly higher to prevent memorizing specific grass
    outputs = layers.Dense(1, activation='sigmoid')(x)
    model = keras.Model(inputs, outputs)

    # --- 5. CLASS WEIGHTS (Priority on Animals) ---
    # Since 'yes_animals' is now Index 1, we set its weight to 4.0
    # This forces the model to move the score toward 1.0 when it sees a cow.
    class_weights = {0: 1.0, 1: 4.0}

    # --- 6. CALLBACKS ---
    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor='val_loss', patience=7, restore_best_weights=True
    )

    # --- 7. PHASE 1: WARM UP ---
    print("🚀 Phase 1: Training the classification head...")
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=0.0001),
                  loss='binary_crossentropy', metrics=['accuracy'])
    
    model.fit(train_ds, validation_data=val_ds, epochs=10, 
              class_weight=class_weights, callbacks=[early_stop])

    # --- 8. PHASE 2: FINE-TUNING ---
    print("🔓 Phase 2: Unfreezing base for aerial texture adaptation...")
    base_model.trainable = True
    
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=1e-5),
                  loss='binary_crossentropy', metrics=['accuracy'])

    model.fit(train_ds, validation_data=val_ds, epochs=MAX_EPOCHS,
              class_weight=class_weights, callbacks=[early_stop])

    # --- 9. EXPORT ---
    model.save(f"{MODEL_NAME}.keras")
    
    print("Converting to TFLite for deployment...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()
    
    with open(f"{MODEL_NAME}.tflite", 'wb') as f:
        f.write(tflite_model)
    print(f"✅ Deployment-ready model saved: {MODEL_NAME}.tflite")

if __name__ == '__main__':
    main()
