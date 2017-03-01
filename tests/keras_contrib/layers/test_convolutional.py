import pytest
import numpy as np
import itertools
from numpy.testing import assert_allclose

from keras.utils.test_utils import layer_test, keras_test
from keras.utils.np_utils import conv_input_length
from keras import backend as K
from keras_contrib import backend as KC
from keras_contrib.layers import convolutional, pooling
from keras.models import Sequential

# TensorFlow does not support full convolution.
if K.backend() == 'theano':
    _convolution_border_modes = ['valid', 'same', 'full']
else:
    _convolution_border_modes = ['valid', 'same']


@keras_test
def test_deconvolution_3d():
    nb_samples = 6
    nb_filter = 4
    stack_size = 2
    kernel_dim1 = 12
    kernel_dim2 = 10
    kernel_dim3 = 8

    for batch_size in [None, nb_samples]:
        for border_mode in _convolution_border_modes:
            for subsample in [(1, 1, 1), (2, 2, 2)]:
                if border_mode == 'same' and subsample != (1, 1, 1):
                    continue

                dim1 = conv_input_length(kernel_dim1, 7, border_mode, subsample[0])
                dim2 = conv_input_length(kernel_dim2, 5, border_mode, subsample[1])
                dim3 = conv_input_length(kernel_dim3, 3, border_mode, subsample[2])
                layer_test(convolutional.Deconvolution3D,
                           kwargs={'nb_filter': nb_filter,
                                   'kernel_dim1': 7,
                                   'kernel_dim2': 5,
                                   'kernel_dim3': 3,
                                   'output_shape': (batch_size, nb_filter, dim1, dim2, dim3),
                                   'border_mode': border_mode,
                                   'subsample': subsample,
                                   'dim_ordering': 'th'},
                           input_shape=(nb_samples, stack_size, kernel_dim1, kernel_dim2, kernel_dim3),
                           fixed_batch_size=True)

                layer_test(convolutional.Deconvolution3D,
                           kwargs={'nb_filter': nb_filter,
                                   'kernel_dim1': 7,
                                   'kernel_dim2': 5,
                                   'kernel_dim3': 3,
                                   'output_shape': (batch_size, nb_filter, dim1, dim2, dim3),
                                   'border_mode': border_mode,
                                   'dim_ordering': 'th',
                                   'W_regularizer': 'l2',
                                   'b_regularizer': 'l2',
                                   'activity_regularizer': 'activity_l2',
                                   'subsample': subsample},
                           input_shape=(nb_samples, stack_size, kernel_dim1, kernel_dim2, kernel_dim3),
                           fixed_batch_size=True)

                layer_test(convolutional.Deconvolution3D,
                           kwargs={'nb_filter': nb_filter,
                                   'kernel_dim1': 7,
                                   'kernel_dim2': 5,
                                   'kernel_dim3': 3,
                                   'output_shape': (nb_filter, dim1, dim2, dim3),
                                   'border_mode': border_mode,
                                   'dim_ordering': 'th',
                                   'W_regularizer': 'l2',
                                   'b_regularizer': 'l2',
                                   'activity_regularizer': 'activity_l2',
                                   'subsample': subsample},
                           input_shape=(nb_samples, stack_size, kernel_dim1, kernel_dim2, kernel_dim3))


@keras_test
def test_cosineconvolution_2d():
    nb_samples = 2
    nb_filter = 2
    stack_size = 3
    nb_row = 10
    nb_col = 6

    if K.backend() == 'theano':
        dim_ordering = 'th'
    elif K.backend() == 'tensorflow':
        dim_ordering = 'tf'

    for border_mode in _convolution_border_modes:
        for subsample in [(1, 1), (2, 2)]:
            for bias_mode in [True, False]:
                if border_mode == 'same' and subsample != (1, 1):
                    continue

                layer_test(convolutional.CosineConvolution2D,
                           kwargs={'nb_filter': nb_filter,
                                   'nb_row': 3,
                                   'nb_col': 3,
                                   'border_mode': border_mode,
                                   'subsample': subsample,
                                   'bias': bias_mode,
                                   'dim_ordering': dim_ordering},
                           input_shape=(nb_samples, nb_row, nb_col, stack_size))

                layer_test(convolutional.CosineConvolution2D,
                           kwargs={'nb_filter': nb_filter,
                                   'nb_row': 3,
                                   'nb_col': 3,
                                   'border_mode': border_mode,
                                   'W_regularizer': 'l2',
                                   'b_regularizer': 'l2',
                                   'activity_regularizer': 'activity_l2',
                                   'subsample': subsample,
                                   'bias': bias_mode,
                                   'dim_ordering': dim_ordering},
                           input_shape=(nb_samples, nb_row, nb_col, stack_size))

    if dim_ordering == 'th':
        X = np.random.randn(1, 3, 5, 5)
        input_dim = (3, 5, 5)
        W0 = X[:, :, ::-1, ::-1]
    elif dim_ordering == 'tf':
        X = np.random.randn(1, 5, 5, 3)
        input_dim = (5, 5, 3)
        W0 = X[0, :, :, :, None]

    model = Sequential()
    model.add(convolutional.CosineConvolution2D(1, 5, 5, bias=True, input_shape=input_dim, dim_ordering=dim_ordering))
    model.compile(loss='mse', optimizer='rmsprop')
    W = model.get_weights()
    W[0] = W0
    W[1] = np.asarray([1.])
    model.set_weights(W)
    out = model.predict(X)
    assert_allclose(out, np.ones((1, 1, 1, 1), dtype=K.floatx()), atol=1e-5)

    model = Sequential()
    model.add(convolutional.CosineConvolution2D(1, 5, 5, bias=False, input_shape=input_dim, dim_ordering=dim_ordering))
    model.compile(loss='mse', optimizer='rmsprop')
    W = model.get_weights()
    W[0] = -2 * W0
    model.set_weights(W)
    out = model.predict(X)
    assert_allclose(out, -np.ones((1, 1, 1, 1), dtype=K.floatx()), atol=1e-5)


@keras_test
def test_sub_pixel_upscaling():
    nb_samples = 2
    nb_row = 16
    nb_col = 16

    for scale_factor in [2, 3, 4]:
        input_data = np.random.random((nb_samples, 4 * (scale_factor ** 2), nb_row, nb_col))

        if K.image_dim_ordering() == 'tf':
            input_data = input_data.transpose((0, 2, 3, 1))

        input_tensor = K.variable(input_data)
        expected_output = K.eval(KC.depth_to_space(input_tensor, scale=scale_factor))

        layer_test(convolutional.SubPixelUpscaling,
                   kwargs={'scale_factor': scale_factor},
                   input_data=input_data,
                   expected_output=expected_output,
                   expected_output_dtype=K.floatx())


if __name__ == '__main__':
    pytest.main([__file__])
