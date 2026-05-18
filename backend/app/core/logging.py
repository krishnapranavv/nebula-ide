"""
Structured logging configuration.
JSON format in production, human-readable in development.
"""
import logging
import sys
from app.core.config import settings


def setup_logging():
    level = logging.DEBUG if settings.DEBUG else logging.INFO

    fmt = (
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
        if settings.ENVIRONMENT == "development"
        else '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
    )

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Quiet noisy third-party loggers
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("docker").setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        f"Logging initialised — level={logging.getLevelName(level)} env={settings.ENVIRONMENT}"
    )
