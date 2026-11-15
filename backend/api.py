from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

import service
from mri.parameters import (
    GROUPS,
    ISS_RACK_MAX_VOLUME_M3,
    ISS_RACK_MAX_WEIGHT_KG,
    ISS_RACK_MAX_POWER_W,
    PARAMS,
    PARAMS_BY_NAME,
    SSIM_MAX_ACCEPTABLE,
    SSIM_MIN_ACCEPTABLE,
)
from mri.telemetry import MissionControlConnector
from mri import sams
from schemas import (
    MissionRequest,
    MissionResponse,
    ParameterSpec,
    ParametersResponse,
    PhantomInfo,
    SimulationRequest,
    SimulationResponse,
    SweepRequest,
    SweepResponse,
    Telemetry,
)

app = FastAPI(
    title="Space MRI Digital Twin API",
    version="0.1.0",
    description="Physics-based simulation of a portable MRI on the ISS.",
)

connector = MissionControlConnector()

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

@app.exception_handler(NotImplementedError)
async def physics_not_ready(request: Request, exc: NotImplementedError):
    return JSONResponse(status_code=501, content={"detail": str(exc) or "Not implemented yet."})

@app.exception_handler(sams.SamsDataMissing)
async def sams_missing(request: Request, exc: sams.SamsDataMissing):
    return JSONResponse(status_code=503, content={"detail": str(exc)})

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/parameters", response_model=ParametersResponse)
def parameters():
    return ParametersResponse(
        parameters=[
            ParameterSpec(
                name=p.name, label=p.label, unit=p.unit, minimum=p.minimum,
                maximum=p.maximum, default=p.default, step=p.step, help=p.help,
                is_int=p.is_int,
            )
            for p in PARAMS
        ],
        groups=GROUPS,
        iss_rack_max_volume_m3=ISS_RACK_MAX_VOLUME_M3,
        iss_rack_max_weight_kg=ISS_RACK_MAX_WEIGHT_KG,
        iss_rack_max_power_w=ISS_RACK_MAX_POWER_W,
        ssim_min=SSIM_MIN_ACCEPTABLE,
        ssim_max=SSIM_MAX_ACCEPTABLE,
    )


@app.post("/simulate", response_model=SimulationResponse)
def simulate(payload: SimulationRequest, include_images: bool = True):
    params = payload.physics_inputs()
    if payload.vibration_scenario:
        recording = sams.describe(payload.vibration_scenario)
        params["g_level_mg"] = recording["rms_mg"]            # keeps the power estimate consistent
        params["vibration_freq_hz"] = recording["dominant_hz"]
    image, metrics = service.run_simulation(params, payload.noise_seed)
    return service.build_response(image, metrics, include_images)


@app.post("/sweep", response_model=SweepResponse)
def sweep(payload: SweepRequest):
    spec = PARAMS_BY_NAME[payload.parameter]
    rows = service.run_sweep(
        payload.base.physics_inputs(), payload.base.noise_seed, payload.parameter, payload.points
    )
    return SweepResponse(parameter=spec.name, unit=spec.unit, rows=rows)


@app.get("/telemetry", response_model=Telemetry)
def telemetry():
    return service.read_telemetry(connector)


@app.post("/mission/simulate", response_model=MissionResponse)
def mission_simulate(payload: MissionRequest, include_images: bool = True):
    live = service.read_telemetry(connector)
    effective_b0 = max(0.01, payload.b0_tesla - live.b0_penalty_tesla)
    params = {
        **payload.physics_inputs(),
        "b0_tesla": effective_b0,
        "g_level_mg": live.live_g_level_mg,
        "vibration_freq_hz": live.live_vibration_hz,
    }
    image, metrics = service.run_simulation(params, payload.noise_seed)
    return MissionResponse(
        telemetry=live,
        effective_b0_tesla=round(effective_b0, 3),
        simulation=service.build_response(image, metrics, include_images),
    )

@app.get("/phantom", response_model=PhantomInfo)
def phantom_info():
    """Which test image the simulations currently start from."""
    return PhantomInfo(name=service.phantom_name())


@app.post("/phantom", response_model=PhantomInfo)
def upload_phantom(file: UploadFile):
    """Use an uploaded picture (png, jpg or npy) as the test image."""
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="The file is larger than 10 MB.")
    try:
        service.set_phantom_from_upload(data, file.filename or "upload")
    except (ValueError, OSError) as err:
        raise HTTPException(status_code=422, detail=f"Could not use this picture: {err}")
    return PhantomInfo(name=service.phantom_name())


@app.delete("/phantom", response_model=PhantomInfo)
def reset_phantom():
    """Go back to the default test image."""
    service.reset_phantom()
    return PhantomInfo(name=service.phantom_name())