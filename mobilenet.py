# -*- coding: utf-8 -*-
"""MobileNet.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1vFuMSl0CXpr2oRhjFKf4boi9pbgpNwM7
"""

from google.colab import files, drive
import numpy as np
import glob
import matplotlib.pyplot as plt
from tensorflow import keras
import os
from keras.models import Model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.applications.mobilenet import MobileNet, preprocess_input

from keras.preprocessing.image import ImageDataGenerator
from keras.callbacks import ModelCheckpoint, EarlyStopping
from keras.layers import Dense, Dropout, Flatten
from pathlib import Path

drive.mount('/content/drive')

! rm -r dataset_train
! rm -r dataset_test

!cp -r '/content/drive/My Drive/ML_dataset_tesi.zip' dataset.zip
!unzip dataset.zip -d content
! mv content/ML_dataset/train dataset_train
! mv content/ML_dataset/test dataset_test

! rm dataset.zip
! rm -r content

train_generator_plot = ImageDataGenerator(
    rescale=1/255.,              # normalize pixel values between 0-1
            # 180 degree flip vertically
    validation_split=0.20        # 15% of the data will be used for validation at end of each epoch
)

test_generator_plot = ImageDataGenerator(rescale=1/255.)

BATCH_SIZE = 32
train_generator = ImageDataGenerator(rotation_range=0, 
                                     brightness_range=[0.3, 0.8],
                                     width_shift_range=0.7, 
                                     height_shift_range=0.7,
                                     horizontal_flip=False, 
                                     vertical_flip=False,# best performance
                                     validation_split=0.25,
                                     preprocessing_function=preprocess_input) # MobileNet preprocessing

test_generator = ImageDataGenerator(preprocessing_function=preprocess_input) # MobileNet preprocessing

traingen = train_generator.flow_from_directory('./dataset_train/',
                                               target_size=(224, 224),
                                               class_mode='categorical',
                                             
                                               subset='training',
                                               batch_size=BATCH_SIZE, 
                                               shuffle=True,
                                               seed=42)
traingen.shuffle
traingen_plot = train_generator_plot.flow_from_directory('./dataset_train/',
                                               target_size=(224, 224),
                                               class_mode='categorical',
                                             
                                               subset='training',
                                               batch_size=BATCH_SIZE, 
                                               shuffle=True,
                                               seed=42)
testgen_plot = test_generator_plot.flow_from_directory('./dataset_test',
                                             target_size=(224, 224),
                                             class_mode=None,
                                           
                                             batch_size=1,
                                             shuffle=False,
                                             seed=42)
testgen = test_generator.flow_from_directory('./dataset_test',
                                             target_size=(224, 224),
                                             class_mode=None,
                                           
                                             batch_size=1,
                                             shuffle=False,
                                             seed=42)

validgen = train_generator.flow_from_directory('./dataset_train/',
                                               target_size=(224, 224),
                                               class_mode='categorical',
                                               
                                               subset='validation',
                                               batch_size=BATCH_SIZE,
                                               shuffle=True,
                                               seed=42)
validgen.shuffle
validgen_plot = train_generator_plot.flow_from_directory('./dataset_train/',
                                               target_size=(224, 224),
                                               class_mode='categorical',
                                               color_mode="rgb",
                                               subset='validation',
                                               batch_size=BATCH_SIZE,
                                               shuffle=True,
                                               seed=42)

def create_model(input_shape, n_classes, optimizer='rmsprop', fine_tune=0):
    """
    Compiles a model integrated with VGG16 pretrained layers
    
    input_shape: tuple - the shape of input images (width, height, channels)
    n_classes: int - number of classes for the output layer
    optimizer: string - instantiated optimizer to use for training. Defaults to 'RMSProp'
    fine_tune: int - The number of pre-trained layers to unfreeze.
                If set to 0, all pretrained layers will freeze during training
    """
    
    # Pretrained convolutional layers are loaded using the Imagenet weights.
    # Include_top is set to False, in order to exclude the model's fully-connected layers.
    conv_base = MobileNet(include_top=False,
                     weights='imagenet', 
                     input_shape=input_shape)
    
    # Defines how many layers to freeze during training.
    # Layers in the convolutional base are switched from trainable to non-trainable
    # depending on the size of the fine-tuning parameter.
    if fine_tune > 0:
        for layer in conv_base.layers[:-fine_tune]:
            layer.trainable = False
    else:
        for layer in conv_base.layers:
            layer.trainable = False

    # Create a new 'top' of the model (i.e. fully-connected layers).
    # This is 'bootstrapping' a new top_model onto the pretrained layers.
    top_model = conv_base.output
    top_model = Flatten(name="flatten")(top_model)
    top_model = Dense(2064, activation='relu')(top_model)
    top_model = Dense(1072, activation='relu')(top_model)
    top_model = Dropout(0.2)(top_model)
    output_layer = Dense(n_classes, activation='softmax')(top_model)
    
    # Group the convolutional base and new fully-connected layers into a Model object.
    model = Model(inputs=conv_base.input, outputs=output_layer)

    # Compiles the model for training.
    model.compile(optimizer=optimizer, 
                  loss='categorical_crossentropy',
                  metrics=['accuracy'])
    
    return model

input_shape = (224, 224, 3)

n_classes=4

