# Copyright (c) OpenMMLab. All rights reserved.
import platform
from unittest.mock import patch

import pytest
import torch
from mmengine.optim import OptimWrapper
from torch.optim import Adam

from mmedit.models.data_preprocessors import EditDataPreprocessor
from mmedit.models.editors import (RealBasicVSR, RealBasicVSRNet,
                                   UNetDiscriminatorWithSpectralNorm)
from mmedit.models.losses import GANLoss, L1Loss, PerceptualLoss, PerceptualVGG
from mmedit.structures import EditDataSample, PixelData


@patch.object(PerceptualVGG, 'init_weights')
@pytest.mark.skipif(
    'win' in platform.system().lower() and 'cu' in torch.__version__,
    reason='skip on windows-cuda due to limited RAM.')
def test_real_basicvsr(init_weights):

    model = RealBasicVSR(
        generator=dict(
            type='RealBasicVSRNet',
            mid_channels=4,
            num_propagation_blocks=1,
            num_cleaning_blocks=1,
            dynamic_refine_thres=5,  # change to 5 for test
            spynet_pretrained=None,
            is_fix_cleaning=False,
            is_sequential_cleaning=False),
        discriminator=dict(
            type='UNetDiscriminatorWithSpectralNorm',
            in_channels=3,
            mid_channels=4,
            skip_connection=True),
        pixel_loss=dict(type='L1Loss', loss_weight=1.0, reduction='mean'),
        cleaning_loss=dict(type='L1Loss', loss_weight=1.0, reduction='mean'),
        perceptual_loss=dict(
            type='PerceptualLoss',
            layer_weights={
                '2': 0.1,
                '7': 0.1,
                '16': 1.0,
                '25': 1.0,
                '34': 1.0,
            },
            vgg_type='vgg19',
            perceptual_weight=1.0,
            style_weight=0,
            norm_img=False),
        gan_loss=dict(
            type='GANLoss',
            gan_type='vanilla',
            loss_weight=5e-2,
            real_label_val=1.0,
            fake_label_val=0),
        is_use_sharpened_gt_in_pixel=True,
        is_use_sharpened_gt_in_percep=True,
        is_use_sharpened_gt_in_gan=False,
        data_preprocessor=EditDataPreprocessor())

    assert isinstance(model, RealBasicVSR)
    assert isinstance(model.generator, RealBasicVSRNet)
    assert isinstance(model.discriminator, UNetDiscriminatorWithSpectralNorm)
    assert isinstance(model.pixel_loss, L1Loss)
    assert isinstance(model.cleaning_loss, L1Loss)
    assert isinstance(model.perceptual_loss, PerceptualLoss)
    assert isinstance(model.gan_loss, GANLoss)

    optimizer_g = Adam(
        model.generator.parameters(), lr=0.0001, betas=(0.9, 0.999))
    optimizer_d = Adam(
        model.discriminator.parameters(), lr=0.0001, betas=(0.9, 0.999))
    optim_wrapper = dict(
        generator=OptimWrapper(optimizer_g),
        discriminator=OptimWrapper(optimizer_d))

    # prepare data
    inputs = torch.rand(1, 5, 3, 64, 64)
    target = torch.rand(5, 3, 256, 256)
    data_sample = EditDataSample(
        gt_img=PixelData(data=target), gt_unsharp=PixelData(data=target))
    data = dict(inputs=inputs, data_samples=[data_sample])

    # train
    log_vars = model.train_step(data, optim_wrapper)
    assert isinstance(log_vars, dict)
    assert set(log_vars.keys()) == set([
        'loss_gan', 'loss_pix', 'loss_perceptual', 'loss_clean', 'loss_d_real',
        'loss_d_fake'
    ])

    # val
    output = model.val_step(data)
    assert output[0].output.pred_img.data.shape == (5, 3, 256, 256)

    # feat
    output = model(torch.rand(1, 5, 3, 64, 64), mode='tensor')
    assert output.shape == (1, 5, 3, 256, 256)

    # train_unsharp
    model.is_use_sharpened_gt_in_pixel = True
    model.is_use_sharpened_gt_in_percep = True
    model.is_use_sharpened_gt_in_gan = False
    log_vars = model.train_step(data, optim_wrapper)
    assert isinstance(log_vars, dict)
    assert set(log_vars.keys()) == set([
        'loss_gan', 'loss_pix', 'loss_perceptual', 'loss_clean', 'loss_d_real',
        'loss_d_fake'
    ])

    # reset mock to clear some memory usage
    init_weights.reset_mock()
