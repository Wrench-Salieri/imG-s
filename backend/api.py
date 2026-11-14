from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import service
from mri.parameters import (
    GROUPS,
    ISS_RACK_MAX_VOLUME_M3,
    ISS_RACK_MAX_WEIGHT_KG,
    PARAMS,
    PARAMS_BY_NAME,
)
from mri.telemetry import MissionControlConnector
from schemas import (
    MissionRequest,
    MissionResponse,
    ParameterSpec,
    ParametersResponse,
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


@app.exception_handler(NotImplementedError)
async def physics_not_ready(request: Request, exc: NotImplementedError):
    return JSONResponse(status_code=501, content={"detail": str(exc) or "Not implemented yet."})


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