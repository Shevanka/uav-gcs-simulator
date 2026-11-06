"""Unit tests for TelemetryProcessor and Telemetry parsing (FR-03, FR-04, FR-05)."""

import json
import pytest
from communication.protocol import BatteryStatus, TelemetryPayload, current_iso_timestamp
from gcs.telemetry import TelemetryProcessor


@pytest.fixture
def sample_payload_dict():
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


def test_process_valid_packet(sample_payload_dict):
    """Test successful parsing of valid JSON packet."""
    processor = TelemetryProcessor()
    data = json.dumps(sample_payload_dict).encode("utf-8")

    result = processor.process_raw_packet(data)
    assert result.success is True
    assert result.payload is not None
    assert result.payload.latitude == -7.2756
    assert result.payload.flight_mode == "AUTO"
    assert processor.last_valid_telemetry == result.payload
    assert processor.valid_count == 1
    assert processor.rejected_count == 0
    assert processor.success_rate == 100.0


def test_process_malformed_json_packet(sample_payload_dict):
    """Test that malformed JSON does not crash and is properly rejected."""
    processor = TelemetryProcessor()
    # First, feed a valid packet
    valid_data = json.dumps(sample_payload_dict).encode("utf-8")
    processor.process_raw_packet(valid_data)
    assert processor.last_valid_telemetry is not None
    original_last_valid = processor.last_valid_telemetry

    # Now feed malformed JSON
    bad_data = b'{"timestamp": "2026-11-06", "latitude": -7.2756, unclosed'
    result = processor.process_raw_packet(bad_data)

    assert result.success is False
    assert len(result.errors) > 0
    assert "json" in result.errors[0].lower()
    # Ensure last_valid_telemetry was NOT updated or cleared
    assert processor.last_valid_telemetry == original_last_valid
    assert processor.valid_count == 1
    assert processor.rejected_count == 1
    assert processor.success_rate == 50.0


def test_process_invalid_validation_packet(sample_payload_dict):
    """Test that a packet violating range validation is rejected and does not update state."""
    processor = TelemetryProcessor()
    # Set invalid altitude
    sample_payload_dict["altitude"] = 15000.0
    data = json.dumps(sample_payload_dict).encode("utf-8")

    result = processor.process_raw_packet(data)
    assert result.success is False
    assert any("altitude" in err.lower() for err in result.errors)
    assert processor.last_valid_telemetry is None
    assert processor.rejected_count == 1


def test_process_non_utf8_data():
    """Test that arbitrary binary garbage is handled gracefully without exception."""
    processor = TelemetryProcessor()
    garbage = b"\x80\x81\xFF\xFE\x00\x01\xFA"
    result = processor.process_raw_packet(garbage)
    assert result.success is False
    assert any("utf-8" in err.lower() for err in result.errors)
    assert processor.rejected_count == 1


@pytest.mark.parametrize("percentage,expected_status", [
    (100.0, BatteryStatus.NORMAL),
    (75.0, BatteryStatus.NORMAL),
    (74.99, BatteryStatus.WARNING),
    (40.0, BatteryStatus.WARNING),
    (39.99, BatteryStatus.CRITICAL),
    (20.0, BatteryStatus.CRITICAL),
    (19.99, BatteryStatus.EMERGENCY),
    (0.0, BatteryStatus.EMERGENCY),
])
def test_battery_status_thresholds(percentage, expected_status):
    """Verify Section 5 FR-05 battery threshold mappings."""
    status = BatteryStatus.from_percentage(percentage)
    assert status == expected_status
