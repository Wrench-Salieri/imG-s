import time

import requests

ISS_POSITION_URL = "http://api.open-notify.org/iss-now.json"


class MissionControlConnector:
    def __init__(self):
        self.iss_api_url = ISS_POSITION_URL

    def fetch_live_telemetry(self) -> dict:
        try:
            response = requests.get(self.iss_api_url, timeout=5).json()
            lat = float(response["iss_position"]["latitude"])
            lon = float(response["iss_position"]["longitude"])
            position_live = True
        except Exception:
            lat, lon, position_live = None, None, False

        # 1. Υπολογισμός Μαγνητικής Παρεμβολής (South Atlantic Anomaly - SAA) 
        in_saa = position_live and (-50 <= lat <= 0) and (-90 <= lon <= 40)

        if in_saa:
            env_status = "WARNING: ISS entering South Atlantic Anomaly. High RF Interference."
            b0_penalty = 0.05
        elif not position_live:
            env_status = "UNKNOWN: ISS position unavailable (offline). Assuming a nominal orbit."
            b0_penalty = 0.0
        else:
            env_status = "NOMINAL: ISS in safe orbit."
            b0_penalty = 0.0

        # 2. Προσομοίωση Telemetry Κραδασμών (SAMS-II Data) 
        current_minute = int(time.time() / 60) % 10

        if current_minute < 2:
            activity = "Crew Exercise (ARED/TRED) Active"
            g_level = 85.0
            freq_hz = 12.0
        elif current_minute < 4:
            activity = "Orbital Maneuver (Thrusters)"
            g_level = 120.0
            freq_hz = 2.0
        else:
            activity = "Microgravity Ambient (Quiet)"
            g_level = 5.0
            freq_hz = 25.0

        return {
            "latitude": lat,
            "longitude": lon,
            "position_live": position_live,
            "environment_status": env_status,
            "b0_penalty_tesla": b0_penalty,
            "iss_activity": activity,
            "live_g_level_mg": g_level,
            "live_vibration_hz": freq_hz,
        }