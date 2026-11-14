import threading
from datetime import datetime, timezone
from functools import lru_cache

import numpy as np

from mri.parameters import PARAMS_BY_NAME
from mri.phantom import head_phantom
from mri.simulator import SpaceMRISimulator
from schemas import ImagePair, Metrics, SimulationResponse, Telemetry
_SIMULATION_LOCK = threading.Lock()


@lru_cache(maxsize=1)
def get_phantom() -> np.ndarray:
    return head_phantom(128, 208.0)


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