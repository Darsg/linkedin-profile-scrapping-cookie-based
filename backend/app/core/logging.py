import logging

import structlog

from app.core.config import get_settings


def configure_logging() -> None:
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if get_settings().log_json
        else structlog.dev.ConsoleRenderer()
    )
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]
