"""Structured logging configuration for TuneUp Alpha."""

from __future__ import annotations

import contextvars
import json
import logging
import logging.handlers
import sys
import uuid
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

# Context variable for correlation ID
correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)


class LogLevel(str, Enum):
    """Available log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class LogOutput(str, Enum):
    """Log output destinations."""

    CONSOLE = "console"
    FILE = "file"
    BOTH = "both"


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if present
        corr_id = correlation_id.get()
        if corr_id:
            log_data["correlation_id"] = corr_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from the record
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter for console output."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record in human-readable format."""
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname
        name = record.name

        # Add correlation ID if present
        corr_id = correlation_id.get()
        corr_str = f" [{corr_id[:8]}]" if corr_id else ""

        # Build the message
        message = record.getMessage()

        # Add extra fields if present
        extra_str = ""
        if hasattr(record, "extra_fields"):
            extra_parts = [f"{k}={v}" for k, v in record.extra_fields.items()]
            if extra_parts:
                extra_str = f" | {', '.join(extra_parts)}"

        formatted = f"{timestamp} {level:8} {name}{corr_str}: {message}{extra_str}"

        # Add exception if present
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)

        return formatted


class LoggingConfig:
    """Configuration for logging system."""

    def __init__(
        self,
        level: LogLevel = LogLevel.INFO,
        output: LogOutput = LogOutput.CONSOLE,
        log_file: Path | None = None,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        structured: bool = False,
    ) -> None:
        """
        Initialize logging configuration.

        Args:
            level: Minimum log level to output
            output: Where to send logs (console, file, or both)
            log_file: Path to log file (required if output is file or both)
            max_bytes: Maximum size of log file before rotation
            backup_count: Number of backup log files to keep
            structured: Whether to use structured JSON logging
        """
        self.level = level
        self.output = output
        self.log_file = log_file
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.structured = structured

        # Validate configuration
        if output in (LogOutput.FILE, LogOutput.BOTH) and log_file is None:
            raise ValueError("log_file is required when output is 'file' or 'both'")


def setup_logging(config: LoggingConfig | None = None) -> None:
    """
    Configure logging for the application.

    Args:
        config: Logging configuration. If None, uses default configuration.
    """
    if config is None:
        config = LoggingConfig()

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level.value))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Choose formatter
    formatter = StructuredFormatter() if config.structured else HumanReadableFormatter()

    # Add console handler if needed
    if config.output in (LogOutput.CONSOLE, LogOutput.BOTH):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Add file handler if needed
    if config.output in (LogOutput.FILE, LogOutput.BOTH) and config.log_file:
        # Ensure log directory exists
        config.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Use rotating file handler for log rotation
        file_handler = logging.handlers.RotatingFileHandler(
            config.log_file,
            maxBytes=config.max_bytes,
            backupCount=config.backup_count,
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def set_correlation_id(corr_id: str | None = None) -> str:
    """
    Set correlation ID for tracking related operations.

    Args:
        corr_id: Correlation ID to set. If None, generates a new UUID.

    Returns:
        The correlation ID that was set
    """
    if corr_id is None:
        corr_id = str(uuid.uuid4())
    correlation_id.set(corr_id)
    return corr_id


def clear_correlation_id() -> None:
    """Clear the current correlation ID."""
    correlation_id.set(None)


def log_with_extra(logger: logging.Logger, level: int, message: str, **kwargs: Any) -> None:
    """
    Log a message with extra fields.

    Args:
        logger: Logger instance
        level: Log level
        message: Log message
        **kwargs: Extra fields to include in the log
    """
    extra = {"extra_fields": kwargs}
    logger.log(level, message, extra=extra)


class AuditLogger:
    """Logger for DNS change audit trail."""

    def __init__(self, logger_name: str = "tuneup_alpha.audit") -> None:
        """Initialize audit logger."""
        self.logger = get_logger(logger_name)

    def log_zone_change(
        self,
        action: str,
        zone_name: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Log a zone configuration change.

        Args:
            action: Action performed (create, update, delete)
            zone_name: Name of the zone
            details: Additional details about the change
        """
        extra_fields = {
            "audit_type": "zone_change",
            "action": action,
            "zone_name": zone_name,
        }
        if details:
            extra_fields.update(details)

        log_with_extra(
            self.logger,
            logging.INFO,
            f"Zone {action}: {zone_name}",
            **extra_fields,
        )

    def log_record_change(
        self,
        action: str,
        zone_name: str,
        record_label: str,
        record_type: str,
        record_value: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Log a DNS record change.

        Args:
            action: Action performed (create, update, delete)
            zone_name: Name of the zone
            record_label: Record label
            record_type: Record type (A, CNAME, etc.)
            record_value: Record value
            details: Additional details about the change
        """
        extra_fields = {
            "audit_type": "record_change",
            "action": action,
            "zone_name": zone_name,
            "record_label": record_label,
            "record_type": record_type,
            "record_value": record_value,
        }
        if details:
            extra_fields.update(details)

        log_with_extra(
            self.logger,
            logging.INFO,
            f"Record {action}: {record_label}.{zone_name} {record_type} {record_value}",
            **extra_fields,
        )

    def log_nsupdate_execution(
        self,
        zone_name: str,
        dry_run: bool,
        success: bool,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Log nsupdate script execution.

        Args:
            zone_name: Name of the zone
            dry_run: Whether this was a dry run
            success: Whether the execution was successful
            details: Additional details about the execution
        """
        extra_fields = {
            "audit_type": "nsupdate_execution",
            "zone_name": zone_name,
            "dry_run": dry_run,
            "success": success,
        }
        if details:
            extra_fields.update(details)

        status = "succeeded" if success else "failed"
        mode = "dry-run" if dry_run else "live"
        log_with_extra(
            self.logger,
            logging.INFO,
            f"nsupdate {mode} {status} for {zone_name}",
            **extra_fields,
        )
