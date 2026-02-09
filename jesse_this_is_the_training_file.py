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
    
    # --- 2. LOAD DATA (1:1 Balanced) ---
    # TensorFlow will now see exactly equal amounts of Yes and No
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

    # --- 3. AUGMENTATION (Field-Resilience) ---
    data_augmentation = keras.Sequential([
        layers.RandomFlip('horizontal_and_vertical'),
        layers.RandomRotation(0.2),
        layers.RandomZoom(0.2),
        layers.RandomBrightness(0.3), 
        layers.RandomContrast(0.4),   # Forces silhouettes to pop against grass
        layers.GaussianNoise(0.05),   # Mimics sensor grain
    ])

    # --- 4. BUILD MODEL (MobileNetV2) ---
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=IMG_SIZE + (3,), include_top=False, weights='imagenet'
    )
    base_model.trainable = False  # Phase 1: Frozen

    preprocess_input = tf.keras.applications.mobilenet_v2.preprocess_input

    inputs = keras.Input(shape=IMG_SIZE + (3,))
    x = data_augmentation(inputs)
    x = preprocess_input(x)
    x = base_model(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.4)(x) 
    outputs = layers.Dense(1, activation='sigmoid')(x)
    model = keras.Model(inputs, outputs)

    # --- 5. CALLBACKS ---
    # EarlyStopping prevents the model from "memorizing" specific grass patches
    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor='val_loss', patience=7, restore_best_weights=True
    )

    # --- 6. PHASE 1: HEAD TRAINING ---
    print("🚀 Phase 1: Training the classification head...")
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=0.0001),
                  loss='binary_crossentropy', metrics=['accuracy'])
    
    model.fit(train_ds, validation_data=val_ds, epochs=10, callbacks=[early_stop])

    # --- 7. PHASE 2: FINE-TUNING (The "Unfreeze") ---
    print("🔓 Phase 2: Adapting weights to aerial agricultural textures...")
    base_model.trainable = True
    
    # We use a tiny learning rate so we don't "shatter" the pre-trained weights
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=1e-5),
                  loss='binary_crossentropy', metrics=['accuracy'])

    model.fit(train_ds, validation_data=val_ds, epochs=MAX_EPOCHS, callbacks=[early_stop])

    # --- 8. EXPORT ---
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
