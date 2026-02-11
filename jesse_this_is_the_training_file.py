import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

def train_balanced_classifier():
    # Load tiled data
    train_ds = tf.keras.utils.image_dataset_from_directory(
        'images', validation_split=0.2, subset="training", seed=123,
        image_size=(224, 224), batch_size=32, label_mode='binary'
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        'images', validation_split=0.2, subset="validation", seed=123,
        image_size=(224, 224), batch_size=32, label_mode='binary'
    )

    # 1. Base Model (Fixed Features)
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(224, 224, 3), include_top=False, weights='imagenet'
    )
    base_model.trainable = False 

    # 2. Modern Architecture
    model = keras.Sequential([
        layers.Input(shape=(224, 224, 3)),
        layers.Rescaling(1./127.5, offset=-1), # MobileNetV2 Specific
        base_model,
        layers.GlobalAveragePooling2D(), # Prevents Overfitting
        layers.Dropout(0.5),
        layers.Dense(1, activation='sigmoid')
    ])

    # 3. Phase 1: Warming Up (Learning rate 1e-4)
    model.compile(optimizer=keras.optimizers.Adam(1e-4),
                  loss='binary_crossentropy', metrics=['accuracy'])
    model.fit(train_ds, validation_data=val_ds, epochs=10)

    # 4. Phase 2: Fine-Tuning (Unfreeze last 20 layers, learning rate 1e-5)
    base_model.trainable = True
    for layer in base_model.layers[:-20]: layer.trainable = False
    
    model.compile(optimizer=keras.optimizers.Adam(1e-5),
                  loss='binary_crossentropy', metrics=['accuracy'])
    model.fit(train_ds, validation_data=val_ds, epochs=20)

    model.save("survey_animal_classifier.keras")
    print("✅ High-Fidelity Model Trained.")

if __name__ == "__main__":
    train_balanced_classifier()
