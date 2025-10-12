"""
Logging utilities with thread-safe considerations.
"""
import logging
import threading
from typing import Optional
from config.settings import LOG_LEVEL, LOG_FORMAT


class ThreadSafeLogger:
    """
    Thread-safe logger wrapper to avoid GIL issues with logging.
    """
    
    def __init__(self, name: str, level: str = LOG_LEVEL):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(getattr(logging, level.upper()))
        self._lock = threading.Lock()
        
        # Avoid duplicate handlers
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(LOG_FORMAT)
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
    
    def info(self, message: str) -> None:
        with self._lock:
            self._logger.info(message)
    
    def error(self, message: str) -> None:
        with self._lock:
            self._logger.error(message)
    
    def warning(self, message: str) -> None:
        with self._lock:
            self._logger.warning(message)
    
    def debug(self, message: str) -> None:
        with self._lock:
            self._logger.debug(message)


def get_logger(name: str, level: str = LOG_LEVEL) -> ThreadSafeLogger:
    """Get a thread-safe logger instance."""
    return ThreadSafeLogger(name, level)
