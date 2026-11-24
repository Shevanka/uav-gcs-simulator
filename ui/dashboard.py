"""Main GCS Dashboard Window with integrated simulation control and live telemetry monitoring."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from communication.protocol import (
    AlertCategory,
    AlertSeverity,
    ConnectionStatus,
    TelemetryPayload,
)
from communication.receiver import UDPReceiver
from gcs.alerts import Alert, AlertManager
from gcs.logger import TelemetryLogger
from gcs.monitor import ConnectionMonitor
from gcs.telemetry import ParseResult, TelemetryProcessor
from simulator.uav import UAVSimulator
from ui.alert_panel import AlertPanel
from ui.map_panel import FlightMapCanvas
from ui.telemetry_panel import TelemetryPanel

logger = logging.getLogger(__name__)


class GCSBridgeSignals(QObject):
    """Qt signals for thread-safe cross-thread UI updates."""
    telemetry_received = Signal(object)  # TelemetryPayload
    packet_rejected = Signal(object)     # ParseResult
    connection_changed = Signal(object, object)  # old_status, new_status
    alert_triggered = Signal(object)     # Alert


class GCSDashboard(QMainWindow):
    """Primary Ground Control Station Simulator Desktop Window."""

    def __init__(self, config_path: str = "config/settings.json") -> None:
        super().__init__()
        self.config = self._load_config(config_path)
        self.setWindowTitle("UAV Ground Control Station Simulator v1.0.0")
        self.resize(1300, 850)
        self.setMinimumSize(1024, 700)

        # Bridge Signals
        self.signals = GCSBridgeSignals()
        self.signals.telemetry_received.connect(self._on_telemetry_ui)
        self.signals.packet_rejected.connect(self._on_rejected_ui)
        self.signals.connection_changed.connect(self._on_connection_ui)
        self.signals.alert_triggered.connect(self._on_alert_ui)

        # Core Engines
        net_cfg = self.config.get("network", {})
        thresh_cfg = self.config.get("thresholds", {})
        log_cfg = self.config.get("logging", {})

        self.host = net_cfg.get("host", "127.0.0.1")
        self.port = int(net_cfg.get("port", 50051))
        self.timeout_sec = float(net_cfg.get("timeout_seconds", 5.0))

        # Alert Manager
        alt_thresh = thresh_cfg.get("altitude", {})
        bat_thresh = thresh_cfg.get("battery", {})
        self.alert_manager = AlertManager(
            min_operational_altitude=alt_thresh.get("min_operational", 0.0),
            max_operational_altitude=alt_thresh.get("max_operational", 500.0),
            battery_critical_threshold=bat_thresh.get("critical_min", 20.0),
            battery_emergency_threshold=10.0,
        )
        self.alert_manager.add_listener(lambda a: self.signals.alert_triggered.emit(a))

        # Processor & Monitor
        self.telemetry_processor = TelemetryProcessor()
        self.connection_monitor = ConnectionMonitor(
            timeout_threshold=self.timeout_sec,
            on_status_changed=lambda old, new: self.signals.connection_changed.emit(old, new),
        )

        # Logger
        self.telemetry_logger = TelemetryLogger(
            log_dir=log_cfg.get("log_dir", "logs"),
            format_type=log_cfg.get("format", "jsonl"),
            file_prefix=log_cfg.get("file_prefix", "telemetry"),
            enabled=log_cfg.get("enabled", True),
        )

        # Networking & Simulation
        self.receiver = UDPReceiver(
            host=self.host,
            port=self.port,
            on_packet_received=self._on_raw_udp_packet,
        )
        self.simulator: Optional[UAVSimulator] = None

        self._init_ui()
        self._apply_global_styles()

        # UI Refresh & Timeout Check Timer (runs at 5 Hz)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._periodic_check)
        self.timer.start(200)

    def _load_config(self, path: str) -> dict:
        """Load JSON settings file."""
        p = Path(path)
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Error loading config %s: %s", path, e)
        return {}

    def _apply_global_styles(self) -> None:
        """Apply sleek modern dark theme styling."""
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #181825;
            }
            QWidget {
                color: #cdd6f4;
                font-family: 'Segoe UI', 'Ubuntu', 'Roboto', sans-serif;
            }
            QScrollBar:vertical {
                background: #181825;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #45475a;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QStatusBar {
                background-color: #11111b;
                color: #a6adc8;
                border-top: 1px solid #313244;
            }
            """
        )

    def _init_ui(self) -> None:
        """Initialize all dashboard components and layouts."""
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(10)

        # Top Control & Status Toolbar
        root_layout.addWidget(self._build_header_toolbar())

        # Main Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #313244; width: 3px; }")

        # Left Column: Telemetry Gauges + Anomaly Control Center
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.setSpacing(12)

        self.telemetry_panel = TelemetryPanel()
        left_layout.addWidget(self.telemetry_panel)
        left_layout.addWidget(self._build_simulation_control_panel())
        left_layout.addStretch()

        scroll_left = QScrollArea()
        scroll_left.setWidget(left_container)
        scroll_left.setWidgetResizable(True)
        scroll_left.setFrameShape(QFrame.Shape.NoFrame)
        splitter.addWidget(scroll_left)

        # Right Column: Map & Strip Charts + Link Status & Alert Table
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.setSpacing(12)

        self.map_canvas = FlightMapCanvas()
        self.alert_panel = AlertPanel()

        right_layout.addWidget(self.map_canvas, stretch=3)
        right_layout.addWidget(self.alert_panel, stretch=2)

        splitter.addWidget(right_container)
        splitter.setSizes([500, 800])

        root_layout.addWidget(splitter)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Click 'Start Receiver' to listen for telemetry.")

    def _build_header_toolbar(self) -> QFrame:
        """Build top horizontal control bar."""
        frame = QFrame()
        frame.setStyleSheet(
            """
            QFrame {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 6px;
            }
            """
        )
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(14)

        # Title
        title_label = QLabel("🚁 UAV-GCS SIMULATOR")
        title_label.setStyleSheet("color: #89b4fa; font-weight: bold; font-size: 15px;")
        layout.addWidget(title_label)

        # IP/Port Configuration
        layout.addWidget(QLabel("IP:"))
        self.ip_input = QLineEdit(self.host)
        self.ip_input.setFixedWidth(100)
        self.ip_input.setStyleSheet("background-color: #2b2b3d; border: 1px solid #45475a; border-radius: 4px; padding: 3px;")
        layout.addWidget(self.ip_input)

        layout.addWidget(QLabel("Port:"))
        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(self.port)
        self.port_input.setStyleSheet("background-color: #2b2b3d; border: 1px solid #45475a; border-radius: 4px; padding: 3px;")
        layout.addWidget(self.port_input)

        # GCS Receiver Toggle Button
        self.btn_receiver = QPushButton("Start Receiver")
        self.btn_receiver.setStyleSheet(
            """
            QPushButton {
                background-color: #a6e3a1;
                color: #11111b;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #94e2d5;
            }
            """
        )
        self.btn_receiver.clicked.connect(self._toggle_receiver)
        layout.addWidget(self.btn_receiver)

        # Embedded UAV Simulator Toggle Button
        self.btn_simulator = QPushButton("Launch UAV Sim")
        self.btn_simulator.setStyleSheet(
            """
            QPushButton {
                background-color: #89b4fa;
                color: #11111b;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            """
        )
        self.btn_simulator.clicked.connect(self._toggle_simulator)
        layout.addWidget(self.btn_simulator)

        layout.addStretch()

        return frame

    def _build_simulation_control_panel(self) -> QGroupBox:
        """Build Anomaly Injection and Demo Testing Panel."""
        box = QGroupBox("ANOMALY INJECTION & TEST BENCH (PORTFOLIO DEMO)")
        box.setStyleSheet(
            """
            QGroupBox {
                color: #fab387;
                font-weight: bold;
                border: 1px solid #45475a;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 5px;
                padding: 5px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45475a;
            }
            """
        )
        layout = QVBoxLayout(box)
        layout.setSpacing(8)

        # Row 1: Low Battery & Critical Altitude
        r1 = QHBoxLayout()
        btn_low_bat = QPushButton("⚡ Inject Low Battery (15%)")
        btn_low_bat.clicked.connect(lambda: self._inject_battery(15.0))
        btn_high_alt = QPushButton("⛰️ Inject Altitude Ceiling (650m)")
        btn_high_alt.clicked.connect(lambda: self._inject_altitude(650.0))
        r1.addWidget(btn_low_bat)
        r1.addWidget(btn_high_alt)
        layout.addLayout(r1)

        # Row 2: Communication Timeout & Malformed JSON
        r2 = QHBoxLayout()
        btn_timeout = QPushButton("⏱️ 6s Blackout (Test Timeout)")
        btn_timeout.clicked.connect(self._inject_blackout)
        btn_malformed = QPushButton("⚠️ Send Malformed JSON")
        btn_malformed.clicked.connect(self._inject_malformed)
        r2.addWidget(btn_timeout)
        r2.addWidget(btn_malformed)
        layout.addLayout(r2)

        # Row 3: Out-of-bounds invalid data & Mode override
        r3 = QHBoxLayout()
        btn_invalid = QPushButton("🚫 Send Out-of-bounds Data")
        btn_invalid.clicked.connect(self._inject_invalid_data)

        btn_rtl = QPushButton("🏠 Command RTL Mode")
        btn_rtl.clicked.connect(lambda: self._inject_mode("RTL"))
        r3.addWidget(btn_invalid)
        r3.addWidget(btn_rtl)
        layout.addLayout(r3)

        return box

    # --- Background Networking Callbacks (Executed on UDP Thread) ---

    def _on_raw_udp_packet(self, data: bytes, addr: tuple) -> None:
        """Called by UDPReceiver thread on packet arrival."""
        result = self.telemetry_processor.process_raw_packet(data)
        if result.success and result.payload:
            self.connection_monitor.record_valid_packet()
            # Evaluate alerts
            self.alert_manager.evaluate_telemetry(result.payload)
            # Log valid packet
            self.telemetry_logger.log(
                connection_status=self.connection_monitor.status,
                validation_status=True,
                payload=result.payload,
            )
            # Emit Qt signal
            self.signals.telemetry_received.emit(result.payload)
        else:
            # Invalid packet or parse error
            self.alert_manager.record_validation_error(result.errors)
            self.telemetry_logger.log(
                connection_status=self.connection_monitor.status,
                validation_status=False,
                payload=result.raw_dict or {},
                errors=result.errors,
            )
            self.signals.packet_rejected.emit(result)

    # --- UI Slot Handlers (Executed on Main Qt Thread) ---

    def _on_telemetry_ui(self, payload: TelemetryPayload) -> None:
        """Update telemetry cards and flight map."""
        self.telemetry_panel.update_telemetry(payload)
        self.map_canvas.add_telemetry_point(
            latitude=payload.latitude,
            longitude=payload.longitude,
            altitude=payload.altitude,
            battery=payload.battery,
            heading=payload.heading,
        )

    def _on_rejected_ui(self, result: ParseResult) -> None:
        """Update status bar on packet rejection."""
        self.status_bar.showMessage(f"Rejected malformed packet: {result.error_message}")

    def _on_connection_ui(self, old_status: ConnectionStatus, new_status: ConnectionStatus) -> None:
        """Update alert manager and status bar on connection state transition."""
        if new_status == ConnectionStatus.TIMEOUT:
            self.alert_manager.record_connection_timeout(self.connection_monitor.seconds_since_last_packet)
        elif new_status == ConnectionStatus.CONNECTED and old_status in (ConnectionStatus.TIMEOUT, ConnectionStatus.DISCONNECTED):
            self.alert_manager.record_connection_restored()

    def _on_alert_ui(self, alert: Alert) -> None:
        """Insert alert in table."""
        self.alert_panel.add_alert(alert)

    def _periodic_check(self) -> None:
        """Periodic timeout evaluation and link status badge refresh."""
        self.connection_monitor.check_timeout()
        self.alert_panel.update_connection_status(
            self.connection_monitor.status,
            self.connection_monitor.seconds_since_last_packet,
        )
        self.alert_panel.update_statistics(
            total=self.telemetry_processor.total_received,
            valid=self.telemetry_processor.valid_count,
            rejected=self.telemetry_processor.rejected_count,
            success_rate=self.telemetry_processor.success_rate,
        )

    # --- Actions & Controls ---

    def _toggle_receiver(self) -> None:
        """Start or stop UDP receiver."""
        if self.receiver.is_running:
            self.receiver.stop()
            self.connection_monitor.reset()
            self.btn_receiver.setText("Start Receiver")
            self.btn_receiver.setStyleSheet(
                "background-color: #a6e3a1; color: #11111b; font-weight: bold; border-radius: 6px; padding: 6px 14px;"
            )
            self.status_bar.showMessage("Receiver stopped.")
        else:
            self.host = self.ip_input.text().strip()
            self.port = self.port_input.value()
            self.receiver.host = self.host
            self.receiver.port = self.port
            started = self.receiver.start()
            if started:
                self.btn_receiver.setText("Stop Receiver")
                self.btn_receiver.setStyleSheet(
                    "background-color: #f38ba8; color: #11111b; font-weight: bold; border-radius: 6px; padding: 6px 14px;"
                )
                self.status_bar.showMessage(f"Receiver listening on {self.host}:{self.port}")
            else:
                QMessageBox.critical(self, "Error", f"Failed to bind UDP socket on {self.host}:{self.port}")

    def _toggle_simulator(self) -> None:
        """Start or stop embedded UAV simulator."""
        if self.simulator and self.simulator.is_running:
            self.simulator.stop()
            self.simulator = None
            self.btn_simulator.setText("Launch UAV Sim")
            self.btn_simulator.setStyleSheet(
                "background-color: #89b4fa; color: #11111b; font-weight: bold; border-radius: 6px; padding: 6px 14px;"
            )
            self.status_bar.showMessage("Embedded UAV simulator stopped.")
        else:
            target_host = self.ip_input.text().strip()
            target_port = self.port_input.value()
            self.simulator = UAVSimulator(host=target_host, port=target_port, update_interval=1.0)
            self.simulator.start()
            self.btn_simulator.setText("Stop UAV Sim")
            self.btn_simulator.setStyleSheet(
                "background-color: #fab387; color: #11111b; font-weight: bold; border-radius: 6px; padding: 6px 14px;"
            )
            self.status_bar.showMessage(f"UAV simulator active, broadcasting to {target_host}:{target_port}")

    def _inject_battery(self, val: float) -> None:
        if self.simulator:
            self.simulator.set_battery(val)
            self.status_bar.showMessage(f"Injected battery level: {val}%")
        else:
            QMessageBox.information(self, "Simulator Not Running", "Please launch the UAV Sim first to inject anomalies.")

    def _inject_altitude(self, val: float) -> None:
        if self.simulator:
            self.simulator.set_altitude(val)
            self.status_bar.showMessage(f"Injected altitude: {val}m")
        else:
            QMessageBox.information(self, "Simulator Not Running", "Please launch the UAV Sim first to inject anomalies.")

    def _inject_blackout(self) -> None:
        if self.simulator:
            self.simulator.simulate_transmission_blackout(duration_sec=6.0)
            self.status_bar.showMessage("Simulating 6.0s telemetry blackout (testing timeout detection)...")
        else:
            QMessageBox.information(self, "Simulator Not Running", "Please launch the UAV Sim first to inject anomalies.")

    def _inject_malformed(self) -> None:
        if self.simulator:
            self.simulator.send_malformed_json_packet()
            self.status_bar.showMessage("Sent malformed JSON packet to receiver.")
        else:
            QMessageBox.information(self, "Simulator Not Running", "Please launch the UAV Sim first to inject anomalies.")

    def _inject_invalid_data(self) -> None:
        if self.simulator:
            self.simulator.send_invalid_data_packet()
            self.status_bar.showMessage("Sent out-of-bounds telemetry packet.")
        else:
            QMessageBox.information(self, "Simulator Not Running", "Please launch the UAV Sim first to inject anomalies.")

    def _inject_mode(self, mode: str) -> None:
        if self.simulator:
            self.simulator.set_flight_mode(mode)
            self.status_bar.showMessage(f"Flight mode set to {mode}")
        else:
            QMessageBox.information(self, "Simulator Not Running", "Please launch the UAV Sim first.")

    def closeEvent(self, event) -> None:
        """Clean shutdown of network threads and log files on window close."""
        if self.simulator:
            self.simulator.stop()
        if self.receiver:
            self.receiver.stop()
        if self.telemetry_logger:
            self.telemetry_logger.close()
        event.accept()
