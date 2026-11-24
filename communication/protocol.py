"""Protocol definitions, payload models, and constants for UAV-GCS communication."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class FlightMode(str, Enum):
    """Recognized flight modes."""
    MANUAL = "MANUAL"
    STABILIZE = "STABILIZE"
    ALT_HOLD = "ALT_HOLD"
    AUTO = "AUTO"
    LOITER = "LOITER"
    GUIDED = "GUIDED"
    RTL = "RTL"
    LAND = "LAND"

    @classmethod
    def has_value(cls, value: str) -> bool:
        return value.upper() in cls._value2member_map_


class BatteryStatus(str, Enum):
    """Battery status categories per Section 5 FR-05."""
    NORMAL = "NORMAL"        # 75 - 100%
    WARNING = "WARNING"      # 40 - 74.99%
    CRITICAL = "CRITICAL"    # 20 - 39.99%
    EMERGENCY = "EMERGENCY"  # 0 - 19.99%

    @classmethod
    def from_percentage(cls, percentage: float) -> BatteryStatus:
        if percentage >= 75.0:
            return cls.NORMAL
        elif percentage >= 40.0:
            return cls.WARNING
        elif percentage >= 20.0:
            return cls.CRITICAL
        else:
            return cls.EMERGENCY


class ConnectionStatus(str, Enum):
    """Connection state per Section 5 FR-07."""
    DISCONNECTED = "DISCONNECTED"
    CONNECTED = "CONNECTED"
    TIMEOUT = "TIMEOUT"


class AlertSeverity(str, Enum):
    """Severity levels for GCS alerts."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


class AlertCategory(str, Enum):
    """Alert categories per Section 5 FR-06."""
    BATTERY = "BATTERY"
    ALTITUDE = "ALTITUDE"
    COMMUNICATION = "COMMUNICATION"
    VALIDATION = "VALIDATION"
    SYSTEM = "SYSTEM"


@dataclass
class TelemetryPayload:
    """Standard UAV Telemetry Data Payload."""
    timestamp: str
    system_id: int
    component_id: int
    latitude: float
    longitude: float
    altitude: float
    ground_speed: float
    heading: float
    battery: float
    flight_mode: str
    armed: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_bytes(self) -> bytes:
        return self.to_json().encode("utf-8")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TelemetryPayload:
        return cls(
            timestamp=str(data["timestamp"]),
            system_id=int(data["system_id"]),
            component_id=int(data["component_id"]),
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            altitude=float(data["altitude"]),
            ground_speed=float(data["ground_speed"]),
            heading=float(data["heading"]),
            battery=float(data["battery"]),
            flight_mode=str(data["flight_mode"]).upper(),
            armed=bool(data["armed"]),
        )


def current_iso_timestamp() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
