import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import pathlib

# --- CONFIG ---
DATA_DIR = 'images'
MODEL_NAME = 'survey_animal_classifier'
IMG_SIZE = (224, 224)

def main():
    # 1. Load the clean, balanced tiles
    train_ds = tf.keras.utils.image_dataset_from_directory(
        DATA_DIR, validation_split=0.2, subset="training", seed=123,
        image_size=IMG_SIZE, batch_size=32, label_mode='binary'
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        DATA_DIR, validation_split=0.2, subset="validation", seed=123,
        image_size=IMG_SIZE, batch_size=32, label_mode='binary'
    )

    # 2. Base Model (MobileNetV2 is optimized for Raspberry Pi/UGV)
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(224, 224, 3), include_top=False, weights='imagenet'
    )
    base_model.trainable = False 

    # 3. Model Architecture
    model = keras.Sequential([
        layers.Input(shape=(224, 224, 3)),
        layers.Rescaling(1./127.5, offset=-1), # Pre-scaling for MobileNetV2
        base_model,
        layers.GlobalAveragePooling2D(), # Reduces parameters to prevent grass overfitting
        layers.Dropout(0.5),
        layers.Dense(1, activation='sigmoid')
    ])

    # 4. Phase 1: Warming Up
    print("🚀 Phase 1: Training the classification head...")
    model.compile(optimizer=keras.optimizers.Adam(1e-4),
                  loss='binary_crossentropy', metrics=['accuracy'])
    model.fit(train_ds, validation_data=val_ds, epochs=10)

    # 5. Phase 2: Fine-Tuning
    print("🔓 Phase 2: Unfreezing top layers for texture adaptation...")
    base_model.trainable = True
    for layer in base_model.layers[:-20]: 
        layer.trainable = False
    
    # Use a tiny learning rate to preserve pre-trained knowledge
    model.compile(optimizer=keras.optimizers.Adam(1e-5),
                  loss='binary_crossentropy', metrics=['accuracy'])
    
    # Early stopping ensures we stop before the model memorizes specific fields
    early_stop = tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
    
    model.fit(train_ds, validation_data=val_ds, epochs=20, callbacks=[early_stop])

    # 6. Save and Export to TFLite for Deployment
    model.save(f"{MODEL_NAME}.keras")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    with open(f"{MODEL_NAME}.tflite", 'wb') as f:
        f.write(converter.convert())
    print(f"✅ Deployment-ready model saved: {MODEL_NAME}.tflite")

if __name__ == "__main__":
    main()
