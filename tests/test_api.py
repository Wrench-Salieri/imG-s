import pytest
import requests
from fastapi.testclient import TestClient

import api
from mri.parameters import PARAMS, REQUIRED_METRIC_KEYS
from mri.simulator import SpaceMRISimulator

client = TestClient(api.app)

OFFLINE_ERROR = requests.exceptions.ConnectionError("no internet in this test")

FAKE_TELEMETRY = {
    "latitude": -20.0,
    "longitude": 10.0,
    "position_live": True,
    "environment_status": "WARNING: ISS entering South Atlantic Anomaly. High RF Interference.",
    "b0_penalty_tesla": 0.05,
    "iss_activity": "Crew Exercise (ARED/TRED) Active",
    "live_g_level_mg": 85.0,
    "live_vibration_hz": 12.0,
}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_parameters_endpoint_matches_the_table():
    data = client.get("/parameters").json()
    assert [p["name"] for p in data["parameters"]] == [p.name for p in PARAMS]
    assert data["iss_rack_max_volume_m3"] == 1.2


def test_every_limit_in_the_table_is_enforced_by_the_api():
    for p in PARAMS:
        too_low = client.post("/simulate", json={p.name: p.minimum - 1})
        too_high = client.post("/simulate", json={p.name: p.maximum + 1})
        assert too_low.status_code == 422, p.name
        assert too_high.status_code == 422, p.name


def test_unknown_field_is_rejected():
    response = client.post("/simulate", json={"b0_teslas": 0.15})
    assert response.status_code == 422


def test_text_instead_of_a_number_is_rejected():
    response = client.post("/simulate", json={"b0_tesla": "strong"})
    assert response.status_code == 422


def test_simulate_with_defaults():
    response = client.post("/simulate", json={})
    assert response.status_code == 200
    data = response.json()
    for key in REQUIRED_METRIC_KEYS:
        assert key in data["metrics"], key
    assert len(data["images"]["ideal"]) == 128
    assert len(data["images"]["simulated"]) == 128
    assert isinstance(data["metrics"]["ISS_Rack_Compatible"], bool)


def test_images_can_be_left_out():
    response = client.post("/simulate", params={"include_images": False}, json={})
    assert response.status_code == 200
    assert response.json()["images"] is None


def test_same_seed_gives_the_same_image():
    first = client.post("/simulate", json={"noise_seed": 7}).json()
    second = client.post("/simulate", json={"noise_seed": 7}).json()
    other = client.post("/simulate", json={"noise_seed": 8}).json()
    assert first["images"]["simulated"] == second["images"]["simulated"]
    assert first["images"]["simulated"] != other["images"]["simulated"]


def test_unfinished_physics_answers_501(monkeypatch):
    def not_written(self, *args, **kwargs):
        raise NotImplementedError("simulate() is not written yet.")

    monkeypatch.setattr(SpaceMRISimulator, "simulate", not_written)
    response = client.post("/simulate", json={})
    assert response.status_code == 501
    assert "not written" in response.json()["detail"]


def test_sweep_over_a_whole_number_parameter_uses_every_value():
    body = {"parameter": "scan_averaging", "points": 5}
    data = client.post("/sweep", json=body).json()
    assert [row["value"] for row in data["rows"]] == [1, 2, 3, 4, 5, 6, 7, 8]


def test_sweep_over_a_decimal_parameter_uses_the_requested_points():
    body = {"parameter": "b0_tesla", "points": 6}
    data = client.post("/sweep", json=body).json()
    assert len(data["rows"]) == 6
    assert data["rows"][0]["value"] == pytest.approx(0.05)
    assert data["rows"][-1]["value"] == pytest.approx(0.30)


def test_sweep_rejects_an_unknown_parameter():
    response = client.post("/sweep", json={"parameter": "warp_speed"})
    assert response.status_code == 422


def test_telemetry_when_offline_does_not_invent_a_position(monkeypatch):
    def offline(*args, **kwargs):
        raise OFFLINE_ERROR

    monkeypatch.setattr(requests, "get", offline)
    data = client.get("/telemetry").json()
    assert data["position_live"] is False
    assert data["latitude"] is None
    assert data["b0_penalty_tesla"] == 0.0
    assert data["environment_status"].startswith("UNKNOWN")


def test_mission_simulation_uses_the_live_vibration_and_the_b0_penalty(monkeypatch):
    monkeypatch.setattr(api.connector, "fetch_live_telemetry", lambda: FAKE_TELEMETRY)
    response = client.post("/mission/simulate", params={"include_images": False},
                           json={"b0_tesla": 0.15})
    assert response.status_code == 200
    data = response.json()
    assert data["telemetry"]["live_g_level_mg"] == 85.0
    assert data["effective_b0_tesla"] == pytest.approx(0.10)
    assert data["simulation"]["images"] is None