from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator
from typing import Literal
from mri.parameters import PARAMS_BY_NAME, SSIM_MAX_ACCEPTABLE, SSIM_MIN_ACCEPTABLE


def _limits(name: str):
    p = PARAMS_BY_NAME[name]
    unit = f" Unit: {p.unit}." if p.unit else ""
    return Field(default=p.default, ge=p.minimum, le=p.maximum, description=p.help + unit)

class DesignInputs(BaseModel):

    model_config = ConfigDict(extra="forbid")      

    b0_tesla: float = _limits("b0_tesla")
    helium_pressure: float = _limits("helium_pressure")
    scan_averaging: int = _limits("scan_averaging")
    vibration_calibration: float = _limits("vibration_calibration")
    scanner_bore_cm: float = _limits("scanner_bore_cm")
    scanner_length_cm: float = _limits("scanner_length_cm")
    noise_seed: int = Field(
        default=42, ge=0, le=9999,
        description="Same seed, same random noise. Change it to get a different noise pattern.",
    )

    def physics_inputs(self) -> dict:
        return self.model_dump(exclude={"noise_seed"})


class SimulationRequest(DesignInputs):
    g_level_mg: float = _limits("g_level_mg")
    vibration_freq_hz: float = _limits("vibration_freq_hz")


class MissionRequest(DesignInputs):
    vibration_scenario: Literal["quiet", "disturbed"] = "quiet"

class SweepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base: SimulationRequest = Field(default_factory=SimulationRequest)
    parameter: str = Field(description="Name of the parameter to sweep, e.g. 'b0_tesla'.")
    points: int = Field(
        default=11, ge=3, le=50,
        description="Number of values to try (whole-number parameters use every value).",
    )

    @field_validator("parameter")
    @classmethod
    def parameter_must_exist(cls, value: str) -> str:
        if value not in PARAMS_BY_NAME:
            raise ValueError(f"unknown parameter '{value}'. Choose one of: {', '.join(PARAMS_BY_NAME)}")
        return value

class Metrics(BaseModel):
    model_config = ConfigDict(extra="allow")

    SSIM: float
    PSNR_dB: float
    Volume_m3: float
    Weight_kg: float
    Power_W: float
    ISS_Rack_Compatible: bool

    @computed_field
    @property
    def SSIM_Compatible(self) -> bool:
        return SSIM_MIN_ACCEPTABLE <= self.SSIM <= SSIM_MAX_ACCEPTABLE


class ImagePair(BaseModel):
    ideal: list[list[float]]
    simulated: list[list[float]]

class PhantomInfo(BaseModel):
    name: str

class SimulationResponse(BaseModel):
    metrics: Metrics
    images: ImagePair | None = None    


class SweepRow(BaseModel):
    value: float
    metrics: Metrics


class SweepResponse(BaseModel):
    parameter: str
    unit: str
    rows: list[SweepRow]


class Telemetry(BaseModel):
    latitude: float | None
    longitude: float | None
    position_live: bool
    environment_status: str
    b0_penalty_tesla: float
    iss_activity: str
    live_g_level_mg: float
    live_vibration_hz: float
    timestamp_utc: str


class MissionResponse(BaseModel):
    telemetry: Telemetry
    effective_b0_tesla: float = Field(description="Design B0 minus the SAA penalty.")
    simulation: SimulationResponse


class ParameterSpec(BaseModel):
    name: str
    label: str
    unit: str
    minimum: float
    maximum: float
    default: float
    step: float
    help: str
    is_int: bool


class ParametersResponse(BaseModel):
    parameters: list[ParameterSpec]
    groups: dict[str, list[str]]
    iss_rack_max_volume_m3: float
    iss_rack_max_weight_kg: float
    ssim_min: float
    ssim_max: float