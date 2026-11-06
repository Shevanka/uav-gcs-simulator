"""Alert System for GCS anomaly detection."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, List, Optional, Set

from communication.protocol import (
    AlertCategory,
    AlertSeverity,
    BatteryStatus,
    TelemetryPayload,
    current_iso_timestamp,
)

logger = logging.getLogger(__name__)

AlertCallback = Callable[["Alert"], None]


@dataclass
class Alert:
    """Represents a system or flight alert."""
    timestamp: str
    category: AlertCategory
    severity: AlertSeverity
    description: str

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "category": self.category.value if isinstance(self.category, AlertCategory) else str(self.category),
            "severity": self.severity.value if isinstance(self.severity, AlertSeverity) else str(self.severity),
            "description": self.description,
        }


class AlertManager:
    """Detects, aggregates, and dispatches abnormal telemetry and connection alerts."""

    def __init__(
        self,
        min_operational_altitude: float = 0.0,
        max_operational_altitude: float = 500.0,
        battery_critical_threshold: float = 20.0,
        battery_emergency_threshold: float = 10.0,
        max_history: int = 500,
    ) -> None:
        self.min_operational_altitude = min_operational_altitude
        self.max_operational_altitude = max_operational_altitude
        self.battery_critical_threshold = battery_critical_threshold
        self.battery_emergency_threshold = battery_emergency_threshold
        self.max_history = max_history

        self.alerts: List[Alert] = []
        self._listeners: List[AlertCallback] = []
        self._active_alert_keys: Set[str] = set()

    def add_listener(self, callback: AlertCallback) -> None:
        """Register a callback invoked when a new alert is created."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: AlertCallback) -> None:
        """Unregister alert listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def trigger_alert(
        self,
        category: AlertCategory,
        severity: AlertSeverity,
        description: str,
        timestamp: Optional[str] = None,
        dedup_key: Optional[str] = None,
    ) -> Alert:
        """Create, store, and broadcast an alert."""
        ts = timestamp or current_iso_timestamp()
        alert = Alert(
            timestamp=ts,
            category=category,
            severity=severity,
            description=description,
        )

        # Optional deduplication to prevent flooding identical alerts
        if dedup_key:
            if dedup_key in self._active_alert_keys:
                return alert
            self._active_alert_keys.add(dedup_key)

        self.alerts.append(alert)
        if len(self.alerts) > self.max_history:
            self.alerts.pop(0)

        logger.warning(
            "ALERT [%s] [%s] %s: %s",
            alert.timestamp,
            alert.severity.value,
            alert.category.value,
            alert.description,
        )

        for listener in self._listeners:
            try:
                listener(alert)
            except Exception as e:
                logger.error("Error in alert listener callback: %s", e)

        return alert

    def clear_active_key(self, dedup_key: str) -> None:
        """Clear deduplication key when abnormal condition has recovered."""
        self._active_alert_keys.discard(dedup_key)

    def evaluate_telemetry(self, telemetry: TelemetryPayload) -> List[Alert]:
        """Examine telemetry against operational thresholds (Battery & Altitude)."""
        new_alerts: List[Alert] = []

        # 1. Battery Monitoring & Alerts
        if telemetry.battery < self.battery_emergency_threshold:
            alert = self.trigger_alert(
                category=AlertCategory.BATTERY,
                severity=AlertSeverity.EMERGENCY,
                description=f"CRITICAL BATTERY EMERGENCY: Battery level is {telemetry.battery:.1f}% (< {self.battery_emergency_threshold}%)",
                dedup_key="battery_emergency",
            )
            new_alerts.append(alert)
        elif telemetry.battery < self.battery_critical_threshold:
            alert = self.trigger_alert(
                category=AlertCategory.BATTERY,
                severity=AlertSeverity.CRITICAL,
                description=f"Battery critically low: {telemetry.battery:.1f}% (< {self.battery_critical_threshold}%)",
                dedup_key="battery_critical",
            )
            new_alerts.append(alert)
        else:
            self.clear_active_key("battery_emergency")
            self.clear_active_key("battery_critical")

        # 2. Altitude Monitoring & Alerts
        if telemetry.altitude > self.max_operational_altitude:
            alert = self.trigger_alert(
                category=AlertCategory.ALTITUDE,
                severity=AlertSeverity.WARNING,
                description=f"Altitude exceeds operational ceiling: {telemetry.altitude:.1f}m > {self.max_operational_altitude}m",
                dedup_key="altitude_high",
            )
            new_alerts.append(alert)
        elif telemetry.altitude < self.min_operational_altitude:
            alert = self.trigger_alert(
                category=AlertCategory.ALTITUDE,
                severity=AlertSeverity.CRITICAL,
                description=f"Altitude below minimum ground reference: {telemetry.altitude:.1f}m < {self.min_operational_altitude}m",
                dedup_key="altitude_low",
            )
            new_alerts.append(alert)
        else:
            self.clear_active_key("altitude_high")
            self.clear_active_key("altitude_low")

        return new_alerts

    def record_validation_error(self, errors: List[str]) -> Alert:
        """Trigger alert for invalid telemetry packets."""
        err_str = "; ".join(errors)
        return self.trigger_alert(
            category=AlertCategory.VALIDATION,
            severity=AlertSeverity.WARNING,
            description=f"Invalid telemetry packet received: {err_str}",
        )

    def record_connection_timeout(self, seconds_elapsed: float) -> Alert:
        """Trigger alert when communication times out."""
        return self.trigger_alert(
            category=AlertCategory.COMMUNICATION,
            severity=AlertSeverity.CRITICAL,
            description=f"Communication timeout: No telemetry received for {seconds_elapsed:.1f} seconds",
            dedup_key="comm_timeout",
        )

    def record_connection_restored(self) -> Alert:
        """Record connection restored alert."""
        self.clear_active_key("comm_timeout")
        return self.trigger_alert(
            category=AlertCategory.COMMUNICATION,
            severity=AlertSeverity.INFO,
            description="Communication restored: Valid telemetry received",
        )

    def clear_all(self) -> None:
        """Clear all alerts and active deduplication keys."""
        self.alerts.clear()
        self._active_alert_keys.clear()
