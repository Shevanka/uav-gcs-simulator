"""UAV Simulator runtime module."""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

from communication.protocol import TelemetryPayload
from communication.sender import UDPSender
from simulator.flight_state import FlightStateManager
from simulator.telemetry_generator import TelemetryGenerator

logger = logging.getLogger(__name__)


class UAVSimulator:
    """Simulates an autonomous UAV and broadcasts telemetry over UDP."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 50051,
        update_interval: float = 1.0,
        initial_lat: float = -7.2756,
        initial_lon: float = 112.7949,
        initial_alt: float = 0.0,
        target_alt: float = 120.0,
        cruising_speed: float = 15.0,
        system_id: int = 1,
        component_id: int = 1,
        on_telemetry_sent: Optional[Callable[[TelemetryPayload], None]] = None,
    ) -> None:
        self.update_interval = update_interval
        self.on_telemetry_sent = on_telemetry_sent

        self.flight_state = FlightStateManager(
            initial_lat=initial_lat,
            initial_lon=initial_lon,
            initial_alt=initial_alt,
            target_altitude=target_alt,
            cruising_speed=cruising_speed,
        )
        self.generator = TelemetryGenerator(
            flight_state=self.flight_state,
            system_id=system_id,
            component_id=component_id,
        )
        self.sender = UDPSender(host=host, port=port)

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_transmission_until: float = 0.0
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def step(self, dt: Optional[float] = None) -> TelemetryPayload:
        """Advance one simulation step and transmit telemetry."""
        delta = dt if dt is not None else self.update_interval
        self.flight_state.update(delta)
        payload = self.generator.generate()

        # Check if transmission is temporarily paused (e.g. for timeout testing)
        now = time.time()
        if now >= self._pause_transmission_until:
            self.sender.send(payload)
            if self.on_telemetry_sent:
                try:
                    self.on_telemetry_sent(payload)
                except Exception as e:
                    logger.error("Error in on_telemetry_sent callback: %s", e)
        else:
            logger.info("Telemetry transmission paused for timeout simulation (%.1fs remaining)",
                        self._pause_transmission_until - now)

        return payload

    def start(self) -> None:
        """Start simulation worker loop in a background thread."""
        if self._is_running:
            logger.warning("UAVSimulator is already running")
            return

        self._stop_event.clear()
        self._pause_event.clear()
        self._is_running = True
        self._thread = threading.Thread(target=self._run_loop, name="UAVSimulatorThread", daemon=True)
        self._thread.start()
        logger.info("UAVSimulator started with interval %.2fs", self.update_interval)

    def _run_loop(self) -> None:
        """Background thread execution loop."""
        last_time = time.time()
        while not self._stop_event.is_set():
            now = time.time()
            elapsed = now - last_time

            if not self._pause_event.is_set():
                dt = min(max(elapsed, 0.01), 2.0)
                try:
                    self.step(dt)
                except Exception as e:
                    logger.error("Error in UAVSimulator step: %s", e, exc_info=True)

            last_time = now
            # Sleep with precision
            sleep_time = max(0.05, self.update_interval - (time.time() - now))
            self._stop_event.wait(timeout=sleep_time)

        self._is_running = False
        logger.info("UAVSimulator run loop exited")

    def pause(self) -> None:
        """Pause simulation updates."""
        self._pause_event.set()
        logger.info("UAVSimulator paused")

    def resume(self) -> None:
        """Resume simulation updates."""
        self._pause_event.clear()
        logger.info("UAVSimulator resumed")

    def stop(self) -> None:
        """Stop simulator and close UDP socket."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None
        self._is_running = False
        self.sender.close()
        logger.info("UAVSimulator stopped")

    # --- Anomaly & Testing Injection Methods ---

    def simulate_transmission_blackout(self, duration_sec: float = 6.0) -> None:
        """Pause telemetry packets for duration_sec to trigger GCS communication timeout."""
        self._pause_transmission_until = time.time() + duration_sec
        logger.warning("Simulating transmission blackout for %.1f seconds", duration_sec)

    def send_malformed_json_packet(self) -> bool:
        """Send a syntactically broken JSON packet to test parser robustness."""
        malformed = self.generator.generate_malformed_json()
        logger.warning("Sending malformed JSON packet: %s", malformed)
        return self.sender.send(malformed)

    def send_invalid_data_packet(self) -> bool:
        """Send a packet with out-of-bounds altitude (15,000m) to test validator."""
        invalid_data = self.generator.generate_out_of_bounds_altitude(15000.0)
        import json
        logger.warning("Sending invalid altitude packet: %s", invalid_data)
        return self.sender.send(json.dumps(invalid_data))

    def set_battery(self, percentage: float) -> None:
        """Manually override battery percentage."""
        self.flight_state.battery = max(0.0, min(100.0, percentage))
        logger.info("Manual battery override: %.1f%%", self.flight_state.battery)

    def set_altitude(self, altitude: float) -> None:
        """Manually override altitude."""
        self.flight_state.altitude = altitude
        logger.info("Manual altitude override: %.1fm", self.flight_state.altitude)

    def set_flight_mode(self, mode: str) -> None:
        """Change flight mode."""
        self.flight_state.flight_mode = mode.upper()
        logger.info("Flight mode set to %s", self.flight_state.flight_mode)

    def set_armed(self, armed: bool) -> None:
        """Arm or disarm the UAV."""
        self.flight_state.armed = armed
        logger.info("UAV armed state set to %s", armed)
