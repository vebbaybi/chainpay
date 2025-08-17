#payday\infra\logger.py
"""
infra/logger.py

Centralized logger factory for the payday project.

Env controls:
- WORKHOUR_LOGLEVEL: logging level (default: INFO)
- WORKHOUR_LOGFILE: optional log file path

Idempotent: no duplicate handlers per logger name.
"""

import logging
import os
import sys


class _LoggerConfig:
    """Internal config derived from environment variables (no dataclass, no type hints)."""

    def __init__(self, level_name="INFO", logfile=None):
        self.level_name = level_name
        self.logfile = logfile

    @classmethod
    def from_env(cls):
        level = os.getenv("WORKHOUR_LOGLEVEL", "INFO").strip().upper()
        logfile = os.getenv("WORKHOUR_LOGFILE")
        logfile = logfile.strip() if logfile else None
        return cls(level_name=level, logfile=logfile)

    @property
    def level(self):
        # Map string to logging level, fallback to INFO
        return getattr(logging, self.level_name, logging.INFO)


class LoggerFactory:
    """
    Provides configured loggers with stderr + optional file handlers.

    Usage:
        from payday.infra import LoggerFactory
        log = LoggerFactory.get_logger(__name__)
    """

    _formatter = logging.Formatter("[%(levelname)s] %(message)s")
    _configured_names = set()

    @classmethod
    def get_logger(cls, name):
        logger = logging.getLogger(name)
        if name in cls._configured_names:
            return logger  # Already configured

        cfg = _LoggerConfig.from_env()

        # Always attach stderr handler
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setFormatter(cls._formatter)
        logger.addHandler(stderr_handler)

        # Optionally add file handler
        if cfg.logfile:
            try:
                file_handler = logging.FileHandler(cfg.logfile, encoding="utf-8")
                file_handler.setFormatter(cls._formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                logger.error("Failed to set up file logging at %s: %s", cfg.logfile, e)

        # Apply level and mark configured
        logger.setLevel(cfg.level)
        cls._configured_names.add(name)
        return logger
