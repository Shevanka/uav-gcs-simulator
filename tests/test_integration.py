"""End-to-end integration tests verifying complete simulation and GCS dataflow."""

import time
import pytest
from communication.protocol import ConnectionStatus
from communication.receiver import UDPReceiver
from gcs.alerts import Alert, AlertCategory, AlertManager, AlertSeverity
from gcs.logger import TelemetryLogger
from gcs.monitor import ConnectionMonitor
from gcs.telemetry import TelemetryProcessor
from simulator.uav import UAVSimulator


def test_end_to_end_simulation_dataflow(tmp_path):
    """Test full pipeline: UAVSimulator -> UDP -> UDPReceiver -> Processor -> Validator -> Monitor -> AlertManager -> Logger."""
    test_port = 55123
    log_dir = tmp_path / "logs"

    processor = TelemetryProcessor()
    alert_manager = AlertManager(max_operational_altitude=500.0, battery_critical_threshold=20.0)
    logger = TelemetryLogger(log_dir=str(log_dir), format_type="jsonl", file_prefix="integ_test")
    monitor = ConnectionMonitor(timeout_threshold=0.5)

    captured_alerts = []
    alert_manager.add_listener(lambda a: captured_alerts.append(a))

    def on_packet(data: bytes, addr: tuple):
        result = processor.process_raw_packet(data)
        if result.success and result.payload:
            monitor.record_valid_packet()
            alert_manager.evaluate_telemetry(result.payload)
            logger.log(
                connection_status=monitor.status,
                validation_status=True,
                payload=result.payload,
            )
        else:
            alert_manager.record_validation_error(result.errors)
            logger.log(
                connection_status=monitor.status,
                validation_status=False,
                payload=result.raw_dict or {},
                errors=result.errors,
            )

    receiver = UDPReceiver(host="127.0.0.1", port=test_port, on_packet_received=on_packet)
    assert receiver.start() is True

    try:
        sim = UAVSimulator(
            host="127.0.0.1",
            port=test_port,
            update_interval=0.05,
            initial_alt=50.0,
            target_alt=100.0,
        )

        # 1. Start simulation and verify valid packet reception
        sim.start()
        time.sleep(0.25)
        assert processor.valid_count >= 3
        assert monitor.is_connected is True
        assert processor.last_valid_telemetry is not None

        # 2. Inject Anomaly: Malformed packet
        sim.send_malformed_json_packet()
        time.sleep(0.1)
        assert processor.rejected_count >= 1
        assert any(a.category == AlertCategory.VALIDATION for a in captured_alerts)

        # 3. Inject Anomaly: Low battery
        sim.set_battery(15.0)
        time.sleep(0.15)
        assert any(a.category == AlertCategory.BATTERY for a in captured_alerts)

        # 4. Inject Anomaly: High altitude ceiling
        sim.set_altitude(600.0)
        time.sleep(0.15)
        assert any(a.category == AlertCategory.ALTITUDE for a in captured_alerts)

        # 5. Stop simulator and verify timeout detection
        sim.stop()
        time.sleep(0.6)  # Exceeds 0.5s timeout threshold
        timed_out = monitor.check_timeout()
        assert timed_out is True
        assert monitor.status == ConnectionStatus.TIMEOUT

    finally:
        receiver.stop()
        logger.close()

    # Verify log file was written and is valid JSONL
    log_files = list(log_dir.glob("*.jsonl"))
    assert len(log_files) == 1
    content = log_files[0].read_text(encoding="utf-8").strip().splitlines()
    assert len(content) >= 3
