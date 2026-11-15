"""Turn the raw NASA SAMS acceleration files into two small CSV files the simulator can use.

Run from the project root:
    python tools/sams_to_csv.py

It reads every data file in data_raw/sams/, measures each minute of vibration, and decides
whether that minute was quiet or disturbed. It writes into backend/data/:
    sams_windows.csv    one row per minute that was measured (so you can check the decision)
    sams_scenarios.csv  one row per label: which minute was chosen to represent it
    sams_quiet.csv      10 seconds of real acceleration from a typical quiet minute
    sams_disturbed.csv  10 seconds from a typical disturbed minute (only if one exists)
"""
import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_RATE_HZ = 500.0
WINDOW_SECONDS = 60
CLIP_SECONDS = 10
BAND_HZ = (1.0, 20.0)          # the range the simulator's vibration lives in
NAME_PATTERN = re.compile(r"^(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2}\.\d+)")
SKIP_SUFFIXES = {".xml", ".ascii", ".xlsx", ".csv", ".txt", ".py"}


def sample_rate(data_file: Path) -> float:
    """Read SampleRate from the header file next to the data file, if there is one."""
    for header in data_file.parent.glob(data_file.name + "*.xml"):
        found = re.search(r"<SampleRate>([\d.]+)</SampleRate>", header.read_text())
        if found:
            return float(found.group(1))
    return DEFAULT_RATE_HZ


def start_time(name: str) -> pd.Timestamp:
    y, mo, d, h, mi, s = NAME_PATTERN.match(name).groups()
    return pd.Timestamp(f"{y}-{mo}-{d} {h}:{mi}:{float(s):06.3f}")


def data_files(folder: Path) -> list:
    return sorted(p for p in folder.iterdir()
                  if p.is_file() and p.suffix.lower() not in SKIP_SUFFIXES
                  and NAME_PATTERN.match(p.name))


def measure(window: np.ndarray, rate: float):
    """RMS over all frequencies, RMS inside 1-20 Hz, and the strongest frequency in 1-20 Hz (mg, Hz)."""
    n = len(window)
    freq = np.fft.rfftfreq(n, 1 / rate)
    in_band = (freq >= BAND_HZ[0]) & (freq <= BAND_HZ[1])
    total_rms = np.sqrt((window ** 2).sum(axis=1).mean()) * 1000
    plain = sum(np.abs(np.fft.rfft(window[:, k])) ** 2 for k in range(3))
    band_rms = np.sqrt(2 * plain[in_band].sum()) / n * 1000
    shaped = sum(np.abs(np.fft.rfft(window[:, k] * np.hanning(n))) ** 2 for k in range(3))
    dominant = freq[in_band][np.argmax(shaped[in_band])]
    return total_rms, band_rms, dominant


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", default="data_raw/sams", help="folder with the NASA files")
    parser.add_argument("--out", default="backend/data", help="folder for the CSV files")
    parser.add_argument("--quiet-max", type=float, default=0.3,
                        help="a minute counts as quiet if its 1-20 Hz RMS is at most this many milli-g")
    args = parser.parse_args()

    raw, out = Path(args.raw), Path(args.out)
    files = data_files(raw)
    if not files:
        raise SystemExit(f"No NASA data files found in {raw}/")
    out.mkdir(parents=True, exist_ok=True)

    rows, windows = [], {}
    for path in files:
        rate = sample_rate(path)
        data = np.fromfile(path, dtype="<f4").reshape(-1, 4).astype(float)
        accel = data[:, 1:] - data[:, 1:].mean(axis=0)          # demean, as NASA instructs
        size = int(WINDOW_SECONDS * rate)
        starts = range(0, len(accel) - size + 1, size) if len(accel) >= size else [0]
        for i in starts:
            window = accel[i:i + size]
            total, band, dominant = measure(window, rate)
            begin = start_time(path.name) + pd.Timedelta(seconds=i / rate)
            rows.append({
                "file": path.name, "window_start_utc": begin.isoformat(timespec="seconds"),
                "rms_mg": round(total, 3), "band_1_20hz_rms_mg": round(band, 3),
                "dominant_hz_1_20": round(float(dominant), 2),
                "label": "quiet" if band <= args.quiet_max else "disturbed",
            })
            windows[len(rows) - 1] = (window, rate)
        print(f"read {path.name}: {len(accel) / rate / 60:.1f} minutes at {rate:g} Hz")

    table = pd.DataFrame(rows)
    table.to_csv(out / "sams_windows.csv", index=False)

    chosen = []
    for label, group in table.groupby("label"):
        middle = group.sort_values("band_1_20hz_rms_mg").iloc[len(group) // 2]
        window, rate = windows[middle.name]
        clip = window[: int(CLIP_SECONDS * rate)]
        pd.DataFrame({
            "time_s": np.arange(len(clip)) / rate,
            "x_g": clip[:, 0], "y_g": clip[:, 1], "z_g": clip[:, 2],
        }).to_csv(out / f"sams_{label}.csv", index=False, float_format="%.7f")
        chosen.append({**middle.to_dict(), "clip_file": f"sams_{label}.csv"})
    pd.DataFrame(chosen).to_csv(out / "sams_scenarios.csv", index=False)

    print("\nMinutes measured, by label:")
    print(table.groupby("label")["band_1_20hz_rms_mg"].describe()[["count", "min", "50%", "max"]])
    print(f"\nQuiet means a 1-20 Hz RMS of at most {args.quiet_max} milli-g "
          "(change it with --quiet-max).")
    if "disturbed" not in set(table["label"]):
        print("No disturbed minute found yet: download a file from a busier time of day.")
    print(f"Wrote the CSV files to {out}/")


if __name__ == "__main__":
    main()
