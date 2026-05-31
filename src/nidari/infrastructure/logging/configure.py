"""Centralized logging setup with console output and rotating file handler."""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

import structlog

from ..config.settings import settings

_CONFIGURED = False

_TEXT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_TEXT_DATEFMT = "%Y-%m-%d %H:%M:%S"

# Reduce noise from chatty third-party libraries in non-debug mode
_QUIET_LOGGERS = ("httpx", "httpcore", "urllib3", "asyncio")


def _resolve_log_level() -> int:
    level_name = settings.LOG_LEVEL.upper()
    return getattr(logging, level_name, logging.INFO)


def _build_text_formatter() -> logging.Formatter:
    return logging.Formatter(fmt=_TEXT_FORMAT, datefmt=_TEXT_DATEFMT)


def _build_json_formatter() -> structlog.stdlib.ProcessorFormatter:
    return structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ],
    )


def _configure_structlog() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def _apply_handler_config(handlers: list[logging.Handler], log_level: int) -> None:
    use_json = settings.LOG_FORMAT.lower() == "json"
    formatter: logging.Formatter | structlog.stdlib.ProcessorFormatter
    if use_json:
        _configure_structlog()
        formatter = _build_json_formatter()
    else:
        formatter = _build_text_formatter()

    for handler in handlers:
        handler.setLevel(log_level)
        handler.setFormatter(formatter)


def _build_handlers(log_dir: Path, log_level: int, log_file: str) -> list[logging.Handler]:
    handlers: list[logging.Handler] = []

    if settings.LOG_TO_CONSOLE:
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(log_level)
        handlers.append(console)

    if settings.LOG_TO_FILE:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / log_file
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=settings.LOG_MAX_BYTES,
            backupCount=settings.LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        handlers.append(file_handler)

    return handlers


def _configure_uvicorn_loggers(handlers: list[logging.Handler], log_level: int) -> None:
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers.clear()
        uv_logger.propagate = False
        for handler in handlers:
            uv_logger.addHandler(handler)
        uv_logger.setLevel(log_level if name != "uvicorn.access" else logging.INFO)


def _tune_third_party_loggers() -> None:
    access_level = logging.INFO if settings.DEBUG else logging.WARNING
    logging.getLogger("uvicorn.access").setLevel(access_level)
    quiet_level = logging.WARNING if not settings.DEBUG else logging.INFO
    for name in _QUIET_LOGGERS:
        logging.getLogger(name).setLevel(quiet_level)


def setup_logging(service_name: str = "nidari", log_file: str | None = None) -> logging.Logger:
    """
    Configure root and uvicorn loggers once per process.

    Returns a logger bound to the logging module for startup messages.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return logging.getLogger(service_name)

    log_level = _resolve_log_level()
    log_dir = Path(settings.LOG_DIR)
    resolved_log_file = log_file or settings.LOG_FILE

    handlers = _build_handlers(log_dir, log_level, resolved_log_file)
    if not handlers:
        handlers = [logging.StreamHandler(sys.stdout)]

    _apply_handler_config(handlers, log_level)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(log_level)
    for handler in handlers:
        root.addHandler(handler)

    _configure_uvicorn_loggers(handlers, log_level)
    _tune_third_party_loggers()

    _CONFIGURED = True
    logger = logging.getLogger(service_name)
    logger.info(
        "Logging initialized (level=%s, format=%s, console=%s, file=%s)",
        settings.LOG_LEVEL,
        settings.LOG_FORMAT,
        settings.LOG_TO_CONSOLE,
        settings.LOG_TO_FILE,
    )
    if settings.LOG_TO_FILE:
        logger.info("Log file: %s", log_dir / resolved_log_file)
    return logger