n_steps = traingen.samples // BATCH_SIZE
n_val_steps = validgen.samples // BATCH_SIZE
n_epochs = 50

!pip install livelossplot --quiet

from livelossplot.inputs.keras import PlotLossesCallback


plot_loss_1 = PlotLossesCallback()

# ModelCheckpoint callback - save best weights
tl_checkpoint_1 = ModelCheckpoint(filepath='tl_model_v1.weights.best.hdf5',
                                  save_best_only=True,
                                  verbose=1)

# EarlyStopping (patience: Number of epochs with no improvement after which training will be stopped.)
early_stop = EarlyStopping(monitor='val_loss',
                           patience=7,
                           restore_best_weights=True,
                           mode='min')

# Use a smaller learning rate
optim_2 = Adam(learning_rate=0.0001)

# Re-compile the model, this time leaving the last 2 layers unfrozen for Fine-Tuning
rnet_model_ft = create_model(input_shape, n_classes, optim_2, fine_tune=30)

# Commented out IPython magic to ensure Python compatibility.
# %%time
# 
# plot_loss_2 = PlotLossesCallback()
# 
# # Retrain model with fine-tuning
# rnet_ft_history = rnet_model_ft.fit(traingen,
#                                   batch_size=BATCH_SIZE,
#                                   epochs=n_epochs,
#                                   validation_data=validgen,
#                                   steps_per_epoch=n_steps, 
#                                   validation_steps=n_val_steps,
#                                   callbacks=[tl_checkpoint_1, early_stop, plot_loss_2],
#                                   verbose=1)

rnet_model_ft.load_weights('tl_model_v1.weights.best.hdf5')

rnet_preds_ft = rnet_model_ft.predict(testgen)
rnet_pred_classes_ft  = np.argmax(rnet_preds_ft, axis=1)

class_indices = traingen.class_indices
class_indices = dict((v,k) for k,v in class_indices.items())
true_classes = testgen.classes

#catch a few image of train_generator.
def traingenplot(traingen):
    x_batch, y_batch = next(traingen)
    x_batch = x_batch[:16]
    y_batch = y_batch[:16]
    fig = plt.figure(figsize=(12, 9))
    for k, (img, lbl) in enumerate(zip(x_batch, y_batch)):
            
            ax = fig.add_subplot(4, 4, k + 1, yticks=[])
            ax.imshow(img)
            y_predetta = np.argmax(lbl)
          
            predizione = (list(traingen.class_indices.keys())[list(traingen.class_indices.values()).index(y_predetta)])#Basically, it separates the dictionary's values in a list, finds the position of the value you have, and gets the key at that position.
            true_idx =predizione
            ax.axis('off')       
          
            ax.set_title(predizione)

import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_fscore_support, accuracy_score

def display_results(y_true, y_preds, class_labels):
    
    results = pd.DataFrame(precision_recall_fscore_support(y_true, y_preds),
                          columns=class_labels).T

    results.rename(columns={0: 'Precision', 1: 'Recall',
                            2: 'F-Score', 3: 'Support'}, inplace=True)
    
    results.sort_values(by='F-Score', ascending=False, inplace=True)                           
    global_acc = accuracy_score(y_true, y_preds)
    
    print("Overall Categorical Accuracy: {:.2f}%".format(global_acc*100))
    return results

def plot_predictions(y_true, y_preds, test_generator_plot, class_indices):

    fig = plt.figure(figsize=(20, 10))
    for i, idx in enumerate(np.random.choice(test_generator_plot.samples, size=20, replace=False)):
        ax = fig.add_subplot(5, 4, i + 1, xticks=[], yticks=[])
        ax.imshow(np.squeeze(test_generator_plot[idx]))
        pred_idx = y_preds[idx]
        true_idx = y_true[idx]
                
        plt.tight_layout()
        ax.set_title("{}\n({})".format(class_indices[pred_idx], class_indices[true_idx]),
                     color=("green" if pred_idx == true_idx else "red"))

plot_predictions(true_classes, rnet_pred_classes_ft, testgen_plot, class_indices)

rnet_acc_ft = accuracy_score(true_classes, rnet_pred_classes_ft)
print("ResNet50 Model Accuracy with Fine-Tuning: {:.2f}%".format(rnet_acc_ft * 100))

#CONFUSION MATRIX
from sklearn.metrics import confusion_matrix
import seaborn as sns
# Plot non-normalized confusion matrix
# Get the names of the ten classes
class_names = testgen.class_indices.keys()
def plot_heatmap(y_true, y_pred, class_names, ax, title):
    cm = confusion_matrix(y_true, y_pred)
    sns.heatmap(
        cm, 
        annot=True, 
        square=True, 
        xticklabels=class_names, 
        yticklabels=class_names,
        fmt='d', 
        cmap=plt.cm.Blues,
        cbar=False,
        ax=ax
    )
    ax.set_title(title, fontsize=16)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
    ax.set_ylabel('True Label', fontsize=12)
    ax.set_xlabel('Predicted Label', fontsize=12)
fig, (ax1) = plt.subplots(1, 1, figsize=(20, 10))
plot_heatmap(true_classes, rnet_pred_classes_ft, class_names, ax1, title="Transfer Learning (MobileNet) with Fine-Tuning")    

fig.tight_layout()
fig.subplots_adjust(top=1.25)
plt.show()