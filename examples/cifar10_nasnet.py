"""
Adapted from keras example cifar10_cnn.py
Train NASNet-CIFAR on the CIFAR10 small images dataset.
GPU run command with Theano backend (with TensorFlow, the GPU is automatically used):
    THEANO_FLAGS=mode=FAST_RUN,device=gpu,floatX=float32 python cifar10_nasnet.py
"""
from __future__ import print_function
from keras.datasets import cifar10
from keras.preprocessing.image import ImageDataGenerator
from keras.utils import np_utils
from keras.callbacks import ModelCheckpoint
from keras.callbacks import ReduceLROnPlateau
from keras.callbacks import CSVLogger
from keras.optimizers import Adam
from keras_contrib.applications.nasnet import NASNetCIFAR, preprocess_input

import numpy as np


weights_file = 'NASNet-CIFAR-10.h5'
lr_reducer = ReduceLROnPlateau(factor=np.sqrt(0.5), cooldown=0, patience=5, min_lr=0.5e-5)
csv_logger = CSVLogger('NASNet-CIFAR-10.csv')
model_checkpoint = ModelCheckpoint(weights_file, monitor='val_prediction_acc', save_best_only=True,
                                   save_weights_only=True, mode='max')

batch_size = 128
nb_classes = 10
nb_epoch = 200 # should be 600
data_augmentation = True

# input image dimensions
img_rows, img_cols = 32, 32
# The CIFAR10 images are RGB.
img_channels = 3

# The data, shuffled and split between train and test sets:
(X_train, y_train), (X_test, y_test) = cifar10.load_data()

# Convert class vectors to binary class matrices.
Y_train = np_utils.to_categorical(y_train, nb_classes)
Y_test = np_utils.to_categorical(y_test, nb_classes)

X_train = X_train.astype('float32')
X_test = X_test.astype('float32')

# preprocess input
X_train = preprocess_input(X_train)
X_test = preprocess_input(X_test)

# For training, the auxilary branch must be used to correctly train NASNet
model = NASNetCIFAR((img_rows, img_cols, img_channels), use_auxilary_branch=True)
model.summary()

optimizer = Adam(lr=1e-3, clipnorm=5)
model.compile(loss=['categorical_crossentropy', 'categorical_crossentropy'],
              optimizer=optimizer, metrics=['accuracy'], loss_weights=[1.0, 0.4])

if not data_augmentation:
    print('Not using data augmentation.')
    model.fit(X_train, Y_train,
              batch_size=batch_size,
              nb_epoch=nb_epoch,
              validation_data=(X_test, Y_test),
              shuffle=True,
              verbose=2,
              callbacks=[lr_reducer, csv_logger, model_checkpoint])
else:
    print('Using real-time data augmentation.')
    # This will do preprocessing and realtime data augmentation:
    datagen = ImageDataGenerator(
        featurewise_center=False,  # set input mean to 0 over the dataset
        samplewise_center=False,  # set each sample mean to 0
        featurewise_std_normalization=False,  # divide inputs by std of the dataset
        samplewise_std_normalization=False,  # divide each input by its std
        zca_whitening=False,  # apply ZCA whitening
        rotation_range=0,  # randomly rotate images in the range (degrees, 0 to 180)
        width_shift_range=0.1,  # randomly shift images horizontally (fraction of total width)
        height_shift_range=0.1,  # randomly shift images vertically (fraction of total height)
        horizontal_flip=True,  # randomly flip images
        vertical_flip=False)  # randomly flip images

    # Compute quantities required for featurewise normalization
    # (std, mean, and principal components if ZCA whitening is applied).
    datagen.fit(X_train)

    # Fit the model on the batches generated by datagen.flow().
    model.fit_generator(datagen.flow(X_train, Y_train, batch_size=batch_size),
                        steps_per_epoch=X_train.shape[0] // batch_size,
                        validation_data=(X_test, Y_test),
                        epochs=nb_epoch, verbose=2,
                        callbacks=[lr_reducer, csv_logger, model_checkpoint])

scores = model.evaluate(X_test, Y_test, batch_size=batch_size)
for score, metric_name in zip(scores, model.metrics_names):
    print("%s : %0.4f" % (metric_name, score))
