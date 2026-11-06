"""Telemetry Data Validator implementation according to Section 9.2 specification."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Tuple

from communication.protocol import FlightMode

REQUIRED_FIELDS = [
    "timestamp",
    "system_id",
    "component_id",
    "latitude",
    "longitude",
    "altitude",
    "ground_speed",
    "heading",
    "battery",
    "flight_mode",
    "armed",
]


class TelemetryValidator:
    """Validates raw parsed telemetry dictionaries against PRD schema and range constraints."""

    @staticmethod
    def validate(data: Any) -> Tuple[bool, List[str]]:
        """Validate telemetry dictionary.

        Args:
            data: Parsed telemetry dictionary.

        Returns:
            Tuple of (is_valid: bool, errors: List[str]).
        """
        errors: List[str] = []

        if not isinstance(data, dict):
            return False, ["Payload must be a JSON object / dictionary"]

        # Check required fields
        for field in REQUIRED_FIELDS:
            if field not in data:
                errors.append(f"Missing required field: '{field}'")

        if errors:
            return False, errors

        # 1. timestamp: String, ISO 8601
        ts_val = data["timestamp"]
        if not isinstance(ts_val, str):
            errors.append(f"Field 'timestamp' must be a string, got {type(ts_val).__name__}")
        else:
            try:
                # Support trailing 'Z' in Python datetime
                iso_clean = ts_val.replace("Z", "+00:00")
                datetime.fromisoformat(iso_clean)
            except ValueError:
                errors.append(f"Field 'timestamp' is not a valid ISO 8601 string: '{ts_val}'")

        # 2. system_id: Integer, 1 - 255
        sys_id = data["system_id"]
        # Note: in Python bool is a subclass of int, so explicitly reject bool
        if isinstance(sys_id, bool) or not isinstance(sys_id, int):
            errors.append(f"Field 'system_id' must be an integer, got {type(sys_id).__name__}")
        elif not (1 <= sys_id <= 255):
            errors.append(f"Field 'system_id' ({sys_id}) out of bounds [1, 255]")

        # 3. component_id: Integer, 1 - 255
        comp_id = data["component_id"]
        if isinstance(comp_id, bool) or not isinstance(comp_id, int):
            errors.append(f"Field 'component_id' must be an integer, got {type(comp_id).__name__}")
        elif not (1 <= comp_id <= 255):
            errors.append(f"Field 'component_id' ({comp_id}) out of bounds [1, 255]")

        # 4. latitude: Float or Int, -90 to 90
        lat = data["latitude"]
        if isinstance(lat, bool) or not isinstance(lat, (int, float)):
            errors.append(f"Field 'latitude' must be a number, got {type(lat).__name__}")
        elif not (-90.0 <= float(lat) <= 90.0):
            errors.append(f"Field 'latitude' ({lat}) out of bounds [-90.0, 90.0]")

        # 5. longitude: Float or Int, -180 to 180
        lon = data["longitude"]
        if isinstance(lon, bool) or not isinstance(lon, (int, float)):
            errors.append(f"Field 'longitude' must be a number, got {type(lon).__name__}")
        elif not (-180.0 <= float(lon) <= 180.0):
            errors.append(f"Field 'longitude' ({lon}) out of bounds [-180.0, 180.0]")

        # 6. altitude: Float or Int, 0 to 10,000
        alt = data["altitude"]
        if isinstance(alt, bool) or not isinstance(alt, (int, float)):
            errors.append(f"Field 'altitude' must be a number, got {type(alt).__name__}")
        elif not (0.0 <= float(alt) <= 10000.0):
            errors.append(f"Field 'altitude' ({alt}) out of bounds [0.0, 10000.0]")

        # 7. ground_speed: Float or Int, >= 0
        speed = data["ground_speed"]
        if isinstance(speed, bool) or not isinstance(speed, (int, float)):
            errors.append(f"Field 'ground_speed' must be a number, got {type(speed).__name__}")
        elif float(speed) < 0.0:
            errors.append(f"Field 'ground_speed' ({speed}) cannot be negative")

        # 8. heading: Float or Int, 0 to 360
        heading = data["heading"]
        if isinstance(heading, bool) or not isinstance(heading, (int, float)):
            errors.append(f"Field 'heading' must be a number, got {type(heading).__name__}")
        elif not (0.0 <= float(heading) <= 360.0):
            errors.append(f"Field 'heading' ({heading}) out of bounds [0.0, 360.0]")

        # 9. battery: Number, 0 to 100
        battery = data["battery"]
        if isinstance(battery, bool) or not isinstance(battery, (int, float)):
            errors.append(f"Field 'battery' must be a number, got {type(battery).__name__}")
        elif not (0.0 <= float(battery) <= 100.0):
            errors.append(f"Field 'battery' ({battery}) out of bounds [0.0, 100.0]")

        # 10. flight_mode: String, recognized values
        mode = data["flight_mode"]
        if not isinstance(mode, str):
            errors.append(f"Field 'flight_mode' must be a string, got {type(mode).__name__}")
        elif not FlightMode.has_value(mode):
            errors.append(f"Field 'flight_mode' unrecognized value: '{mode}'")

        # 11. armed: Boolean, True or False
        armed = data["armed"]
        if not isinstance(armed, bool):
            errors.append(f"Field 'armed' must be a boolean (True/False), got {type(armed).__name__}")

        return len(errors) == 0, errors
