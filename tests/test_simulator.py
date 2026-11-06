"""Unit tests for UAVSimulator and TelemetryGenerator."""

import json
import time
import pytest
from communication.protocol import TelemetryPayload
from simulator.flight_state import FlightStateManager
from simulator.telemetry_generator import TelemetryGenerator
from simulator.uav import UAVSimulator


def test_telemetry_generator():
    """Test all generator methods including anomaly generation."""
    state = FlightStateManager()
    gen = TelemetryGenerator(state, system_id=2, component_id=3)

    payload = gen.generate()
    assert isinstance(payload, TelemetryPayload)
    assert payload.system_id == 2
    assert payload.component_id == 3

    p_dict = gen.generate_dict()
    assert isinstance(p_dict, dict)
    assert p_dict["system_id"] == 2

    p_json = gen.generate_json()
    assert isinstance(p_json, str)
    assert '"system_id": 2' in p_json

    # Test anomalies
    malformed = gen.generate_malformed_json()
    assert isinstance(malformed, str)
    with pytest.raises(json.JSONDecodeError):
        json.loads(malformed)

    missing = gen.generate_missing_field_dict()
    assert "latitude" not in missing
    assert "battery" not in missing

    oob_alt = gen.generate_out_of_bounds_altitude(12000.0)
    assert oob_alt["altitude"] == 12000.0

    oob_coords = gen.generate_out_of_bounds_coordinates(95.0, 200.0)
    assert oob_coords["latitude"] == 95.0
    assert oob_coords["longitude"] == 200.0

    inv_types = gen.generate_invalid_types_dict()
    assert inv_types["battery"] == "NOT_A_NUMBER"


def test_uav_simulator_lifecycle_and_step():
    """Test UAVSimulator step, start, pause, resume, stop."""
    sent_payloads = []

    def on_sent(p):
        sent_payloads.append(p)

    sim = UAVSimulator(
        host="127.0.0.1",
        port=59999,
        update_interval=0.05,
        on_telemetry_sent=on_sent,
    )
    assert not sim.is_running

    # Test single step
    payload = sim.step(dt=1.0)
    assert isinstance(payload, TelemetryPayload)
    assert len(sent_payloads) == 1

    # Test overrides
    sim.set_battery(45.0)
    assert sim.flight_state.battery == 45.0

    sim.set_altitude(300.0)
    assert sim.flight_state.altitude == 300.0

    sim.set_flight_mode("LOITER")
    assert sim.flight_state.flight_mode == "LOITER"

    sim.set_armed(False)
    assert sim.flight_state.armed is False

    # Test anomaly transmitters
    assert sim.send_malformed_json_packet() is True
    assert sim.send_invalid_data_packet() is True

    # Test blackout simulation
    sim.simulate_transmission_blackout(duration_sec=0.2)
    step_res = sim.step(dt=0.1)
    assert step_res is not None

    # Test background thread start & stop
    sim.start()
    assert sim.is_running
    time.sleep(0.15)
    sim.pause()
    time.sleep(0.05)
    sim.resume()
    time.sleep(0.1)
    sim.stop()
    assert not sim.is_running
