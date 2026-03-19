"""Structured logging: JSON-friendly bound logger."""

from __future__ import annotations

import logging
from typing import Any


class BoundLogger:
    def __init__(self, logger: logging.Logger, context: dict[str, Any]) -> None:
        self._logger = logger
        self._context = context

    def bind(self, **kwargs: Any) -> BoundLogger:
        return BoundLogger(self._logger, {**self._context, **kwargs})

    def _fmt(self, msg: str) -> str:
        if not self._context:
            return msg
        ctx = " ".join(f"{k}={v}" for k, v in self._context.items())
        return f"{msg} [{ctx}]"

    def info(self, msg: str, **kwargs: Any) -> None:
        self._logger.info(self._fmt(msg), **kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        self._logger.warning(self._fmt(msg), **kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        self._logger.error(self._fmt(msg), **kwargs)

    def debug(self, msg: str, **kwargs: Any) -> None:
        self._logger.debug(self._fmt(msg), **kwargs)


def get_logger(name: str) -> BoundLogger:
    return BoundLogger(logging.getLogger(name), {})
