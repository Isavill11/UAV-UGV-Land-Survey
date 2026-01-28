import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.models import Sequential
import matplotlib.pyplot as plt
import os
import pathlib

# --- 1. Configuration ---
DATA_DIR = 'images'
MODEL_NAME = 'animal_binary_classifier'

IMG_SIZE = (224, 224) 
BATCH_SIZE = 32
EPOCHS = 10

def main():
    data_dir = pathlib.Path(DATA_DIR)
    
    # --- 2. Load Data ---
    print("Loading data...")
    train_dataset = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=0.2,
        subset="training",
        seed=123,
        image_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        label_mode='binary'
    )

    validation_dataset = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=0.2,
        subset="validation",
        seed=123,
        image_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        label_mode='binary'
    )
    
    class_names = train_dataset.class_names
    print(f"Found classes: {class_names}")

    # --- 3. Augmentation & Performance ---
    AUTOTUNE = tf.data.AUTOTUNE

    # Data Augmentation (Applied only to training data)
    data_augmentation = Sequential([
        layers.RandomFlip('horizontal'),
        layers.RandomRotation(0.2),
        layers.RandomZoom(0.2),
    ])

    train_dataset = train_dataset.map(lambda x, y: (data_augmentation(x, training=True), y), 
                                      num_parallel_calls=AUTOTUNE)
    
    train_dataset = train_dataset.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
    validation_dataset = validation_dataset.cache().prefetch(buffer_size=AUTOTUNE)

    # --- 4. Build the Model ---
    print("Building model...")
    
    # Get MobileNetV2 base
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=IMG_SIZE + (3,),
        include_top=False,
        weights='imagenet'
    )
    base_model.trainable = False 

    # MobileNetV2 specific preprocessing
    preprocess_input = tf.keras.applications.mobilenet_v2.preprocess_input

    inputs = keras.Input(shape=IMG_SIZE + (3,))
    x = preprocess_input(inputs)
    x = base_model(x, training=False) 
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.2)(x)
    outputs = layers.Dense(1, activation='sigmoid')(x)
    
    model = keras.Model(inputs, outputs)

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.0001),
        loss=keras.losses.BinaryCrossentropy(),
        metrics=['accuracy']
    )
    
    model.summary()

    # --- 5. Train ---
    print("Starting training...")
    history = model.fit(
        train_dataset,
        validation_data=validation_dataset,
        epochs=EPOCHS
    )

    # --- 6. Save & Convert ---
    plot_history(history, f"{MODEL_NAME}_training_plot.png")

    # Save as .keras
    model.save(f"{MODEL_NAME}.keras")
    
    # Convert to TFLite with Dynamic Range Quantization
    print("Converting to TFLite...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT] 
    tflite_model = converter.convert()
    
    with open(f"{MODEL_NAME}.tflite", 'wb') as f:
        f.write(tflite_model)
    print(f"✅ Deployment-ready model saved: {MODEL_NAME}.tflite")

def plot_history(history, save_path):
    # (Same as your original plot_history function)
    acc = history.history['accuracy']
    val_acc = history.history['val_accuracy']
    loss = history.history['loss']
    val_loss = history.history['val_loss']
    plt.figure(figsize=(8, 8))
    plt.subplot(2, 1, 1)
    plt.plot(acc, label='Training')
    plt.plot(val_acc, label='Validation')
    plt.title('Accuracy')
    plt.subplot(2, 1, 2)
    plt.plot(loss, label='Training')
    plt.plot(val_loss, label='Validation')
    plt.title('Loss')
    plt.savefig(save_path)

if __name__ == '__main__':
    main()
