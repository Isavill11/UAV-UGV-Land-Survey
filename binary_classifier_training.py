import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.models import Sequential
import matplotlib.pyplot as plt
import os
import pathlib

# --- 1. Configuration ---

# TODO: Change this to point to your data directory
DATA_DIR = 'animal_data'
# TODO: Change this to the name you want for your final model
MODEL_NAME = 'animal_classifier'

# Model parameters
IMG_SIZE = (160, 160) # Input size for MobileNetV2
BATCH_SIZE = 32
EPOCHS = 10

def main():
    data_dir = pathlib.Path(DATA_DIR)
    
    # --- 2. Load Data ---
    print("Loading data...")
    # Create a training dataset (80% of the data)
    train_dataset = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=0.2,
        subset="training",
        seed=123,
        image_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        label_mode='binary' # Perfect for Yes/No (2 classes)
    )

    # Create a validation dataset (20% of the data)
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

    # Configure the dataset for high performance
    AUTOTUNE = tf.data.AUTOTUNE
    train_dataset = train_dataset.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
    validation_dataset = validation_dataset.cache().prefetch(buffer_size=AUTOTUNE)

    # --- 3. Build the Model ---
    print("Building model...")
    
    # Create a data augmentation layer
    data_augmentation = Sequential([
        layers.RandomFlip('horizontal'),
        layers.RandomRotation(0.2),
        layers.RandomZoom(0.2),
    ], name="data_augmentation")

    # Get the MobileNetV2 base model (pre-trained on ImageNet)
    # We set include_top=False to remove its original 1000-class classifier
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=IMG_SIZE + (3,),
        include_top=False,
        weights='imagenet'
    )
    
    # Freeze the base model so we only train our new layers
    base_model.trainable = False
    
    # This layer scales pixel values from [0, 255] to [-1, 1],
    # which is what MobileNetV2 was trained on.
    preprocess_input = tf.keras.applications.mobilenet_v2.preprocess_input

    # Create our new model
    inputs = keras.Input(shape=IMG_SIZE + (3,))
    x = data_augmentation(inputs)
    x = preprocess_input(x)
    x = base_model(x, training=False) # Run the base model in inference mode
    x = layers.GlobalAveragePooling2D()(x) # Pool the features
    x = layers.Dropout(0.2)(x) # Add dropout for regularization
    # Our final prediction layer: 1 neuron with a sigmoid activation
    # This will output a single number between 0 (class 0) and 1 (class 1)
    outputs = layers.Dense(1, activation='sigmoid')(x)
    
    model = keras.Model(inputs, outputs)

    # --- 4. Compile the Model ---
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.0001),
        loss=keras.losses.BinaryCrossentropy(),
        metrics=['accuracy']
    )
    
    model.summary()

    # --- 5. Train the Model ---
    print("Starting training...")
    history = model.fit(
        train_dataset,
        validation_data=validation_dataset,
        epochs=EPOCHS
    )

    # --- 6. Plot Training Results ---
    plot_history(history, f"{MODEL_NAME}_training_plot.png")

    # --- 7. Save the Final Keras Model ---
    keras_model_path = f"{MODEL_NAME}.keras"
    model.save(keras_model_path)
    print(f"Full Keras model saved to: {keras_model_path}")

    # --- 8. Convert and Save the TFLite Model ---
    print("Converting to TensorFlow Lite...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT] # Optimizes for size and speed
    tflite_model = converter.convert()
    
    tflite_model_path = f"{MODEL_NAME}.tflite"
    with open(tflite_model_path, 'wb') as f:
        f.write(tflite_model)
    print(f"TFLite model saved to: {tflite_model_path}")

def plot_history(history, save_path):
    """Plots the training and validation accuracy and loss."""
    acc = history.history['accuracy']
    val_acc = history.history['val_accuracy']
    loss = history.history['loss']
    val_loss = history.history['val_loss']

    plt.figure(figsize=(8, 8))
    plt.subplot(2, 1, 1)
    plt.plot(acc, label='Training Accuracy')
    plt.plot(val_acc, label='Validation Accuracy')
    plt.legend(loc='lower right')
    plt.ylabel('Accuracy')
    plt.title('Training and Validation Accuracy')

    plt.subplot(2, 1, 2)
    plt.plot(loss, label='Training Loss')
    plt.plot(val_loss, label='Validation Loss')
    plt.legend(loc='upper right')
    plt.ylabel('Cross Entropy')
    plt.title('Training and Validation Loss')
    plt.xlabel('epoch')
    
    plt.savefig(save_path)
    print(f"Training plot saved to: {save_path}")

if __name__ == '__main__':
    main()