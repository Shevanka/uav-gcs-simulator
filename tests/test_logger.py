"""Unit tests for TelemetryLogger (FR-08)."""

import json
from pathlib import Path
import pytest
from communication.protocol import ConnectionStatus, TelemetryPayload, current_iso_timestamp
from gcs.logger import TelemetryLogger


def test_jsonl_logger(tmp_path):
    """Test telemetry logger with jsonl format."""
    log_dir = tmp_path / "logs"
    logger = TelemetryLogger(log_dir=str(log_dir), format_type="jsonl", file_prefix="test_telemetry")

    payload = TelemetryPayload(
        timestamp=current_iso_timestamp(),
        system_id=1,
        component_id=1,
        latitude=-7.2756,
        longitude=112.7949,
        altitude=120.0,
        ground_speed=15.0,
        heading=90.0,
        battery=88.0,
        flight_mode="AUTO",
        armed=True,
    )

    logger.log(
        connection_status=ConnectionStatus.CONNECTED,
        validation_status=True,
        payload=payload,
    )
    logger.close()

    log_files = list(log_dir.glob("*.jsonl"))
    assert len(log_files) == 1

    content = log_files[0].read_text(encoding="utf-8")
    lines = content.strip().splitlines()
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["connection_status"] == "CONNECTED"
    assert entry["validation_status"] == "VALID"
    assert entry["telemetry"]["latitude"] == -7.2756


def test_csv_logger(tmp_path):
    """Test telemetry logger with CSV format."""
    log_dir = tmp_path / "logs"
    logger = TelemetryLogger(log_dir=str(log_dir), format_type="csv", file_prefix="test_telemetry")

    payload = TelemetryPayload(
        timestamp=current_iso_timestamp(),
        system_id=1,
        component_id=1,
        latitude=-7.2756,
        longitude=112.7949,
        altitude=120.0,
        ground_speed=15.0,
        heading=90.0,
        battery=88.0,
        flight_mode="AUTO",
        armed=True,
    )

    logger.log(
        connection_status=ConnectionStatus.CONNECTED,
        validation_status=True,
        payload=payload,
    )
    logger.close()

    log_files = list(log_dir.glob("*.csv"))
    assert len(log_files) == 1

    content = log_files[0].read_text(encoding="utf-8")
    lines = content.strip().splitlines()
    # Line 0 is header, Line 1 is data
    assert len(lines) == 2
    assert "timestamp,connection_status,validation_status" in lines[0]
    assert "-7.2756" in lines[1]
