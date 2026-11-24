"""Telemetry Logging System supporting JSONL and CSV formats (FR-08)."""

from __future__ import annotations

import csv
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from communication.protocol import ConnectionStatus, TelemetryPayload, current_iso_timestamp

logger = logging.getLogger(__name__)


class TelemetryLogger:
    """Thread-safe telemetry logger writing structured JSONL or CSV records."""

    def __init__(
        self,
        log_dir: str = "logs",
        format_type: str = "jsonl",
        file_prefix: str = "telemetry",
        enabled: bool = True,
    ) -> None:
        self.log_dir = Path(log_dir)
        self.format_type = format_type.lower()
        self.file_prefix = file_prefix
        self.enabled = enabled

        self._lock = threading.Lock()
        self._file = None
        self._csv_writer = None
        self.current_filepath: Optional[Path] = None

        if self.enabled:
            self._init_logfile()

    def _init_logfile(self) -> None:
        """Initialize log directory and current session file."""
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"{self.file_prefix}_{timestamp_str}.{self.format_type}"
            self.current_filepath = self.log_dir / filename

            self._file = open(self.current_filepath, mode="a", encoding="utf-8", newline="", buffering=1)

            if self.format_type == "csv":
                fieldnames = [
                    "timestamp",
                    "connection_status",
                    "validation_status",
                    "system_id",
                    "component_id",
                    "latitude",
                    "longitude",
                    "altitude",
                    "ground_speed",
                    "heading",
                    "battery",
                    "flight_mode",
                    "armed",
                    "errors",
                    "raw_payload",
                ]
                self._csv_writer = csv.DictWriter(self._file, fieldnames=fieldnames)
                if self._file.tell() == 0:
                    self._csv_writer.writeheader()

            logger.info("TelemetryLogger opened log file: %s", self.current_filepath)
        except OSError as e:
            logger.error("Failed to initialize telemetry log file: %s", e)
            self.enabled = False

    def log(
        self,
        connection_status: Union[ConnectionStatus, str],
        validation_status: bool,
        payload: Optional[Union[TelemetryPayload, Dict[str, Any]]] = None,
        errors: Optional[List[str]] = None,
        timestamp: Optional[str] = None,
    ) -> None:
        """Write an entry to the log file."""
        if not self.enabled or self._file is None:
            return

        ts = timestamp or current_iso_timestamp()
        conn_str = connection_status.value if isinstance(connection_status, ConnectionStatus) else str(connection_status)
        val_str = "VALID" if validation_status else "INVALID"
        err_list = errors or []

        # Convert payload to dict
        if isinstance(payload, TelemetryPayload):
            payload_dict = payload.to_dict()
        elif isinstance(payload, dict):
            payload_dict = payload
        else:
            payload_dict = {}

        record: Dict[str, Any] = {
            "timestamp": ts,
            "connection_status": conn_str,
            "validation_status": val_str,
            "telemetry": payload_dict,
            "errors": err_list,
        }

        with self._lock:
            try:
                if self.format_type == "jsonl":
                    self._file.write(json.dumps(record) + "\n")
                elif self.format_type == "csv" and self._csv_writer:
                    row = {
                        "timestamp": ts,
                        "connection_status": conn_str,
                        "validation_status": val_str,
                        "system_id": payload_dict.get("system_id", ""),
                        "component_id": payload_dict.get("component_id", ""),
                        "latitude": payload_dict.get("latitude", ""),
                        "longitude": payload_dict.get("longitude", ""),
                        "altitude": payload_dict.get("altitude", ""),
                        "ground_speed": payload_dict.get("ground_speed", ""),
                        "heading": payload_dict.get("heading", ""),
                        "battery": payload_dict.get("battery", ""),
                        "flight_mode": payload_dict.get("flight_mode", ""),
                        "armed": payload_dict.get("armed", ""),
                        "errors": "; ".join(err_list),
                        "raw_payload": json.dumps(payload_dict) if payload_dict else "",
                    }
                    self._csv_writer.writerow(row)
                self._file.flush()
            except Exception as e:
                logger.error("Error writing telemetry log record: %s", e)

    def close(self) -> None:
        """Flush and close active log file."""
        with self._lock:
            if self._file:
                try:
                    self._file.flush()
                    self._file.close()
                except OSError as e:
                    logger.warning("Error closing log file: %s", e)
                finally:
                    self._file = None
                    self._csv_writer = None
                    logger.info("TelemetryLogger closed")

    def __enter__(self) -> TelemetryLogger:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
