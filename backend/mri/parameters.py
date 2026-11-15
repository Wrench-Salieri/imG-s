from dataclasses import dataclass


@dataclass(frozen=True)
class Param:
    name: str
    label: str
    unit: str
    minimum: float
    maximum: float
    default: float
    step: float
    help: str

    @property
    def is_int(self):
        return isinstance(self.default, int)


PARAMS = [
    Param("b0_tesla", "Magnetic field strength", "T", 0.05, 0.30, 0.08, 0.01,
          "Field strength of the small permanent magnets. A weaker field gives a noisier image."),
    Param("g_level_mg", "Vibration intensity", "milli-g", 0.0, 100.0, 3.0, 1.0,
          "Vibration level from SAMS-II telemetry."),
    Param("vibration_freq_hz", "Vibration frequency", "Hz", 1.0, 20.0, 12.5, 0.5,
          "Vibration frequency of the ISS."),
    Param("scan_averaging", "Scan averaging", "scans", 10, 30, 20, 1,
          "Number of repeated scans. More scans mean less noise."),
    Param("helium_pressure", "Helium pressure", "bar", 1.0, 5.0, 4.5, 0.1,
          "Pressure and stability of the helium cooling in the coils."),
    Param("vibration_calibration", "Vibration sensitivity", "", 0.1, 3.0, 0.1, 0.1,
          "Calibration factor linking vibration level to phase error."),
    Param("scanner_bore_cm", "Scanner bore diameter", "cm", 28.0, 50.0, 33.0, 1.0,
          "Inner diameter of the 3D scanner chamber."),
    Param("scanner_length_cm", "Scanner length", "cm", 40.0, 100.0, 60.0, 1.0,
          "Total length of the 3D scanner."),
]

GROUPS = {
    "Magnet and scanner": ["b0_tesla", "scanner_bore_cm", "scanner_length_cm"],
    "Cooling": ["helium_pressure"],
    "Vibration": ["g_level_mg", "vibration_freq_hz", "vibration_calibration"],
    "Scan": ["scan_averaging"],
}

PARAMS_BY_NAME = {p.name: p for p in PARAMS}
DEFAULTS = {p.name: p.default for p in PARAMS}

# simulate() return
REQUIRED_METRIC_KEYS = (
    "SSIM", "PSNR_dB", "Volume_m3", "Weight_kg", "Power_W", "ISS_Rack_Compatible",
)

# ISS rack limits
ISS_RACK_MAX_VOLUME_M3 = 1.2
ISS_RACK_MAX_WEIGHT_KG = 300.0
ISS_RACK_MAX_POWER_W = 2000.0 

# SSIM limits
SSIM_MIN_ACCEPTABLE = 0.65
SSIM_MAX_ACCEPTABLE = 0.85

def parameter_table():
    return [
        {
            "Parameter": p.name,
            "Description": p.help,
            "Range": f"{p.minimum} to {p.maximum} {p.unit}".strip(),
            "Default": p.default,
        }
        for p in PARAMS
    ]