import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import pathlib

# --- CONFIG ---
DATA_DIR = 'images'
MODEL_NAME = 'survey_animal_classifier'
IMG_SIZE = (224, 224)

def main():
    # Load Data
    train_ds = tf.keras.utils.image_dataset_from_directory(
        DATA_DIR, validation_split=0.2, subset="training", seed=123,
        image_size=IMG_SIZE, batch_size=32, label_mode='binary'
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        DATA_DIR, validation_split=0.2, subset="validation", seed=123,
        image_size=IMG_SIZE, batch_size=32, label_mode='binary'
    )

    # 1. Base Model with ImageNet Weights
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(224, 224, 3), include_top=False, weights='imagenet'
    )
    
    # 2. Unfreeze top 20 layers for texture adaptation
    base_model.trainable = True
    for layer in base_model.layers[:-20]:
        layer.trainable = False

    # 3. Build Architecture
    model = keras.Sequential([
        layers.Input(shape=(224, 224, 3)),
        layers.Rescaling(1./127.5, offset=-1), # Mandatory MobileNetV2 scaling
        base_model,
        layers.GlobalAveragePooling2D(),
        layers.Dropout(0.5), # Prevent memorizing grass
        layers.Dense(1, activation='sigmoid')
    ])

    # 4. Compile with slow Learning Rate (1e-5)
    model.compile(optimizer=keras.optimizers.Adam(1e-5),
                  loss='binary_crossentropy', metrics=['accuracy'])

    # 5. Train
    print("🚀 Training... If accuracy is >0.70 after 5 epochs, the tiling worked!")
    model.fit(train_ds, validation_data=val_ds, epochs=30)

    # 6. Save & Export
    model.save(f"{MODEL_NAME}.keras")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    with open(f"{MODEL_NAME}.tflite", 'wb') as f:
        f.write(converter.convert())
    print(f"✅ Deployment-ready model saved: {MODEL_NAME}.tflite")

if __name__ == "__main__":
    main()
