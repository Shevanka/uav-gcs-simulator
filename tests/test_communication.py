"""Unit tests for UDP communication and ConnectionMonitor (FR-02, FR-07)."""

import threading
import time
import pytest
from communication.protocol import ConnectionStatus, TelemetryPayload, current_iso_timestamp
from communication.receiver import UDPReceiver
from communication.sender import UDPSender
from gcs.monitor import ConnectionMonitor


def test_connection_monitor_state_machine():
    """Verify Section 5 FR-07 connection state transitions."""
    status_changes = []

    def on_change(old_s, new_s):
        status_changes.append((old_s, new_s))

    monitor = ConnectionMonitor(timeout_threshold=0.3, on_status_changed=on_change)
    assert monitor.status == ConnectionStatus.DISCONNECTED

    # 1. First valid packet received -> CONNECTED
    monitor.record_valid_packet()
    assert monitor.status == ConnectionStatus.CONNECTED
    assert len(status_changes) == 1
    assert status_changes[0] == (ConnectionStatus.DISCONNECTED, ConnectionStatus.CONNECTED)

    # 2. Wait for timeout
    time.sleep(0.35)
    timed_out = monitor.check_timeout()
    assert timed_out is True
    assert monitor.status == ConnectionStatus.TIMEOUT
    assert len(status_changes) == 2
    assert status_changes[1] == (ConnectionStatus.CONNECTED, ConnectionStatus.TIMEOUT)

    # 3. Valid packet received after timeout -> returns to CONNECTED
    monitor.record_valid_packet()
    assert monitor.status == ConnectionStatus.CONNECTED
    assert len(status_changes) == 3
    assert status_changes[2] == (ConnectionStatus.TIMEOUT, ConnectionStatus.CONNECTED)


def test_udp_sender_receiver_loopback():
    """Test actual UDP transmission and receipt between UDPSender and UDPReceiver."""
    received_packets = []
    received_event = threading.Event()

    def on_packet(data, addr):
        received_packets.append(data)
        received_event.set()

    test_port = 54321
    receiver = UDPReceiver(host="127.0.0.1", port=test_port, on_packet_received=on_packet)
    started = receiver.start()
    assert started is True

    try:
        sender = UDPSender(host="127.0.0.1", port=test_port)
        payload = TelemetryPayload(
            timestamp=current_iso_timestamp(),
            system_id=1,
            component_id=1,
            latitude=-7.2756,
            longitude=112.7949,
            altitude=150.0,
            ground_speed=18.0,
            heading=45.0,
            battery=92.0,
            flight_mode="AUTO",
            armed=True,
        )

        success = sender.send(payload)
        assert success is True

        # Wait for receipt
        got_packet = received_event.wait(timeout=2.0)
        assert got_packet is True
        assert len(received_packets) == 1
        assert b"-7.2756" in received_packets[0]
        assert b"AUTO" in received_packets[0]

        sender.close()
    finally:
        receiver.stop()
        assert not receiver.is_running
