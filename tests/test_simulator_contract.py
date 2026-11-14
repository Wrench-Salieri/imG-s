#Run with:  python -m pytest tests   (from the project root; pip install pytest)
import math

import numpy as np
import pytest

from mri.parameters import DEFAULTS, PARAMS, REQUIRED_METRIC_KEYS
from mri.phantom import head_phantom
from mri.simulator import SpaceMRISimulator                      # noqa: E402


def _simulate(seed=0, **overrides):
    np.random.seed(seed)
    simulator = SpaceMRISimulator(head_phantom(64, 208.0))
    try:
        return simulator.simulate(**{**DEFAULTS, **overrides})
    except NotImplementedError:
        pytest.skip("simulate() is not written yet")


def test_parameter_defaults_are_inside_their_ranges():
    for p in PARAMS:
        assert p.minimum <= p.default <= p.maximum, p.name


def test_output_shape_and_keys():
    image, metrics = _simulate()
    assert image.shape == (64, 64)
    assert np.isfinite(image).all()
    assert image.min() >= 0.0 and image.max() <= 1.0
    for key in REQUIRED_METRIC_KEYS:
        assert key in metrics, key


def test_volume_formula():
    _, metrics = _simulate(scanner_bore_cm=40.0, scanner_length_cm=80.0)
    expected = math.pi * (40.0 / 200) ** 2 * (80.0 / 100)
    assert metrics["Volume_m3"] == pytest.approx(expected, abs=1e-3)


def test_more_averaging_gives_higher_psnr():
    _, few = _simulate(scan_averaging=1)
    _, many = _simulate(scan_averaging=8)
    assert many["PSNR_dB"] >= few["PSNR_dB"]


def test_vibration_does_not_help_the_image():
    _, still = _simulate(g_level_mg=0.0)
    _, shaky = _simulate(g_level_mg=100.0)
    assert still["SSIM"] >= shaky["SSIM"]