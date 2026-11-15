from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

import service
from mri.parameters import (
    GROUPS,
    ISS_RACK_MAX_VOLUME_M3,
    ISS_RACK_MAX_WEIGHT_KG,
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
        ssim_min=SSIM_MIN_ACCEPTABLE,
        ssim_max=SSIM_MAX_ACCEPTABLE,
    )


@app.post("/simulate", response_model=SimulationResponse)
def simulate(payload: SimulationRequest, include_images: bool = True):
    image, metrics = service.run_simulation(payload.physics_inputs(), payload.noise_seed)
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
    live = service.read_telemetry(connector)          # ISS position and radiation only
    try:
        override = cloud_state.read_override()
        cloud_error = None
    except cloud_state.CloudStateError as err:
        override = {"active": False, "storage": cloud_state.get_store().name}
        cloud_error = str(err)

    params = payload.physics_inputs()
    if override["active"]:
        g_level, frequency = override["g_level_mg"], override["vibration_freq_hz"]
        activity, source = "Astronaut override", "astronaut override"
        params["vibration_scenario"] = None            # the sine wave, with the astronaut's numbers
    else:
        recording = sams.describe(payload.vibration_scenario)
        g_level, frequency = recording["rms_mg"], recording["dominant_hz"]
        activity = recording["label"]
        source = f"NASA SAMS recording, {recording['source_utc']} UTC"

    live = live.model_copy(update={"iss_activity": activity, "live_g_level_mg": g_level,
                                   "live_vibration_hz": frequency})
    effective_b0 = max(0.01, payload.b0_tesla - live.b0_penalty_tesla)
    params.update(b0_tesla=effective_b0, g_level_mg=g_level, vibration_freq_hz=frequency)

    image, metrics = service.run_simulation(params, payload.noise_seed)
    return MissionResponse(
        telemetry=live,
        effective_b0_tesla=round(effective_b0, 3),
        effective_g_level_mg=g_level,
        effective_vibration_hz=frequency,
        vibration_source=source,
        override=override,
        cloud_error=cloud_error,
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