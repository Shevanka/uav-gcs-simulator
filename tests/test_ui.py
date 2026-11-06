"""Unit tests for UI components (headless offscreen)."""

import os
import pytest

# Ensure Qt runs headlessly in testing environment
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from communication.protocol import ConnectionStatus, TelemetryPayload, current_iso_timestamp
from gcs.alerts import Alert, AlertCategory, AlertSeverity
from ui.alert_panel import AlertPanel
from ui.dashboard import GCSDashboard
from ui.map_panel import FlightMapCanvas
from ui.telemetry_panel import TelemetryPanel


@pytest.fixture(scope="session")
def qapp():
    """Create a persistent QApplication for offscreen UI testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def sample_telemetry():
    return TelemetryPayload(
        timestamp=current_iso_timestamp(),
        system_id=1,
        component_id=1,
        latitude=-7.2756,
        longitude=112.7949,
        altitude=125.0,
        ground_speed=14.5,
        heading=120.0,
        battery=82.0,
        flight_mode="AUTO",
        armed=True,
    )


def test_telemetry_panel_update(qapp, sample_telemetry):
    """Test updating telemetry cards."""
    panel = TelemetryPanel()
    panel.update_telemetry(sample_telemetry)

    assert "125.0" in panel.card_altitude.value_label.text()
    assert "82.0%" in panel.battery_val_label.text()
    assert "AUTO" in panel.mode_badge.text()
    assert panel.armed_badge.text() == "ARMED"

    # Test battery status color styling
    sample_telemetry.battery = 15.0
    panel.update_telemetry(sample_telemetry)
    assert panel.battery_status_badge.text() == "EMERGENCY"


def test_alert_panel_update(qapp):
    """Test alert panel connection state and inserting alerts."""
    panel = AlertPanel()

    panel.update_connection_status(ConnectionStatus.CONNECTED, 0.5)
    assert panel.conn_badge.text() == "CONNECTED"

    panel.update_connection_status(ConnectionStatus.TIMEOUT, 5.2)
    assert panel.conn_badge.text() == "TIMEOUT"

    # Add alert
    alert = Alert(
        timestamp=current_iso_timestamp(),
        category=AlertCategory.BATTERY,
        severity=AlertSeverity.CRITICAL,
        description="Battery low 19.5%",
    )
    panel.add_alert(alert)
    assert panel.table.rowCount() == 1
    assert panel.table.item(0, 1).text() == "CRITICAL"

    panel.clear_table()
    assert panel.table.rowCount() == 0


def test_map_canvas(qapp):
    """Test flight path map canvas."""
    canvas = FlightMapCanvas()
    canvas.add_telemetry_point(
        latitude=-7.2756,
        longitude=112.7949,
        altitude=100.0,
        battery=90.0,
        heading=45.0,
    )
    assert len(canvas.latitudes) == 1
    assert len(canvas.longitudes) == 1

    canvas.clear_data()
    assert len(canvas.latitudes) == 0


def test_dashboard_instantiation(qapp):
    """Test instantiating GCSDashboard window."""
    dashboard = GCSDashboard()
    assert dashboard.windowTitle() == "UAV Ground Control Station Simulator v1.0.0"
    dashboard.close()
