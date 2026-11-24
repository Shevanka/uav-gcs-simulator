"""Telemetry Display Panel for GCS Dashboard."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from communication.protocol import BatteryStatus, TelemetryPayload


class MetricCard(QFrame):
    """Reusable visual card displaying a single telemetry parameter."""

    def __init__(self, title: str, unit: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            """
            MetricCard {
                background-color: #2b2b3d;
                border: 1px solid #3e3e55;
                border-radius: 8px;
                padding: 6px;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        self.title_label = QLabel(title.upper())
        self.title_label.setStyleSheet("color: #a6adc8; font-size: 11px; font-weight: bold;")

        val_layout = QHBoxLayout()
        val_layout.setContentsMargins(0, 0, 0, 0)
        val_layout.setSpacing(4)

        self.value_label = QLabel("--")
        self.value_label.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold;")

        self.unit_label = QLabel(unit)
        self.unit_label.setStyleSheet("color: #89b4fa; font-size: 12px; font-weight: normal; margin-top: 6px;")

        val_layout.addWidget(self.value_label)
        val_layout.addWidget(self.unit_label)
        val_layout.addStretch()

        self.sub_label = QLabel("")
        self.sub_label.setStyleSheet("color: #bac2de; font-size: 11px;")
        self.sub_label.setVisible(False)

        layout.addWidget(self.title_label)
        layout.addLayout(val_layout)
        layout.addWidget(self.sub_label)

    def set_value(self, val_str: str, sub_str: Optional[str] = None) -> None:
        self.value_label.setText(val_str)
        if sub_str:
            self.sub_label.setText(sub_str)
            self.sub_label.setVisible(True)
        else:
            self.sub_label.setVisible(False)


class TelemetryPanel(QWidget):
    """Panel displaying real-time telemetry gauges, battery state, and flight status."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        # 1. Flight Status Header Card (Mode, Armed, Heartbeat)
        status_box = QGroupBox("AIRCRAFT FLIGHT STATE")
        status_box.setStyleSheet(
            """
            QGroupBox {
                color: #cdd6f4;
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
            """
        )
        status_layout = QHBoxLayout(status_box)

        # Mode Badge
        self.mode_badge = QLabel("MODE: --")
        self.mode_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mode_badge.setStyleSheet(
            """
            QLabel {
                background-color: #313244;
                color: #89b4fa;
                font-weight: bold;
                font-size: 14px;
                padding: 6px 14px;
                border: 1px solid #45475a;
                border-radius: 6px;
            }
            """
        )

        # Armed Badge
        self.armed_badge = QLabel("DISARMED")
        self.armed_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.armed_badge.setStyleSheet(
            """
            QLabel {
                background-color: #313244;
                color: #6c7086;
                font-weight: bold;
                font-size: 14px;
                padding: 6px 14px;
                border: 1px solid #45475a;
                border-radius: 6px;
            }
            """
        )

        # System/Comp ID
        self.sys_info_label = QLabel("SYS: - | COMP: -")
        self.sys_info_label.setStyleSheet("color: #a6adc8; font-size: 12px;")

        status_layout.addWidget(self.mode_badge)
        status_layout.addWidget(self.armed_badge)
        status_layout.addStretch()
        status_layout.addWidget(self.sys_info_label)

        main_layout.addWidget(status_box)

        # 2. Battery Monitoring Card (FR-05)
        battery_box = QGroupBox("BATTERY MONITORING")
        battery_box.setStyleSheet(
            """
            QGroupBox {
                color: #cdd6f4;
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
            """
        )
        battery_layout = QVBoxLayout(battery_box)

        bat_header = QHBoxLayout()
        self.battery_val_label = QLabel("100.0%")
        self.battery_val_label.setStyleSheet("color: #a6e3a1; font-size: 18px; font-weight: bold;")

        self.battery_status_badge = QLabel("NORMAL")
        self.battery_status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.battery_status_badge.setStyleSheet(
            """
            QLabel {
                background-color: #a6e3a1;
                color: #11111b;
                font-weight: bold;
                font-size: 11px;
                padding: 3px 8px;
                border-radius: 4px;
            }
            """
        )
        bat_header.addWidget(QLabel("LEVEL:"))
        bat_header.addWidget(self.battery_val_label)
        bat_header.addStretch()
        bat_header.addWidget(self.battery_status_badge)

        self.battery_bar = QProgressBar()
        self.battery_bar.setRange(0, 100)
        self.battery_bar.setValue(100)
        self.battery_bar.setTextVisible(False)
        self.battery_bar.setStyleSheet(
            """
            QProgressBar {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                height: 14px;
            }
            QProgressBar::chunk {
                background-color: #a6e3a1;
                border-radius: 5px;
            }
            """
        )

        battery_layout.addLayout(bat_header)
        battery_layout.addWidget(self.battery_bar)

        main_layout.addWidget(battery_box)

        # 3. Telemetry Parameter Grid (FR-04)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)

        self.card_altitude = MetricCard("Altitude", "m")
        self.card_speed = MetricCard("Ground Speed", "m/s")
        self.card_heading = MetricCard("Heading", "°")
        self.card_lat = MetricCard("Latitude", "°")
        self.card_lon = MetricCard("Longitude", "°")
        self.card_time = MetricCard("Telemetry Time", "UTC")

        grid_layout.addWidget(self.card_altitude, 0, 0)
        grid_layout.addWidget(self.card_speed, 0, 1)
        grid_layout.addWidget(self.card_heading, 0, 2)
        grid_layout.addWidget(self.card_lat, 1, 0)
        grid_layout.addWidget(self.card_lon, 1, 1)
        grid_layout.addWidget(self.card_time, 1, 2)

        main_layout.addLayout(grid_layout)

    def update_telemetry(self, telemetry: TelemetryPayload) -> None:
        """Update all display elements with latest verified telemetry data."""
        # Flight Mode
        self.mode_badge.setText(f"MODE: {telemetry.flight_mode}")
        # Armed Status
        if telemetry.armed:
            self.armed_badge.setText("ARMED")
            self.armed_badge.setStyleSheet(
                """
                QLabel {
                    background-color: #f38ba8;
                    color: #11111b;
                    font-weight: bold;
                    font-size: 14px;
                    padding: 6px 14px;
                    border: 1px solid #f38ba8;
                    border-radius: 6px;
                }
                """
            )
        else:
            self.armed_badge.setText("DISARMED")
            self.armed_badge.setStyleSheet(
                """
                QLabel {
                    background-color: #313244;
                    color: #6c7086;
                    font-weight: bold;
                    font-size: 14px;
                    padding: 6px 14px;
                    border: 1px solid #45475a;
                    border-radius: 6px;
                }
                """
            )

        self.sys_info_label.setText(f"SYS: {telemetry.system_id} | COMP: {telemetry.component_id}")

        # Battery (FR-05)
        self.battery_val_label.setText(f"{telemetry.battery:.1f}%")
        self.battery_bar.setValue(int(telemetry.battery))
        status = BatteryStatus.from_percentage(telemetry.battery)
        self.battery_status_badge.setText(status.value)

        # Style battery bar and badge according to status
        if status == BatteryStatus.NORMAL:
            chunk_color = "#a6e3a1"  # Soft Green
            badge_bg = "#a6e3a1"
            badge_fg = "#11111b"
        elif status == BatteryStatus.WARNING:
            chunk_color = "#f9e2af"  # Soft Amber
            badge_bg = "#f9e2af"
            badge_fg = "#11111b"
        elif status == BatteryStatus.CRITICAL:
            chunk_color = "#fab387"  # Peach / Orange
            badge_bg = "#fab387"
            badge_fg = "#11111b"
        else:  # EMERGENCY
            chunk_color = "#f38ba8"  # Danger Red
            badge_bg = "#f38ba8"
            badge_fg = "#11111b"

        self.battery_status_badge.setStyleSheet(
            f"background-color: {badge_bg}; color: {badge_fg}; font-weight: bold; "
            "font-size: 11px; padding: 3px 8px; border-radius: 4px;"
        )
        self.battery_bar.setStyleSheet(
            f"QProgressBar {{ background-color: #313244; border: 1px solid #45475a; "
            f"border-radius: 6px; height: 14px; }} "
            f"QProgressBar::chunk {{ background-color: {chunk_color}; border-radius: 5px; }}"
        )
        self.battery_val_label.setStyleSheet(f"color: {chunk_color}; font-size: 18px; font-weight: bold;")

        # Metrics (FR-04)
        self.card_altitude.set_value(f"{telemetry.altitude:.1f}", f"AGL: {telemetry.altitude:.1f} m")
        speed_kmh = telemetry.ground_speed * 3.6
        self.card_speed.set_value(f"{telemetry.ground_speed:.1f}", f"≈ {speed_kmh:.1f} km/h")

        compass_dir = self._heading_to_compass(telemetry.heading)
        self.card_heading.set_value(f"{telemetry.heading:.1f}", f"Heading: {compass_dir}")

        lat_hemi = "N" if telemetry.latitude >= 0 else "S"
        lon_hemi = "E" if telemetry.longitude >= 0 else "W"
        self.card_lat.set_value(f"{telemetry.latitude:.5f}", f"{abs(telemetry.latitude):.4f}° {lat_hemi}")
        self.card_lon.set_value(f"{telemetry.longitude:.5f}", f"{abs(telemetry.longitude):.4f}° {lon_hemi}")

        time_part = telemetry.timestamp.split("T")[-1].replace("Z", "") if "T" in telemetry.timestamp else telemetry.timestamp
        self.card_time.set_value(time_part, "ISO 8601")

    @staticmethod
    def _heading_to_compass(heading: float) -> str:
        dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        idx = int((heading + 11.25) / 22.5) % 16
        return dirs[idx]
