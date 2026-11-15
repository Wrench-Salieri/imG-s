"""Real NASA SAMS vibration, saved as small clips by tools/sams_to_csv.py."""
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SCENARIO_LABELS = {
    "quiet": "Quiet ambient (microgravity)",
    "disturbed": "Orbital Maneuver (Thrusters)",
}


class SamsDataMissing(Exception):
    """The clip files have not been made yet."""


@lru_cache(maxsize=None)
def load_trace(scenario: str):
    """Time in seconds and acceleration along y in milli-g, from the saved NASA clip."""
    path = DATA_DIR / f"sams_{scenario}.csv"
    if not path.is_file():
        raise SamsDataMissing(
            f"{path.name} not found. Run 'python tools/sams_to_csv.py' from the project root."
        )
    table = pd.read_csv(path)
    return table["time_s"].to_numpy(), table["y_g"].to_numpy() * 1000.0


@lru_cache(maxsize=1)
def _summary():
    path = DATA_DIR / "sams_scenarios.csv"
    if not path.is_file():
        raise SamsDataMissing("sams_scenarios.csv not found. Run 'python tools/sams_to_csv.py'.")
    return pd.read_csv(path).set_index("label")


def describe(scenario: str) -> dict:
    """The numbers measured for the clip that stands for this scenario."""
    table = _summary()
    if scenario not in table.index:
        raise SamsDataMissing(
            f"No '{scenario}' minute was found in the NASA files. "
            "Download a file from a different time of day and run tools/sams_to_csv.py again."
        )
    row = table.loc[scenario]
    return {
        "label": SCENARIO_LABELS[scenario],
        "rms_mg": float(row["rms_mg"]),
        "dominant_hz": float(row["dominant_hz_1_20"]),
        "source_utc": str(row["window_start_utc"]),
    }
