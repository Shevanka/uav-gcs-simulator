"""Telemetry Generator for UAV Simulation."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from communication.protocol import TelemetryPayload, current_iso_timestamp
from simulator.flight_state import FlightStateManager


class TelemetryGenerator:
    """Generates valid and anomalous telemetry payloads for simulation and testing."""

    def __init__(
        self,
        flight_state: FlightStateManager,
        system_id: int = 1,
        component_id: int = 1,
    ) -> None:
        self.flight_state = flight_state
        self.system_id = system_id
        self.component_id = component_id

    def generate(self, custom_timestamp: Optional[str] = None) -> TelemetryPayload:
        """Generate current valid telemetry payload."""
        ts = custom_timestamp or current_iso_timestamp()
        return TelemetryPayload(
            timestamp=ts,
            system_id=self.system_id,
            component_id=self.component_id,
            latitude=self.flight_state.latitude,
            longitude=self.flight_state.longitude,
            altitude=self.flight_state.altitude,
            ground_speed=self.flight_state.ground_speed,
            heading=self.flight_state.heading,
            battery=self.flight_state.battery,
            flight_mode=self.flight_state.flight_mode,
            armed=self.flight_state.armed,
        )

    def generate_dict(self, custom_timestamp: Optional[str] = None) -> Dict[str, Any]:
        """Generate telemetry as a Python dictionary."""
        return self.generate(custom_timestamp).to_dict()

    def generate_json(self, custom_timestamp: Optional[str] = None) -> str:
        """Generate telemetry serialized as JSON string."""
        return self.generate(custom_timestamp).to_json()

    # --- Anomaly Generators for Testing & Demonstration ---

    def generate_malformed_json(self) -> str:
        """Generate invalid/corrupt JSON syntax."""
        return '{"timestamp": "' + current_iso_timestamp() + '", "latitude": -7.2756, "unclosed_string: 123'

    def generate_missing_field_dict(self) -> Dict[str, Any]:
        """Generate a dictionary with missing mandatory fields."""
        data = self.generate_dict()
        data.pop("latitude", None)
        data.pop("battery", None)
        return data

    def generate_out_of_bounds_altitude(self, alt: float = 12500.0) -> Dict[str, Any]:
        """Generate a payload with an altitude violating the 0..10,000m rule."""
        data = self.generate_dict()
        data["altitude"] = alt
        return data

    def generate_out_of_bounds_coordinates(self, lat: float = 999.0, lon: float = -999.0) -> Dict[str, Any]:
        """Generate a payload with latitude or longitude out of range."""
        data = self.generate_dict()
        data["latitude"] = lat
        data["longitude"] = lon
        return data

    def generate_invalid_types_dict(self) -> Dict[str, Any]:
        """Generate a payload with invalid data types."""
        data = self.generate_dict()
        data["battery"] = "NOT_A_NUMBER"
        data["armed"] = "MAYBE"
        data["system_id"] = -5
        return data
