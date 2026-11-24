"""Unit tests for AlertManager (FR-06)."""

import pytest
from communication.protocol import (
    AlertCategory,
    AlertSeverity,
    TelemetryPayload,
    current_iso_timestamp,
)
from gcs.alerts import Alert, AlertManager


@pytest.fixture
def base_payload():
    return TelemetryPayload(
        timestamp=current_iso_timestamp(),
        system_id=1,
        component_id=1,
        latitude=-7.2756,
        longitude=112.7949,
        altitude=120.0,
        ground_speed=15.0,
        heading=90.0,
        battery=80.0,
        flight_mode="AUTO",
        armed=True,
    )


def test_normal_telemetry_no_alerts(base_payload):
    """Test that normal telemetry values do not trigger any abnormal alerts."""
    manager = AlertManager()
    alerts = manager.evaluate_telemetry(base_payload)
    assert len(alerts) == 0
    assert len(manager.alerts) == 0


def test_battery_critical_alert(base_payload):
    """Test battery < 20% triggers CRITICAL alert."""
    manager = AlertManager()
    base_payload.battery = 18.5
    alerts = manager.evaluate_telemetry(base_payload)
    assert len(alerts) == 1
    assert alerts[0].category == AlertCategory.BATTERY
    assert alerts[0].severity == AlertSeverity.CRITICAL
    assert "18.5%" in alerts[0].description


def test_battery_emergency_alert(base_payload):
    """Test battery < 10% triggers EMERGENCY alert."""
    manager = AlertManager()
    base_payload.battery = 8.0
    alerts = manager.evaluate_telemetry(base_payload)
    assert len(alerts) == 1
    assert alerts[0].category == AlertCategory.BATTERY
    assert alerts[0].severity == AlertSeverity.EMERGENCY


def test_altitude_high_alert(base_payload):
    """Test altitude exceeding operational ceiling (500m) triggers WARNING."""
    manager = AlertManager(max_operational_altitude=500.0)
    base_payload.altitude = 550.0
    alerts = manager.evaluate_telemetry(base_payload)
    assert len(alerts) == 1
    assert alerts[0].category == AlertCategory.ALTITUDE
    assert alerts[0].severity == AlertSeverity.WARNING
    assert "550.0m" in alerts[0].description


def test_altitude_low_alert(base_payload):
    """Test negative altitude triggers CRITICAL alert."""
    manager = AlertManager(min_operational_altitude=0.0)
    base_payload.altitude = -5.0
    alerts = manager.evaluate_telemetry(base_payload)
    assert len(alerts) == 1
    assert alerts[0].category == AlertCategory.ALTITUDE
    assert alerts[0].severity == AlertSeverity.CRITICAL


def test_communication_timeout_and_restore():
    """Test triggering connection timeout and recovery alerts."""
    manager = AlertManager()
    alert_to = manager.record_connection_timeout(5.2)
    assert alert_to.category == AlertCategory.COMMUNICATION
    assert alert_to.severity == AlertSeverity.CRITICAL
    assert "5.2" in alert_to.description

    alert_rest = manager.record_connection_restored()
    assert alert_rest.category == AlertCategory.COMMUNICATION
    assert alert_rest.severity == AlertSeverity.INFO


def test_validation_error_alert():
    """Test recording validation error as alert."""
    manager = AlertManager()
    alert = manager.record_validation_error(["Missing altitude", "Invalid heading"])
    assert alert.category == AlertCategory.VALIDATION
    assert alert.severity == AlertSeverity.WARNING
    assert "Missing altitude" in alert.description


def test_alert_listener():
    """Test that registered listeners receive callbacks."""
    manager = AlertManager()
    received_alerts = []

    def callback(alert: Alert):
        received_alerts.append(alert)

    manager.add_listener(callback)
    manager.record_connection_timeout(5.0)

    assert len(received_alerts) == 1
    assert received_alerts[0].category == AlertCategory.COMMUNICATION
