import threading
import tempfile
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np

from mri.parameters import PARAMS_BY_NAME
from mri.simulator import SpaceMRISimulator
from mri.phantom import head_phantom, load_phantom_from_file
from schemas import ImagePair, Metrics, SimulationResponse, Telemetry
_SIMULATION_LOCK = threading.Lock()
DATA_DIR = Path(__file__).parent / "data"
PHANTOM_NAMES = ("phantom.png", "phantom.jpg", "phantom.jpeg", "phantom.npy")

_phantom = {"array": None, "name": None}

@lru_cache(maxsize=1)
def _default_phantom():
    """A picture from backend/data/ if there is one, otherwise the built-in head."""
    for name in PHANTOM_NAMES:
        candidate = DATA_DIR / name
        if candidate.exists():
            return load_phantom_from_file(candidate, 128), name
    return head_phantom(128, 208.0), "built-in head"


def get_phantom() -> np.ndarray:
    if _phantom["array"] is None:
        _phantom["array"], _phantom["name"] = _default_phantom()
    return _phantom["array"]


def phantom_name() -> str:
    get_phantom()
    return _phantom["name"]


def set_phantom_from_upload(data: bytes, filename: str) -> None:
    """Use an uploaded picture as the phantom. Raises ValueError/OSError if it can't be read."""
    suffix = Path(filename).suffix.lower()
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / f"upload{suffix}"
        path.write_bytes(data)
        array = load_phantom_from_file(path, 128)
    _phantom["array"], _phantom["name"] = array, filename


def reset_phantom() -> None:
    """Go back to the default phantom."""
    _phantom["array"] = None


def run_simulation(params: dict, seed: int):
    simulator = SpaceMRISimulator(get_phantom())
    with _SIMULATION_LOCK:
        np.random.seed(seed)
        return simulator.simulate(**params)


def _to_list(image: np.ndarray) -> list:
    return np.round(image, 4).tolist()


def build_response(image: np.ndarray, metrics: dict, include_images: bool) -> SimulationResponse:
    images = None
    if include_images:
        images = ImagePair(ideal=_to_list(get_phantom()), simulated=_to_list(image))
    return SimulationResponse(metrics=Metrics(**metrics), images=images)


def sweep_values(name: str, points: int) -> list:
    spec = PARAMS_BY_NAME[name]
    if spec.is_int:
        return list(range(int(spec.minimum), int(spec.maximum) + 1))
    return [float(v) for v in np.linspace(spec.minimum, spec.maximum, points)]


def run_sweep(params: dict, seed: int, name: str, points: int) -> list:
    rows = []
    for value in sweep_values(name, points):
        _, metrics = run_simulation({**params, name: value}, seed)
        rows.append({"value": float(value), "metrics": metrics})
    return rows


def read_telemetry(connector) -> Telemetry:
    raw = connector.fetch_live_telemetry()
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return Telemetry(**raw, timestamp_utc=stamp)