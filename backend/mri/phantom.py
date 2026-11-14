# load_phantom_from_file() οτάν χρησιμοποιήσουμε τα DICOM

from pathlib import Path

import numpy as np
from PIL import Image


def _dist_to_segment(x, y, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    t = np.clip(((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy), 0, 1)
    return np.hypot(x - (x1 + t * dx), y - (y1 + t * dy))


def head_phantom(n=128, fov_mm=208.0):
    # Schematic axial slice through the orbits, n x n pixels, values 0..1.
    #Row 0 is the front of the head. Sizes are in millimetres.

    m = 2 * n                                           
    c = (np.arange(m) + 0.5) / m * fov_mm - fov_mm / 2
    x, y = np.meshgrid(c, c)

    def ell(cx, cy, a, b):
        return ((x - cx) / a) ** 2 + ((y - cy) / b) ** 2 <= 1

    img = np.zeros_like(x)
    img[ell(0, 0, 78, 95)] = 0.55                       # scalp and soft tissue
    img[ell(0, 0, 70, 87)] = 0.45                       # orbital fat and face
    img[ell(0, 10, 66, 76)] = 0.08                      # skull (dark)
    img[ell(0, 10, 61, 71)] = 0.75                      # brain
    for side in (-1, 1):
        img[ell(side * 10, 12, 6, 18)] = 0.12           # ventricles
        d = _dist_to_segment(x, y, side * 30, -58, side * 7, -22)
        img[d < 3.5] = 0.2                              # nerve sheath (dark CSF)
        img[d < 2.0] = 0.6                              # optic nerve
        img[ell(side * 30, -68, 12, 12)] = 0.12         # eye globe
    return img.reshape(n, 2, n, 2).mean(axis=(1, 3))


def load_phantom_from_file(path, n=128):
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix in (".png", ".jpg", ".jpeg"):
        picture = Image.open(path).convert("F")          
    elif suffix == ".npy":
        data = np.load(path)
        if data.ndim != 2:
            raise ValueError(f"{path.name}: expected a 2D array, got shape {data.shape}.")
        picture = Image.fromarray(data.astype(np.float32), mode="F")
    elif suffix in (".nii", ".gz", ".dcm"):
        raise NotImplementedError("NIfTI and DICOM files need nibabel / pydicom (not added yet).")
    else:
        raise ValueError(f"{path.name}: unsupported file type '{suffix}'. Use png, jpg or npy.")

    width, height = picture.size
    side = min(width, height)
    left, top = (width - side) // 2, (height - side) // 2
    picture = picture.crop((left, top, left + side, top + side))
    picture = picture.resize((n, n), Image.Resampling.LANCZOS)

    pixels = np.asarray(picture, dtype=np.float64)
    low, high = pixels.min(), pixels.max()
    if high - low < 1e-9:
        raise ValueError(f"{path.name}: the picture is one flat colour.")
    return (pixels - low) / (high - low)