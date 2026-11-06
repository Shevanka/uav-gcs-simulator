"""UDP Telemetry Sender implementation."""

from __future__ import annotations

import logging
import socket
from typing import Optional, Union

from communication.protocol import TelemetryPayload

logger = logging.getLogger(__name__)


class UDPSender:
    """Sends telemetry data over UDP socket."""

    def __init__(self, host: str = "127.0.0.1", port: int = 50051) -> None:
        self.host = host
        self.port = port
        self._socket: Optional[socket.socket] = None
        self._is_open = False
        self._init_socket()

    def _init_socket(self) -> None:
        """Initialize UDP socket."""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._is_open = True
            logger.info("UDPSender initialized targeting %s:%d", self.host, self.port)
        except OSError as e:
            logger.error("Failed to initialize UDPSender socket: %s", e)
            self._is_open = False

    def send(self, data: Union[TelemetryPayload, str, bytes]) -> bool:
        """Send data over UDP.

        Args:
            data: TelemetryPayload, JSON string, or raw bytes.

        Returns:
            True if packet was sent successfully, False otherwise.
        """
        if not self._is_open or self._socket is None:
            self._init_socket()
            if not self._is_open or self._socket is None:
                logger.error("Cannot send data: socket is not available")
                return False

        try:
            if isinstance(data, TelemetryPayload):
                payload_bytes = data.to_bytes()
            elif isinstance(data, str):
                payload_bytes = data.encode("utf-8")
            elif isinstance(data, bytes):
                payload_bytes = data
            else:
                payload_bytes = str(data).encode("utf-8")

            self._socket.sendto(payload_bytes, (self.host, self.port))
            logger.debug("Sent %d bytes to %s:%d", len(payload_bytes), self.host, self.port)
            return True
        except OSError as e:
            logger.error("Error sending UDP packet to %s:%d: %s", self.host, self.port, e)
            return False

    def close(self) -> None:
        """Close UDP socket."""
        if self._socket:
            try:
                self._socket.close()
            except OSError as e:
                logger.warning("Error closing UDPSender socket: %s", e)
            finally:
                self._socket = None
                self._is_open = False
                logger.info("UDPSender socket closed")

    def __enter__(self) -> UDPSender:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
