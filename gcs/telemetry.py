"""Telemetry Parser and State Holder for GCS."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from communication.protocol import TelemetryPayload
from gcs.validator import TelemetryValidator

logger = logging.getLogger(__name__)


class ParseResult:
    """Encapsulates the result of parsing and validating a raw telemetry packet."""

    def __init__(
        self,
        success: bool,
        payload: Optional[TelemetryPayload] = None,
        raw_dict: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None,
        raw_data: Optional[bytes] = None,
    ) -> None:
        self.success = success
        self.payload = payload
        self.raw_dict = raw_dict
        self.errors = errors or []
        self.raw_data = raw_data

    @property
    def error_message(self) -> str:
        return "; ".join(self.errors)


class TelemetryProcessor:
    """Parses raw UDP byte payloads, validates them, and maintains telemetry state."""

    def __init__(self) -> None:
        self.last_valid_telemetry: Optional[TelemetryPayload] = None
        self.total_received: int = 0
        self.valid_count: int = 0
        self.rejected_count: int = 0

    @property
    def success_rate(self) -> float:
        """Percentage of successfully parsed and validated packets."""
        if self.total_received == 0:
            return 100.0
        return (self.valid_count / self.total_received) * 100.0

    def process_raw_packet(self, data: bytes) -> ParseResult:
        """Process incoming raw UDP packet bytes.

        Steps:
        1. Decode UTF-8 string.
        2. Parse JSON.
        3. Validate schema and ranges.
        4. If valid, update last_valid_telemetry.
        """
        self.total_received += 1

        # Step 1: Decode
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as ude:
            err = f"Failed to decode UDP packet as UTF-8: {ude}"
            logger.warning(err)
            self.rejected_count += 1
            return ParseResult(success=False, errors=[err], raw_data=data)

        # Step 2: Parse JSON
        try:
            parsed_json = json.loads(text)
        except json.JSONDecodeError as jde:
            err = f"Invalid JSON syntax in packet: {jde}"
            logger.warning(err)
            self.rejected_count += 1
            return ParseResult(success=False, errors=[err], raw_data=data)

        # Step 3: Validate
        is_valid, validation_errors = TelemetryValidator.validate(parsed_json)
        if not is_valid:
            logger.warning("Telemetry packet rejected due to validation errors: %s", validation_errors)
            self.rejected_count += 1
            return ParseResult(
                success=False,
                raw_dict=parsed_json if isinstance(parsed_json, dict) else None,
                errors=validation_errors,
                raw_data=data,
            )

        # Step 4: Construct verified payload and update state
        try:
            payload = TelemetryPayload.from_dict(parsed_json)
            self.last_valid_telemetry = payload
            self.valid_count += 1
            logger.debug("Successfully processed valid telemetry packet (timestamp=%s)", payload.timestamp)
            return ParseResult(
                success=True,
                payload=payload,
                raw_dict=parsed_json,
                raw_data=data,
            )
        except Exception as e:
            err = f"Error converting validated dict to TelemetryPayload: {e}"
            logger.error(err, exc_info=True)
            self.rejected_count += 1
            return ParseResult(
                success=False,
                raw_dict=parsed_json,
                errors=[err],
                raw_data=data,
            )

    def reset_stats(self) -> None:
        """Reset parser statistics counters."""
        self.total_received = 0
        self.valid_count = 0
        self.rejected_count = 0
