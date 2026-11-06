"""Unit tests for FlightStateManager and kinematics (FR-01)."""

import pytest
from simulator.flight_state import FlightStateManager


def test_flight_state_initialization():
    """Verify default initial values for UAV flight state."""
    state = FlightStateManager(
        initial_lat=-7.2756,
        initial_lon=112.7949,
        initial_alt=0.0,
        initial_battery=100.0,
        target_altitude=100.0,
        cruising_speed=15.0,
    )
    assert state.latitude == -7.2756
    assert state.longitude == 112.7949
    assert state.altitude == 0.0
    assert state.battery == 100.0
    assert state.armed is True


def test_altitude_climb_and_kinematics():
    """Verify that armed UAV climbs towards target altitude and moves forward."""
    state = FlightStateManager(
        initial_lat=-7.2756,
        initial_lon=112.7949,
        initial_alt=0.0,
        target_altitude=50.0,
        cruising_speed=10.0,
    )
    # Simulate 5 seconds
    for _ in range(5):
        state.update(dt=1.0)

    # Climb rate is 3 m/s, so after 5s altitude should be around 15m
    assert state.altitude > 10.0
    # Battery should have decreased
    assert state.battery < 100.0


def test_disarmed_uav_remains_stationary():
    """Verify that disarmed UAV speed stays 0 and altitude doesn't climb."""
    state = FlightStateManager(initial_alt=0.0, initial_armed=False)
    state.update(dt=1.0)
    assert state.ground_speed == 0.0
    assert state.altitude == 0.0


def test_distance_and_bearing_calculation():
    """Test haversine distance and bearing calculation."""
    # Distance between same points should be 0
    dist, bearing = FlightStateManager.calculate_distance_and_bearing(-7.0, 112.0, -7.0, 112.0)
    assert dist == 0.0

    # Moving directly north
    dist, bearing = FlightStateManager.calculate_distance_and_bearing(0.0, 0.0, 1.0, 0.0)
    assert dist > 110000.0  # Approx 111 km
    assert abs(bearing - 0.0) < 1.0 or abs(bearing - 360.0) < 1.0
