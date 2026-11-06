"""Main Entry Point for UAV Ground Control Station Simulator."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from communication.protocol import ConnectionStatus, TelemetryPayload
from gcs.alerts import Alert, AlertManager
from gcs.logger import TelemetryLogger
from gcs.monitor import ConnectionMonitor
from gcs.telemetry import TelemetryProcessor
from simulator.uav import UAVSimulator


def setup_logging(verbose: bool = False) -> None:
    """Configure terminal logging format."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%H:%M:%S",
    )


def run_headless_simulator(host: str, port: int, interval: float) -> None:
    """Run standalone UAV Simulator in headless console mode."""
    print("=" * 65)
    print(f"🚁 UAV Simulator Broadcasting to UDP {host}:{port}")
    print(f"⏱️ Update Interval: {interval}s (Press Ctrl+C to stop)")
    print("=" * 65)

    def on_sent(p: TelemetryPayload) -> None:
        print(
            f"[{p.timestamp}] Mode: {p.flight_mode:8s} | Alt: {p.altitude:6.1f}m | "
            f"Spd: {p.ground_speed:5.1f}m/s | Hdg: {p.heading:5.1f}° | "
            f"Bat: {p.battery:5.1f}% | Lat: {p.latitude:.5f} | Lon: {p.longitude:.5f}"
        )

    sim = UAVSimulator(host=host, port=port, update_interval=interval, on_telemetry_sent=on_sent)
    sim.start()

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping UAV Simulator...")
    finally:
        sim.stop()
        print("UAV Simulator stopped.")


def run_headless_gcs(host: str, port: int, timeout_sec: float) -> None:
    """Run GCS Receiver and Monitor in headless console mode."""
    from communication.receiver import UDPReceiver

    print("=" * 70)
    print(f"📡 GCS Receiver Listening on UDP {host}:{port}")
    print(f"⏱️ Connection Timeout Threshold: {timeout_sec}s (Press Ctrl+C to stop)")
    print("=" * 70)

    processor = TelemetryProcessor()
    alert_manager = AlertManager()
    logger = TelemetryLogger()

    def on_alert(alert: Alert) -> None:
        print(f"⚠️  ALERT [{alert.severity.value}] {alert.category.value}: {alert.description}")

    alert_manager.add_listener(on_alert)

    def on_status_changed(old_s: ConnectionStatus, new_s: ConnectionStatus) -> None:
        print(f"🔄 Connection Status Changed: {old_s.value} -> {new_s.value}")

    monitor = ConnectionMonitor(timeout_threshold=timeout_sec, on_status_changed=on_status_changed)

    def on_packet(data: bytes, addr: tuple) -> None:
        res = processor.process_raw_packet(data)
        if res.success and res.payload:
            monitor.record_valid_packet()
            alert_manager.evaluate_telemetry(res.payload)
            logger.log(connection_status=monitor.status, validation_status=True, payload=res.payload)
            p = res.payload
            print(
                f"[{p.timestamp}] [RECV] Mode:{p.flight_mode} Alt:{p.altitude:.1f}m "
                f"Bat:{p.battery:.1f}% Spd:{p.ground_speed:.1f}m/s Pos:({p.latitude:.4f}, {p.longitude:.4f})"
            )
        else:
            alert_manager.record_validation_error(res.errors)
            logger.log(
                connection_status=monitor.status,
                validation_status=False,
                payload=res.raw_dict or {},
                errors=res.errors,
            )
            print(f"❌ [REJECTED] {res.error_message}")

    receiver = UDPReceiver(host=host, port=port, on_packet_received=on_packet)
    if not receiver.start():
        print(f"Failed to bind to {host}:{port}")
        return

    try:
        while True:
            time.sleep(0.5)
            monitor.check_timeout()
    except KeyboardInterrupt:
        print("\nStopping GCS Receiver...")
    finally:
        receiver.stop()
        logger.close()
        print("GCS Receiver stopped.")


def run_gui_dashboard(config_path: str, autostart: bool = False) -> None:
    """Launch PySide6 Desktop GUI."""
    try:
        from PySide6.QtWidgets import QApplication
        from ui.dashboard import GCSDashboard
    except ImportError as e:
        print(f"Error importing PySide6 GUI components: {e}")
        print("Please ensure PySide6 is installed: pip install PySide6")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    dashboard = GCSDashboard(config_path=config_path)
    dashboard.show()

    if autostart:
        # Automatically launch both receiver and simulator for instant demo
        dashboard._toggle_receiver()
        dashboard._toggle_simulator()

    sys.exit(app.exec())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="UAV Ground Control Station Simulator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["gui", "sim", "headless-gcs", "all"],
        default="gui",
        help="Run mode: 'gui' (desktop UI), 'sim' (UAV simulator), 'headless-gcs' (console receiver), 'all' (GUI + autostart)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Target UDP host")
    parser.add_argument("--port", type=int, default=50051, help="Target UDP port")
    parser.add_argument("--interval", type=float, default=1.0, help="Simulation update interval (seconds)")
    parser.add_argument("--timeout", type=float, default=5.0, help="Connection timeout threshold (seconds)")
    parser.add_argument("--config", default="config/settings.json", help="Path to configuration JSON file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.mode == "sim":
        run_headless_simulator(args.host, args.port, args.interval)
    elif args.mode == "headless-gcs":
        run_headless_gcs(args.host, args.port, args.timeout)
    elif args.mode == "all":
        run_gui_dashboard(args.config, autostart=True)
    else:
        run_gui_dashboard(args.config, autostart=False)


if __name__ == "__main__":
    main()
