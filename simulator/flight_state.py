"""UAV Flight State and Physical Kinematics Model."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# Earth radius in meters
EARTH_RADIUS = 6378137.0


@dataclass
class Waypoint:
    """Navigation Waypoint."""
    latitude: float
    longitude: float
    altitude: float


class FlightStateManager:
    """Manages the kinematics, battery, navigation, and state transitions of the simulated UAV."""

    def __init__(
        self,
        initial_lat: float = -7.2756,
        initial_lon: float = 112.7949,
        initial_alt: float = 0.0,
        initial_battery: float = 100.0,
        initial_mode: str = "AUTO",
        initial_armed: bool = True,
        target_altitude: float = 120.0,
        cruising_speed: float = 15.0,
    ) -> None:
        self.latitude = initial_lat
        self.longitude = initial_lon
        self.altitude = initial_alt
        self.battery = initial_battery
        self.flight_mode = initial_mode
        self.armed = initial_armed

        self.target_altitude = target_altitude
        self.target_speed = cruising_speed
        self.ground_speed = cruising_speed if initial_alt > 1.0 else 0.0
        self.heading = 90.0  # Eastward

        # Flight dynamics parameters
        self.climb_rate = 3.0       # m/s
        self.descent_rate = 2.0     # m/s
        self.turn_rate = 15.0       # deg/s
        self.base_battery_drain = 0.05  # % per second idle
        self.flight_battery_drain = 0.15 # % per second cruising

        # Waypoints for flight simulation (a polygonal flight path around initial coordinates)
        self.waypoints: List[Waypoint] = self._generate_default_waypoints(initial_lat, initial_lon, target_altitude)
        self.current_wp_index = 0

    def _generate_default_waypoints(self, center_lat: float, center_lon: float, alt: float) -> List[Waypoint]:
        """Generate a realistic survey/surveillance rectangular flight path."""
        # Approx 0.005 degrees is ~550m
        delta = 0.004
        return [
            Waypoint(center_lat + delta, center_lon + delta, alt),
            Waypoint(center_lat + delta, center_lon - delta, alt),
            Waypoint(center_lat - delta, center_lon - delta, alt),
            Waypoint(center_lat - delta, center_lon + delta, alt),
        ]

    def update(self, dt: float = 1.0) -> None:
        """Advance the simulation by dt seconds."""
        if not self.armed:
            self.ground_speed = 0.0
            self.battery = max(0.0, self.battery - (self.base_battery_drain * dt))
            return

        # 1. Update Altitude
        if self.flight_mode == "LAND":
            self.target_altitude = 0.0
            if self.altitude > 0.0:
                self.altitude = max(0.0, self.altitude - self.descent_rate * dt)
                self.ground_speed = max(0.0, self.ground_speed - 1.0 * dt)
            else:
                self.armed = False
                self.ground_speed = 0.0
        elif self.flight_mode == "RTL":
            # Return To Launch: climb to safe altitude then head home (center)
            safe_rtl_alt = max(50.0, self.target_altitude)
            if self.altitude < safe_rtl_alt:
                self.altitude = min(safe_rtl_alt, self.altitude + self.climb_rate * dt)
            self._navigate_towards(self.waypoints[0].latitude, self.waypoints[0].longitude, dt)
        else:
            # Normal or Auto flight
            if self.altitude < self.target_altitude:
                self.altitude = min(self.target_altitude, self.altitude + self.climb_rate * dt)
            elif self.altitude > self.target_altitude:
                self.altitude = max(self.target_altitude, self.altitude - self.descent_rate * dt)

            # 2. Update Speed
            if self.altitude > 2.0:
                # Accelerate towards target speed
                if self.ground_speed < self.target_speed:
                    self.ground_speed = min(self.target_speed, self.ground_speed + 2.0 * dt)
            else:
                self.ground_speed = min(self.ground_speed, 2.0)

            # 3. Waypoint Navigation
            if self.waypoints and self.flight_mode in ("AUTO", "GUIDED"):
                wp = self.waypoints[self.current_wp_index]
                reached = self._navigate_towards(wp.latitude, wp.longitude, dt)
                if reached:
                    self.current_wp_index = (self.current_wp_index + 1) % len(self.waypoints)
            elif self.flight_mode == "LOITER":
                # Circle around current position
                self.heading = (self.heading + self.turn_rate * 0.5 * dt) % 360.0
                self._apply_kinematics(dt)
            else:
                self._apply_kinematics(dt)

        # 4. Battery Discharge Model
        # Drain faster when climbing or flying fast
        power_factor = 1.0 + (0.5 if self.altitude < self.target_altitude else 0.0)
        drain = (self.flight_battery_drain * (self.ground_speed / max(1.0, self.target_speed)) * power_factor) * dt
        self.battery = max(0.0, round(self.battery - drain, 2))

    def _navigate_towards(self, target_lat: float, target_lon: float, dt: float) -> bool:
        """Turn and fly towards target coordinates. Return True if arrived within 15 meters."""
        dist, bearing = self.calculate_distance_and_bearing(self.latitude, self.longitude, target_lat, target_lon)

        if dist < 15.0:
            return True

        # Smooth turn towards bearing
        angle_diff = (bearing - self.heading + 180.0) % 360.0 - 180.0
        max_turn = self.turn_rate * dt

        if abs(angle_diff) <= max_turn:
            self.heading = bearing
        else:
            self.heading = (self.heading + math.copysign(max_turn, angle_diff)) % 360.0

        self._apply_kinematics(dt)
        return False

    def _apply_kinematics(self, dt: float) -> None:
        """Update lat/lon from speed and heading using flat-earth projection approximation."""
        dist_moved = self.ground_speed * dt
        heading_rad = math.radians(self.heading)

        # North-South delta (latitude)
        d_lat = (dist_moved * math.cos(heading_rad)) / EARTH_RADIUS
        # East-West delta (longitude)
        d_lon = (dist_moved * math.sin(heading_rad)) / (EARTH_RADIUS * math.cos(math.radians(self.latitude)))

        self.latitude = round(self.latitude + math.degrees(d_lat), 6)
        self.longitude = round(self.longitude + math.degrees(d_lon), 6)
        self.altitude = round(self.altitude, 2)
        self.ground_speed = round(self.ground_speed, 2)
        self.heading = round(self.heading, 1)

    @staticmethod
    def calculate_distance_and_bearing(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> Tuple[float, float]:
        """Compute haversine distance (meters) and initial bearing (degrees)."""
        r_lat1, r_lon1 = math.radians(lat1), math.radians(lon1)
        r_lat2, r_lon2 = math.radians(lat2), math.radians(lon2)

        d_lat = r_lat2 - r_lat1
        d_lon = r_lon2 - r_lon1

        # Haversine distance
        a = math.sin(d_lat / 2.0) ** 2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin(d_lon / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        distance = EARTH_RADIUS * c

        # Forward bearing
        y = math.sin(d_lon) * math.cos(r_lat2)
        x = math.cos(r_lat1) * math.sin(r_lat2) - math.sin(r_lat1) * math.cos(r_lat2) * math.cos(d_lon)
        bearing = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0

        return distance, bearing
