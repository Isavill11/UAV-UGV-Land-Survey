import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import pathlib

# --- CONFIG ---
DATA_DIR = 'images'
MODEL_NAME = 'survey_animal_classifier'
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
MAX_EPOCHS = 100 # Increased because training from scratch takes longer

def main():
    data_dir = pathlib.Path(DATA_DIR)
    train_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir, validation_split=0.2, subset="training", seed=123,
        image_size=IMG_SIZE, batch_size=BATCH_SIZE, label_mode='binary'
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir, validation_split=0.2, subset="validation", seed=123,
        image_size=IMG_SIZE, batch_size=BATCH_SIZE, label_mode='binary'
    )

    # AUGMENTATION
    data_augmentation = keras.Sequential([
        layers.RandomFlip('horizontal_and_vertical'),
        layers.RandomRotation(0.2),
        layers.RandomContrast(0.3),
    ])

    # BUILD MODEL (No pre-trained weights)
    # We are forcing the model to learn ONLY aerial textures
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=IMG_SIZE + (3,), include_top=False, weights=None
    )
    base_model.trainable = True # Fully trainable from the start

    inputs = keras.Input(shape=IMG_SIZE + (3,))
    x = data_augmentation(inputs)
    x = layers.Rescaling(1./255)(x) # Simple 0-1 scaling
    x = base_model(x)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.5)(x)
    outputs = layers.Dense(1, activation='sigmoid')(x)
    
    model = keras.Model(inputs, outputs)

    # Callback to stop if the model collapses or stops learning
    early_stop = tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

    model.compile(optimizer=keras.optimizers.Adam(learning_rate=0.0001),
                  loss='binary_crossentropy', metrics=['accuracy'])
    
    print("🚀 Training starting... This will be slower as it learns from scratch.")
    model.fit(train_ds, validation_data=val_ds, epochs=MAX_EPOCHS, callbacks=[early_stop])

    # SAVE
    model.save(f"{MODEL_NAME}.keras")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    with open(f"{MODEL_NAME}.tflite", 'wb') as f:
        f.write(converter.convert())
    print("✅ TFLite Exported.")

if __name__ == "__main__":
    main()
