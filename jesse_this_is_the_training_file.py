import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import matplotlib.pyplot as plt
import pathlib

# --- CONFIGURATION ---
DATA_DIR = 'images'
MODEL_NAME = 'animal_binary_classifier'
IMG_SIZE = (224, 224)
BATCH_SIZE = 32

def main():
    data_dir = pathlib.Path(DATA_DIR)
    
    # --- 1. Load Data ---
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

    # --- 2. Build Model ---
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=IMG_SIZE + (3,), include_top=False, weights='imagenet'
    )
    base_model.trainable = False  # Start frozen

    preprocess_input = tf.keras.applications.mobilenet_v2.preprocess_input

    inputs = keras.Input(shape=IMG_SIZE + (3,))
    x = preprocess_input(inputs)
    x = base_model(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.2)(x)
    outputs = layers.Dense(1, activation='sigmoid')(x)
    model = keras.Model(inputs, outputs)

    # --- 3. Phase 1: Training the Head ---
    print("🚀 Phase 1: Training the top layer...")
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=0.0001),
                  loss='binary_crossentropy', metrics=['accuracy'])
    
    model.fit(train_ds, validation_data=val_ds, epochs=5)

    # --- 4. Phase 2: Fine-Tuning (Unfreeze) ---
    print("🔓 Phase 2: Unfreezing base model for aerial adaptation...")
    base_model.trainable = True
    
    # Use a MUCH smaller learning rate so we don't break pre-trained features
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=1e-5),
                  loss='binary_crossentropy', metrics=['accuracy'])

    history = model.fit(train_ds, validation_data=val_ds, epochs=10)

    # --- 5. Save & Convert ---
    model.save(f"{MODEL_NAME}.keras")
    
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()
    
    with open(f"{MODEL_NAME}.tflite", 'wb') as f:
        f.write(tflite_model)
    print(f"✅ TFLite model saved: {MODEL_NAME}.tflite")

if __name__ == '__main__':
    main()
