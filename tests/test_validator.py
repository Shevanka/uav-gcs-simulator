"""Unit tests for TelemetryValidator (FR-03 & Section 9.2)."""

import pytest
from communication.protocol import current_iso_timestamp
from gcs.validator import TelemetryValidator


@pytest.fixture
def valid_telemetry_dict():
    """Return a valid telemetry dictionary fixture."""
    return {
        "timestamp": current_iso_timestamp(),
        "system_id": 1,
        "component_id": 1,
        "latitude": -7.2756,
        "longitude": 112.7949,
        "altitude": 120.5,
        "ground_speed": 15.2,
        "heading": 90.0,
        "battery": 85.0,
        "flight_mode": "AUTO",
        "armed": True,
    }


def test_valid_telemetry(valid_telemetry_dict):
    """Test that a completely valid payload passes validation without errors."""
    is_valid, errors = TelemetryValidator.validate(valid_telemetry_dict)
    assert is_valid is True
    assert len(errors) == 0


def test_non_dict_payload():
    """Test validation fails when payload is not a dictionary."""
    is_valid, errors = TelemetryValidator.validate(["not", "a", "dict"])
    assert is_valid is False
    assert any("dictionary" in err.lower() for err in errors)


@pytest.mark.parametrize("missing_field", [
    "timestamp", "system_id", "component_id", "latitude", "longitude",
    "altitude", "ground_speed", "heading", "battery", "flight_mode", "armed"
])
def test_missing_required_fields(valid_telemetry_dict, missing_field):
    """Test that omitting any required field fails validation."""
    del valid_telemetry_dict[missing_field]
    is_valid, errors = TelemetryValidator.validate(valid_telemetry_dict)
    assert is_valid is False
    assert any(f"Missing required field: '{missing_field}'" in err for err in errors)


def test_invalid_timestamp(valid_telemetry_dict):
    """Test that invalid ISO 8601 timestamps fail."""
    valid_telemetry_dict["timestamp"] = "invalid-date-string"
    is_valid, errors = TelemetryValidator.validate(valid_telemetry_dict)
    assert is_valid is False
    assert any("timestamp" in err.lower() for err in errors)

    valid_telemetry_dict["timestamp"] = 123456789
    is_valid, errors = TelemetryValidator.validate(valid_telemetry_dict)
    assert is_valid is False


@pytest.mark.parametrize("invalid_id", [-1, 0, 256, 1000, "1", True, False])
def test_invalid_system_and_component_id(valid_telemetry_dict, invalid_id):
    """Test system_id and component_id bounds (1 to 255) and integer typing."""
    valid_telemetry_dict["system_id"] = invalid_id
    is_valid, errors = TelemetryValidator.validate(valid_telemetry_dict)
    assert is_valid is False

    valid_telemetry_dict["system_id"] = 1
    valid_telemetry_dict["component_id"] = invalid_id
    is_valid, errors = TelemetryValidator.validate(valid_telemetry_dict)
    assert is_valid is False


@pytest.mark.parametrize("lat,expected_valid", [
    (-90.0, True),
    (90.0, True),
    (0.0, True),
    (-90.1, False),
    (90.1, False),
    ("0.0", False),
    (True, False),
])
def test_latitude_validation(valid_telemetry_dict, lat, expected_valid):
    """Test latitude bounds [-90, 90]."""
    valid_telemetry_dict["latitude"] = lat
    is_valid, errors = TelemetryValidator.validate(valid_telemetry_dict)
    assert is_valid == expected_valid


@pytest.mark.parametrize("lon,expected_valid", [
    (-180.0, True),
    (180.0, True),
    (0.0, True),
    (-180.1, False),
    (180.1, False),
])
def test_longitude_validation(valid_telemetry_dict, lon, expected_valid):
    """Test longitude bounds [-180, 180]."""
    valid_telemetry_dict["longitude"] = lon
    is_valid, errors = TelemetryValidator.validate(valid_telemetry_dict)
    assert is_valid == expected_valid


@pytest.mark.parametrize("alt,expected_valid", [
    (0.0, True),
    (10000.0, True),
    (500.5, True),
    (-0.1, False),
    (10000.1, False),
])
def test_altitude_validation(valid_telemetry_dict, alt, expected_valid):
    """Test altitude bounds [0, 10000]."""
    valid_telemetry_dict["altitude"] = alt
    is_valid, errors = TelemetryValidator.validate(valid_telemetry_dict)
    assert is_valid == expected_valid


@pytest.mark.parametrize("speed,expected_valid", [
    (0.0, True),
    (25.5, True),
    (-0.1, False),
])
def test_ground_speed_validation(valid_telemetry_dict, speed, expected_valid):
    """Test ground speed >= 0."""
    valid_telemetry_dict["ground_speed"] = speed
    is_valid, errors = TelemetryValidator.validate(valid_telemetry_dict)
    assert is_valid == expected_valid


@pytest.mark.parametrize("heading,expected_valid", [
    (0.0, True),
    (360.0, True),
    (180.5, True),
    (-0.5, False),
    (360.5, False),
])
def test_heading_validation(valid_telemetry_dict, heading, expected_valid):
    """Test heading bounds [0, 360]."""
    valid_telemetry_dict["heading"] = heading
    is_valid, errors = TelemetryValidator.validate(valid_telemetry_dict)
    assert is_valid == expected_valid


@pytest.mark.parametrize("bat,expected_valid", [
    (0.0, True),
    (100.0, True),
    (55, True),
    (-1.0, False),
    (100.5, False),
    ("100", False),
])
def test_battery_validation(valid_telemetry_dict, bat, expected_valid):
    """Test battery percentage bounds [0, 100]."""
    valid_telemetry_dict["battery"] = bat
    is_valid, errors = TelemetryValidator.validate(valid_telemetry_dict)
    assert is_valid == expected_valid


@pytest.mark.parametrize("mode,expected_valid", [
    ("AUTO", True),
    ("MANUAL", True),
    ("STABILIZE", True),
    ("ALT_HOLD", True),
    ("LOITER", True),
    ("GUIDED", True),
    ("RTL", True),
    ("LAND", True),
    ("auto", True),  # Case insensitive in FlightMode.has_value
    ("UNKNOWN_MODE", False),
    (123, False),
])
def test_flight_mode_validation(valid_telemetry_dict, mode, expected_valid):
    """Test recognized flight mode values."""
    valid_telemetry_dict["flight_mode"] = mode
    is_valid, errors = TelemetryValidator.validate(valid_telemetry_dict)
    assert is_valid == expected_valid


@pytest.mark.parametrize("armed_val,expected_valid", [
    (True, True),
    (False, True),
    ("True", False),
    (1, False),
    (0, False),
    (None, False),
])
def test_armed_boolean_validation(valid_telemetry_dict, armed_val, expected_valid):
    """Test armed field strictly requires boolean."""
    valid_telemetry_dict["armed"] = armed_val
    is_valid, errors = TelemetryValidator.validate(valid_telemetry_dict)
    assert is_valid == expected_valid
