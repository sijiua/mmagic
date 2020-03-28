import copy

import numpy as np
import pytest
from mmedit.datasets.pipelines import (BinarizeImage, Flip, Pad, RandomAffine,
                                       RandomJitter, RandomMaskDilation,
                                       RandomTransposeHW, Resize)


class TestAugmentations(object):

    @classmethod
    def setup_class(cls):
        cls.results = dict()
        cls.img_gt = np.random.rand(256, 128, 3).astype(np.float32)
        cls.img_lq = np.random.rand(64, 32, 3).astype(np.float32)

        cls.results = dict(
            lq=cls.img_lq,
            gt=cls.img_gt,
            scale=4,
            lq_path='fake_lq_path',
            gt_path='fake_gt_path')

        cls.results['img'] = np.random.rand(256, 256, 3).astype(np.float32)
        cls.results['mask'] = np.random.rand(256, 256, 1).astype(np.float32)

    @staticmethod
    def assert_img_equal(img, ref_img, ratio_thr=0.999):
        """Check if img and ref_img are matched approximatively."""
        assert img.shape == ref_img.shape
        assert img.dtype == ref_img.dtype
        area = ref_img.shape[-1] * ref_img.shape[-2]
        diff = np.abs(img.astype('int32') - ref_img.astype('int32'))
        assert np.sum(diff <= 1) / float(area) > ratio_thr

    @staticmethod
    def check_keys_contain(result_keys, target_keys):
        """Check if all elements in target_keys is in result_keys."""
        return set(target_keys).issubset(set(result_keys))

    @staticmethod
    def check_flip(origin_img, result_img, flip_type):
        """Check if the origin_img are flipped correctly into result_img
        in different flip_types"""
        h, w, c = origin_img.shape
        if flip_type == 'horizontal':
            # yapf: disable
            for i in range(h):
                for j in range(w):
                    for k in range(c):
                        if result_img[i, j, k] != origin_img[i, w - 1 - j, k]:
                            return False
            # yapf: enable
        else:
            # yapf: disable
            for i in range(h):
                for j in range(w):
                    for k in range(c):
                        if result_img[i, j, k] != origin_img[h - 1 - i, j, k]:
                            return False
            # yapf: enable
        return True

    def test_binarize(self):
        mask_ = np.zeros((5, 5, 1))
        mask_[2, 2, :] = 0.6
        gt_mask = mask_.copy()
        gt_mask[2, 2, :] = 1.
        results = dict(mask=mask_.copy())
        binarize = BinarizeImage(['mask'], 0.5, to_int=False)
        results = binarize(results)
        assert np.array_equal(results['mask'], gt_mask.astype(np.float32))

        results = dict(mask=mask_.copy())
        binarize = BinarizeImage(['mask'], 0.5, to_int=True)
        results = binarize(results)
        assert np.array_equal(results['mask'], gt_mask.astype(np.int32))
        assert str(binarize) == binarize.__class__.__name__ + \
            '(keys={}, binary_thr={}, to_int={})'.format(
            ['mask'], 0.5, True)

    def test_flip(self):
        results = copy.deepcopy(self.results)

        with pytest.raises(ValueError):
            Flip(keys=['lq', 'gt'], direction='vertically')

        # horizontal
        np.random.seed(1)
        target_keys = ['lq', 'gt', 'flip', 'flip_direction']
        flip = Flip(keys=['lq', 'gt'], flip_ratio=1, direction='horizontal')
        results = flip(results)
        assert self.check_keys_contain(results.keys(), target_keys)
        assert self.check_flip(self.img_lq, results['lq'],
                               results['flip_direction'])
        assert self.check_flip(self.img_gt, results['gt'],
                               results['flip_direction'])
        assert results['lq'].shape == self.img_lq.shape
        assert results['gt'].shape == self.img_gt.shape

        # vertical
        results = copy.deepcopy(self.results)
        flip = Flip(keys=['lq', 'gt'], flip_ratio=1, direction='vertical')
        results = flip(results)
        assert self.check_keys_contain(results.keys(), target_keys)
        assert self.check_flip(self.img_lq, results['lq'],
                               results['flip_direction'])
        assert self.check_flip(self.img_gt, results['gt'],
                               results['flip_direction'])
        assert results['lq'].shape == self.img_lq.shape
        assert results['gt'].shape == self.img_gt.shape
        assert repr(flip) == flip.__class__.__name__ + (
            f"(keys={['lq', 'gt']}, flip_ratio=1, "
            f"direction={results['flip_direction']})")

    def test_pad(self):
        target_keys = ['alpha', 'img_shape']

        alpha = np.random.rand(319, 321).astype(np.float32)
        results = dict(alpha=alpha, img_shape=(319, 321))
        pad = Pad(keys=['alpha'], ds_factor=32, mode='constant')
        pad_results = pad(results)
        assert self.check_keys_contain(pad_results.keys(), target_keys)
        assert pad_results['alpha'].shape == (320, 352)
        assert self.check_pad(alpha, results['alpha'], 'constant')

        alpha = np.random.rand(319, 321).astype(np.float32)
        results = dict(alpha=alpha, img_shape=(319, 321))
        pad = Pad(keys=['alpha'], ds_factor=32, mode='reflect')
        pad_results = pad(results)
        assert self.check_keys_contain(pad_results.keys(), target_keys)
        assert pad_results['alpha'].shape == (320, 352)
        assert self.check_pad(alpha, results['alpha'], 'reflect')

        alpha = np.random.rand(320, 320).astype(np.float32)
        results = dict(alpha=alpha, img_shape=(320, 320))
        pad = Pad(keys=['alpha'], ds_factor=32, mode='reflect')
        pad_results = pad(results)
        assert self.check_keys_contain(pad_results.keys(), target_keys)
        assert pad_results['alpha'].shape == (320, 320)
        assert self.check_pad(alpha, results['alpha'], 'reflect')

        assert repr(pad) == pad.__class__.__name__ + (
            f"(keys={['alpha']}, ds_factor=32, mode={'reflect'})")

    @staticmethod
    def check_pad(origin_img, result_img, mode, ds_factor=32):
        """Check if the origin_img is padded correctly.

        Supported modes for checking are 'constant' (with 'constant_values' of
        0) and 'reflect'.
        Supported images should be 2 dimentional.
        """
        if mode not in ['constant', 'reflect']:
            raise NotImplementedError(
                f'Pad checking of mode {mode} is not implemented.')
        assert len(origin_img.shape) == 2, f'Image should be 2 dimentional.'

        h, w = origin_img.shape
        new_h = ds_factor * (h - 1) // ds_factor + 1
        new_w = ds_factor * (w - 1) // ds_factor + 1

        # check the bottom rectangle
        for i in range(h, new_h):
            for j in range(0, w):
                target = origin_img[h - i, j] if mode == 'reflect' else 0
                if result_img[i, j] != target:
                    return False

        # check the right rectangle
        for i in range(0, h):
            for j in range(w, new_w):
                target = origin_img[i, w - j] if mode == 'reflect' else 0
                if result_img[i, j] != target:
                    return False

        # check the bottom right rectangle
        for i in range(h, new_h):
            for j in range(w, new_w):
                target = origin_img[h - i, w - j] if mode == 'reflect' else 0
                if result_img[i, j] != target:
                    return False

        return True

    def test_random_affine(self):
        with pytest.raises(AssertionError):
            RandomAffine(None, -1)

        with pytest.raises(AssertionError):
            RandomAffine(None, 0, translate='Not a tuple')

        with pytest.raises(AssertionError):
            RandomAffine(None, 0, translate=(0, 0, 0))

        with pytest.raises(AssertionError):
            RandomAffine(None, 0, translate=(0, 2))

        with pytest.raises(AssertionError):
            RandomAffine(None, 0, scale='Not a tuple')

        with pytest.raises(AssertionError):
            RandomAffine(None, 0, scale=(0.8, 1., 1.2))

        with pytest.raises(AssertionError):
            RandomAffine(None, 0, scale=(-0.8, 1.))

        with pytest.raises(AssertionError):
            RandomAffine(None, 0, shear=-1)

        with pytest.raises(AssertionError):
            RandomAffine(None, 0, shear=(0, 1, 2))

        with pytest.raises(AssertionError):
            RandomAffine(None, 0, flip_ratio='Not a float')

        target_keys = ['fg', 'alpha']

        # test random affine with different valid setting combinations
        alpha = np.random.rand(240, 320).astype(np.float32)
        fg = np.random.rand(240, 320).astype(np.float32)
        results = dict(alpha=alpha, fg=fg, img_shape=(240, 320))
        random_affine = RandomAffine(['fg', 'alpha'],
                                     degrees=30,
                                     translate=(0, 1),
                                     shear=(10, 20),
                                     flip_ratio=0.5)
        random_affine_results = random_affine(results)
        assert self.check_keys_contain(random_affine_results.keys(),
                                       target_keys)
        assert random_affine_results['fg'].shape == (240, 320)
        assert random_affine_results['alpha'].shape == (240, 320)

        alpha = np.random.rand(240, 320).astype(np.float32)
        fg = np.random.rand(240, 320).astype(np.float32)
        results = dict(alpha=alpha, fg=fg, img_shape=(240, 320))
        random_affine = RandomAffine(['fg', 'alpha'],
                                     degrees=(-30, 30),
                                     scale=(0.8, 1.25),
                                     shear=10,
                                     flip_ratio=0.5)
        random_affine_results = random_affine(results)
        assert self.check_keys_contain(random_affine_results.keys(),
                                       target_keys)
        assert random_affine_results['fg'].shape == (240, 320)
        assert random_affine_results['alpha'].shape == (240, 320)

        alpha = np.random.rand(240, 320).astype(np.float32)
        fg = np.random.rand(240, 320).astype(np.float32)
        results = dict(alpha=alpha, fg=fg, img_shape=(240, 320))
        random_affine = RandomAffine(['fg', 'alpha'], degrees=30)
        random_affine_results = random_affine(results)
        assert self.check_keys_contain(random_affine_results.keys(),
                                       target_keys)
        assert random_affine_results['fg'].shape == (240, 320)
        assert random_affine_results['alpha'].shape == (240, 320)

        assert repr(random_affine) == random_affine.__class__.__name__ + (
            f'(keys={target_keys}, degrees={(-30, 30)}, '
            f'translate={None}, scale={None}, '
            f'shear={None}, flip_ratio={0})')

    def test_random_jitter(self):
        with pytest.raises(AssertionError):
            RandomJitter(-40)

        with pytest.raises(AssertionError):
            RandomJitter((-40, 40, 40))

        target_keys = ['fg']

        fg = np.random.rand(240, 320, 3).astype(np.float32)
        alpha = np.random.rand(240, 320).astype(np.float32)
        results = dict(fg=fg.copy(), alpha=alpha)
        random_jitter = RandomJitter(40)
        random_jitter_results = random_jitter(results)
        assert self.check_keys_contain(random_jitter_results.keys(),
                                       target_keys)
        assert random_jitter_results['fg'].shape == (240, 320, 3)

        fg = np.random.rand(240, 320, 3).astype(np.float32)
        alpha = np.random.rand(240, 320).astype(np.float32)
        results = dict(fg=fg.copy(), alpha=alpha)
        random_jitter = RandomJitter((-50, 50))
        random_jitter_results = random_jitter(results)
        assert self.check_keys_contain(random_jitter_results.keys(),
                                       target_keys)
        assert random_jitter_results['fg'].shape == (240, 320, 3)

        assert repr(random_jitter) == random_jitter.__class__.__name__ + (
            f'hue_range=(-50, 50)')

    @staticmethod
    def check_transposehw(origin_img, result_img):
        """Check if the origin_imgs are transposed correctly"""
        h, w, c = origin_img.shape
        # yapf: disable
        for i in range(c):
            for j in range(h):
                for k in range(w):
                    if result_img[k, j, i] != origin_img[j, k, i]:  # noqa:E501
                        return False
            # yapf: enable
        return True

    def test_transposehw(self):
        results = self.results.copy()
        target_keys = ['lq', 'gt', 'transpose']
        transposehw = RandomTransposeHW(keys=['lq', 'gt'], transpose_ratio=1)
        results = transposehw(results)
        assert self.check_keys_contain(results.keys(), target_keys)
        assert self.check_transposehw(self.img_lq, results['lq'])
        assert self.check_transposehw(self.img_gt, results['gt'])
        assert results['lq'].shape == (32, 64, 3)
        assert results['gt'].shape == (128, 256, 3)

        assert repr(transposehw) == transposehw.__class__.__name__ + (
            f"(keys={['lq', 'gt']}, transpose_ratio=1)")

    def test_random_dilation(self):
        mask = np.zeros((3, 3, 1), dtype=np.float32)
        mask[1, 1] = 1
        gt_mask = np.ones_like(mask)
        results = dict(mask=mask.copy())
        dilation = RandomMaskDilation(['mask'],
                                      binary_thr=0.5,
                                      kernel_min=3,
                                      kernel_max=3)
        results = dilation(results)
        assert np.array_equal(results['mask'], gt_mask)
        assert results['mask_dilate_kernel_size'] == 3
        assert str(dilation) == dilation.__class__.__name__ + \
            '(keys={}, kernel_min={}, kernel_max={})'. \
            format(['mask'], 3, 3)

    def test_resize(self):
        with pytest.raises(AssertionError):
            Resize([], scale=0.5)
        with pytest.raises(AssertionError):
            Resize(['gt_img'], size_factor=32, scale=0.5)
        with pytest.raises(AssertionError):
            Resize(['gt_img'], size_factor=32, keep_ratio=True)
        with pytest.raises(AssertionError):
            Resize(['gt_img'], max_size=32, size_factor=None)
        with pytest.raises(ValueError):
            Resize(['gt_img'], scale=-0.5)
        with pytest.raises(TypeError):
            Resize(['gt_img'], (0.4, 0.2))
        with pytest.raises(TypeError):
            Resize(['gt_img'], dict(test=None))

        target_keys = ['alpha', 'img_shape']

        alpha = np.random.rand(240, 320).astype(np.float32)
        results = dict(alpha=alpha)
        resize = Resize(keys=['alpha'], size_factor=32, max_size=None)
        resize_results = resize(results)
        assert self.check_keys_contain(resize_results.keys(), target_keys)
        assert resize_results['alpha'].shape == (224, 320, 1)
        resize = Resize(keys=['alpha'], size_factor=32, max_size=320)
        resize_results = resize(results)
        assert self.check_keys_contain(resize_results.keys(), target_keys)
        assert resize_results['alpha'].shape == (224, 320, 1)

        resize = Resize(keys=['alpha'], size_factor=32, max_size=200)
        resize_results = resize(results)
        assert self.check_keys_contain(resize_results.keys(), target_keys)
        assert resize_results['alpha'].shape == (192, 192, 1)

        resize = Resize(['gt_img'], (-1, 200))
        assert resize.scale == (np.inf, 200)

        results = dict(gt_img=self.results['img'].copy())
        resize_keep_ratio = Resize(['gt_img'], scale=0.5, keep_ratio=True)
        results = resize_keep_ratio(results)
        assert results['gt_img'].shape[:2] == (128, 128)
        assert results['scale_factor'] == 0.5

        results = dict(gt_img=self.results['img'].copy())
        resize_keep_ratio = Resize(['gt_img'],
                                   scale=(128, 128),
                                   keep_ratio=False)
        results = resize_keep_ratio(results)
        assert results['gt_img'].shape[:2] == (128, 128)

        # test input with shape (256, 256)
        results = dict(gt_img=self.results['img'][..., 0].copy())
        resize = Resize(['gt_img'], scale=(128, 128), keep_ratio=False)
        results = resize(results)
        assert results['gt_img'].shape == (128, 128, 1)

        name_ = str(resize_keep_ratio)
        print(name_)
        assert name_ == resize_keep_ratio.__class__.__name__ + (
            f"(keys={['gt_img']}, scale=(128, 128), "
            f'keep_ratio={False}, size_factor=None, '
            f'max_size=None,interpolation=bilinear)')