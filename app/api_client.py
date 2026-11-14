import os

import requests

API_URL = os.environ.get("IMG_API_URL", "http://127.0.0.1:8000")
TIMEOUT_SECONDS = 30


class ApiOffline(Exception):
    pass

class ApiNotReady(Exception):
    pass

class ApiError(Exception):
    pass

def _detail(response) -> str:
    try:
        detail = response.json().get("detail", response.text)
    except ValueError:
        return response.text
    if isinstance(detail, list):        # validation errors (HTTP 422)
        return "; ".join(
            f"{'.'.join(str(part) for part in item['loc'][1:])}: {item['msg']}" for item in detail
        )
    return str(detail)


def _call(method: str, path: str, **kwargs):
    try:
        response = requests.request(method, f"{API_URL}{path}", timeout=TIMEOUT_SECONDS, **kwargs)
    except requests.exceptions.RequestException as err:
        raise ApiOffline(f"Cannot reach the backend at {API_URL}.") from err
    if response.status_code == 501:
        raise ApiNotReady(_detail(response))
    if response.status_code >= 400:
        raise ApiError(_detail(response))
    return response.json()


def get_parameters() -> dict:
    return _call("GET", "/parameters")


def simulate(params: dict, seed: int) -> dict:
    return _call("POST", "/simulate", json={**params, "noise_seed": seed})


def sweep(params: dict, seed: int, parameter: str, points: int) -> dict:
    body = {"base": {**params, "noise_seed": seed}, "parameter": parameter, "points": points}
    return _call("POST", "/sweep", json=body)


def mission(design: dict, seed: int) -> dict:
    return _call("POST", "/mission/simulate", json={**design, "noise_seed": seed})

