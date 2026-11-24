"""UDP Telemetry Receiver implementation."""

from __future__ import annotations

import logging
import socket
import threading
from typing import Callable, Optional, Tuple

logger = logging.getLogger(__name__)

PacketCallback = Callable[[bytes, Tuple[str, int]], None]


class UDPReceiver:
    """Listens for telemetry UDP packets asynchronously in a background thread."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 50051,
        buffer_size: int = 4096,
        socket_timeout: float = 0.5,
        on_packet_received: Optional[PacketCallback] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.buffer_size = buffer_size
        self.socket_timeout = socket_timeout
        self.on_packet_received = on_packet_received

        self._socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self) -> bool:
        """Start listening on the configured host and port in a background thread."""
        if self._is_running:
            logger.warning("UDPReceiver is already running")
            return True

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Allow reusing address for quick restart
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind((self.host, self.port))
            self._socket.settimeout(self.socket_timeout)
        except OSError as e:
            logger.error("Failed to bind UDPReceiver on %s:%d: %s", self.host, self.port, e)
            if self._socket:
                try:
                    self._socket.close()
                except OSError:
                    pass
                self._socket = None
            return False

        self._stop_event.clear()
        self._is_running = True
        self._thread = threading.Thread(target=self._listen_loop, name="UDPReceiverThread", daemon=True)
        self._thread.start()
        logger.info("UDPReceiver started listening on %s:%d", self.host, self.port)
        return True

    def _listen_loop(self) -> None:
        """Background thread worker loop for receiving UDP packets."""
        while not self._stop_event.is_set():
            if self._socket is None:
                break
            try:
                data, addr = self._socket.recvfrom(self.buffer_size)
                if data:
                    logger.debug("Received %d bytes from %s:%d", len(data), addr[0], addr[1])
                    if self.on_packet_received:
                        try:
                            self.on_packet_received(data, addr)
                        except Exception as cb_err:
                            logger.error("Exception in on_packet_received callback: %s", cb_err, exc_info=True)
            except socket.timeout:
                # Normal timeout to check stop_event
                continue
            except OSError as e:
                if self._stop_event.is_set():
                    break
                logger.error("Socket error in UDPReceiver: %s", e)

        self._is_running = False
        logger.info("UDPReceiver listen loop stopped")

    def stop(self) -> None:
        """Stop receiver thread and close socket."""
        if not self._is_running and self._socket is None:
            return

        logger.info("Stopping UDPReceiver...")
        self._stop_event.set()

        if self._socket:
            try:
                self._socket.close()
            except OSError as e:
                logger.warning("Error closing UDPReceiver socket: %s", e)
            finally:
                self._socket = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None

        self._is_running = False
        logger.info("UDPReceiver stopped successfully")

    def __enter__(self) -> UDPReceiver:
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
