# -*- coding: utf-8 -*-
# This file is part of the APSimulator API.
# Author: Lars Frogner
import numpy as np


def perform_liear_stretch(image, black_point, white_point):
    '''
    Perform a linear stretch to make the "black_point" pixel values black
    and the "white_point" pixel values white. The returned image has
    values in the range [0, 1].
    '''
    return (image - black_point)/(white_point - black_point)


def perform_histogram_clip(image, black_point_scale=1, white_point_scale=1):
    return perform_liear_stretch(image, np.min(image)*black_point_scale, np.max(image)*white_point_scale)


def perform_midtone_stretch(image, midtones_balance):
    '''
    Stretch the image using the midtones transfer function. Assumes the
    image levels to be beteween 0 and 1. The midtones balance parameter
    specifies the level that will be stretched to 0.5.
    '''
    return (midtones_balance - 1)*image/((2*midtones_balance - 1)*image - midtones_balance)


def perform_autostretch(image, new_mean=0.25):
    '''
    Returns a clipped and stretched image where the new mean is at the given
    gray level (25% by default).
    '''
    # Clip both ends of histogram (also gets scaled to to the range [0, 1])
    clipped_image = perform_histogram_clip(image)

    # Stretch the image to bring the new mean level to the given value
    mean = np.mean(clipped_image)
    midtones_balance = perform_midtone_stretch(mean, new_mean)
    stretched_image = perform_midtone_stretch(clipped_image, midtones_balance)

    return stretched_image


def perform_fast_gamma_correction(image):
    clipped_image = perform_histogram_clip(image)
    return np.sqrt(clipped_image) # gamma = 1/2


def perform_gamma_correction(image, gamma=1/2.2):
    clipped_image = perform_histogram_clip(image)
    return perform_fast_gamma_correction(image) if gamma == 0.5 else clipped_image**gamma
