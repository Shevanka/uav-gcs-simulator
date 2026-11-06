"""Connection Monitor implementation according to Section 5 FR-07."""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from communication.protocol import ConnectionStatus

logger = logging.getLogger(__name__)

StatusChangeCallback = Callable[[ConnectionStatus, ConnectionStatus], None]


class ConnectionMonitor:
    """Monitors telemetry heartbeat and detects communication timeouts."""

    def __init__(
        self,
        timeout_threshold: float = 5.0,
        on_status_changed: Optional[StatusChangeCallback] = None,
    ) -> None:
        self.timeout_threshold = timeout_threshold
        self.on_status_changed = on_status_changed

        self.status: ConnectionStatus = ConnectionStatus.DISCONNECTED
        self.last_packet_time: Optional[float] = None
        self.total_packets_tracked: int = 0

    @property
    def seconds_since_last_packet(self) -> float:
        """Seconds elapsed since last valid packet was received."""
        if self.last_packet_time is None:
            return float("inf")
        return max(0.0, time.time() - self.last_packet_time)

    @property
    def is_connected(self) -> bool:
        return self.status == ConnectionStatus.CONNECTED

    def record_valid_packet(self) -> None:
        """Call whenever a valid telemetry packet is processed."""
        now = time.time()
        self.last_packet_time = now
        self.total_packets_tracked += 1

        if self.status != ConnectionStatus.CONNECTED:
            old_status = self.status
            self.status = ConnectionStatus.CONNECTED
            logger.info("Connection status changed: %s -> CONNECTED", old_status.value)
            if self.on_status_changed:
                try:
                    self.on_status_changed(old_status, ConnectionStatus.CONNECTED)
                except Exception as e:
                    logger.error("Error in on_status_changed callback: %s", e)

    def check_timeout(self) -> bool:
        """Check if elapsed time exceeds timeout threshold.

        Returns:
            True if timeout occurred or is active, False otherwise.
        """
        if self.status == ConnectionStatus.CONNECTED:
            elapsed = self.seconds_since_last_packet
            if elapsed >= self.timeout_threshold:
                old_status = self.status
                self.status = ConnectionStatus.TIMEOUT
                logger.warning(
                    "Connection status changed: %s -> TIMEOUT (no packet for %.2fs)",
                    old_status.value,
                    elapsed,
                )
                if self.on_status_changed:
                    try:
                        self.on_status_changed(old_status, ConnectionStatus.TIMEOUT)
                    except Exception as e:
                        logger.error("Error in on_status_changed callback: %s", e)
                return True
        return self.status == ConnectionStatus.TIMEOUT

    def reset(self) -> None:
        """Reset connection state to DISCONNECTED."""
        old_status = self.status
        self.status = ConnectionStatus.DISCONNECTED
        self.last_packet_time = None
        if old_status != ConnectionStatus.DISCONNECTED and self.on_status_changed:
            try:
                self.on_status_changed(old_status, ConnectionStatus.DISCONNECTED)
            except Exception as e:
                logger.error("Error in on_status_changed callback: %s", e)
