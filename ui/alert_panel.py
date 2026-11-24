"""Alert Panel and Connection Status Panel for GCS Dashboard."""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from communication.protocol import AlertCategory, AlertSeverity, ConnectionStatus
from gcs.alerts import Alert


class AlertPanel(QWidget):
    """Panel showing communication link status, telemetry parsing statistics, and alert logs."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        # 1. Connection & Link Status (FR-07)
        conn_box = QGroupBox("COMMUNICATION LINK & TELEMETRY HEALTH")
        conn_box.setStyleSheet(
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
        conn_layout = QVBoxLayout(conn_box)

        status_row = QHBoxLayout()

        # Connection status badge
        self.conn_badge = QLabel("DISCONNECTED")
        self.conn_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.conn_badge.setStyleSheet(
            """
            QLabel {
                background-color: #313244;
                color: #6c7086;
                font-weight: bold;
                font-size: 13px;
                padding: 6px 16px;
                border: 1px solid #45475a;
                border-radius: 6px;
            }
            """
        )

        self.last_packet_label = QLabel("Last Packet: None")
        self.last_packet_label.setStyleSheet("color: #bac2de; font-size: 12px;")

        status_row.addWidget(self.conn_badge)
        status_row.addWidget(self.last_packet_label)
        status_row.addStretch()

        # Link Statistics
        stats_row = QHBoxLayout()
        self.stat_total = QLabel("Total: 0")
        self.stat_valid = QLabel("Valid: 0")
        self.stat_rejected = QLabel("Rejected: 0")
        self.stat_rate = QLabel("Success Rate: 100.0%")

        for lbl in (self.stat_total, self.stat_valid, self.stat_rejected, self.stat_rate):
            lbl.setStyleSheet("color: #a6adc8; font-size: 11px;")
            stats_row.addWidget(lbl)
        stats_row.addStretch()

        conn_layout.addLayout(status_row)
        conn_layout.addLayout(stats_row)

        main_layout.addWidget(conn_box)

        # 2. Alerts Table (FR-06)
        alerts_box = QGroupBox("SYSTEM & FLIGHT ALERTS")
        alerts_box.setStyleSheet(
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
        alerts_layout = QVBoxLayout(alerts_box)

        # Alerts control bar
        ctrl_bar = QHBoxLayout()
        self.alert_count_label = QLabel("0 active alerts")
        self.alert_count_label.setStyleSheet("color: #a6adc8; font-size: 12px;")

        self.clear_btn = QPushButton("Clear History")
        self.clear_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45475a;
            }
            """
        )
        self.clear_btn.clicked.connect(self.clear_table)

        ctrl_bar.addWidget(self.alert_count_label)
        ctrl_bar.addStretch()
        ctrl_bar.addWidget(self.clear_btn)
        alerts_layout.addLayout(ctrl_bar)

        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["TIME", "SEVERITY", "CATEGORY", "DESCRIPTION"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(
            """
            QTableWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 6px;
                gridline-color: #313244;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #2b2b3d;
                color: #89b4fa;
                font-weight: bold;
                border: 1px solid #313244;
                padding: 4px 6px;
            }
            """
        )
        alerts_layout.addWidget(self.table)

        main_layout.addWidget(alerts_box)

    def update_connection_status(self, status: ConnectionStatus, seconds_ago: float) -> None:
        """Update connection badge and last packet text."""
        if status == ConnectionStatus.CONNECTED:
            self.conn_badge.setText("CONNECTED")
            self.conn_badge.setStyleSheet(
                """
                QLabel {
                    background-color: #a6e3a1;
                    color: #11111b;
                    font-weight: bold;
                    font-size: 13px;
                    padding: 6px 16px;
                    border: 1px solid #a6e3a1;
                    border-radius: 6px;
                }
                """
            )
            self.last_packet_label.setText(f"Last Packet: {seconds_ago:.1f}s ago")
        elif status == ConnectionStatus.TIMEOUT:
            self.conn_badge.setText("TIMEOUT")
            self.conn_badge.setStyleSheet(
                """
                QLabel {
                    background-color: #f38ba8;
                    color: #11111b;
                    font-weight: bold;
                    font-size: 13px;
                    padding: 6px 16px;
                    border: 1px solid #f38ba8;
                    border-radius: 6px;
                }
                """
            )
            self.last_packet_label.setText(f"Last Packet: {seconds_ago:.1f}s ago (LOST)")
        else:  # DISCONNECTED
            self.conn_badge.setText("DISCONNECTED")
            self.conn_badge.setStyleSheet(
                """
                QLabel {
                    background-color: #313244;
                    color: #6c7086;
                    font-weight: bold;
                    font-size: 13px;
                    padding: 6px 16px;
                    border: 1px solid #45475a;
                    border-radius: 6px;
                }
                """
            )
            self.last_packet_label.setText("Last Packet: None")

    def update_statistics(self, total: int, valid: int, rejected: int, success_rate: float) -> None:
        """Update link packet counters."""
        self.stat_total.setText(f"Total: {total}")
        self.stat_valid.setText(f"Valid: {valid}")
        self.stat_rejected.setText(f"Rejected: {rejected}")
        self.stat_rate.setText(f"Success Rate: {success_rate:.1f}%")

    def add_alert(self, alert: Alert) -> None:
        """Insert a new alert at the top of the table."""
        self.table.insertRow(0)

        # Format time
        time_part = alert.timestamp.split("T")[-1].replace("Z", "") if "T" in alert.timestamp else alert.timestamp

        sev_str = alert.severity.value if isinstance(alert.severity, AlertSeverity) else str(alert.severity)
        cat_str = alert.category.value if isinstance(alert.category, AlertCategory) else str(alert.category)

        item_time = QTableWidgetItem(time_part)
        item_sev = QTableWidgetItem(sev_str)
        item_cat = QTableWidgetItem(cat_str)
        item_desc = QTableWidgetItem(alert.description)

        # Style based on severity
        if sev_str in ("EMERGENCY", "CRITICAL"):
            color = QColor("#f38ba8")
        elif sev_str == "WARNING":
            color = QColor("#f9e2af")
        else:
            color = QColor("#89b4fa")

        for item in (item_time, item_sev, item_cat, item_desc):
            item.setForeground(color)

        self.table.setItem(0, 0, item_time)
        self.table.setItem(0, 1, item_sev)
        self.table.setItem(0, 2, item_cat)
        self.table.setItem(0, 3, item_desc)

        count = self.table.rowCount()
        self.alert_count_label.setText(f"{count} recorded alert{'s' if count != 1 else ''}")

    def clear_table(self) -> None:
        """Clear all entries in alert table."""
        self.table.setRowCount(0)
        self.alert_count_label.setText("0 recorded alerts")
