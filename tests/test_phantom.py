import numpy as np
import pytest
from PIL import Image

from mri.phantom import load_phantom_from_file


def test_png_becomes_a_square_array_between_0_and_1(tmp_path):
    pixels = np.random.default_rng(0).integers(40, 200, size=(90, 140), dtype=np.uint8)
    path = tmp_path / "scan.png"
    Image.fromarray(pixels).save(path)

    image = load_phantom_from_file(path, n=64)

    assert image.shape == (64, 64)
    assert image.min() == pytest.approx(0.0)
    assert image.max() == pytest.approx(1.0)


def test_colour_picture_is_accepted(tmp_path):
    path = tmp_path / "colour.jpg"
    Image.fromarray(np.random.default_rng(1).integers(0, 255, size=(80, 80, 3), dtype=np.uint8)).save(path)
    assert load_phantom_from_file(path, n=32).shape == (32, 32)


def test_npy_file_is_accepted(tmp_path):
    path = tmp_path / "slice.npy"
    np.save(path, np.random.default_rng(2).random((50, 70)))
    assert load_phantom_from_file(path, n=32).shape == (32, 32)


def test_unknown_file_type_is_rejected(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("not a picture")
    with pytest.raises(ValueError):
        load_phantom_from_file(path)


def test_flat_picture_is_rejected(tmp_path):
    path = tmp_path / "grey.png"
    Image.new("L", (40, 40), 128).save(path)
    with pytest.raises(ValueError):
        load_phantom_from_file(path)


def test_loaded_phantom_works_with_the_simulator(tmp_path):
    from mri.simulator import SpaceMRISimulator
    path = tmp_path / "scan.png"
    Image.fromarray(np.random.default_rng(3).integers(0, 255, size=(100, 100), dtype=np.uint8)).save(path)
    image, metrics = SpaceMRISimulator(load_phantom_from_file(path, 64)).simulate()
    assert image.shape == (64, 64)
    assert -1.0 <= metrics["SSIM"] <= 1.0