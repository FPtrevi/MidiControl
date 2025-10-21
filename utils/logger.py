"""
Logging utilities with thread-safe considerations.
"""
import logging
import threading
from typing import Optional, Dict, Any
from config.settings import LOG_LEVEL, LOG_FORMAT


class ThreadSafeLogger:
    """
    Thread-safe logger wrapper to avoid GIL issues with logging.
    """
    
    def __init__(self, name: str, level: str = LOG_LEVEL):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(getattr(logging, level.upper()))
        self._lock = threading.RLock()  # Use RLock for better thread safety
        self._initialized = False
        self._gui_callback = None  # GUI log callback
        
        # Avoid duplicate handlers
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(LOG_FORMAT)
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._initialized = True
    
    def info(self, message: str) -> None:
        if not self._initialized:
            return
        with self._lock:
            self._logger.info(message)
            self._send_to_gui(message)
    
    def error(self, message: str) -> None:
        if not self._initialized:
            return
        with self._lock:
            self._logger.error(message)
            self._send_to_gui(message)
    
    def warning(self, message: str) -> None:
        if not self._initialized:
            return
        with self._lock:
            self._logger.warning(message)
            self._send_to_gui(message)
    
    def debug(self, message: str) -> None:
        if not self._initialized:
            return
        with self._lock:
            self._logger.debug(message)
            self._send_to_gui(message)
    
    def critical(self, message: str) -> None:
        if not self._initialized:
            return
        with self._lock:
            self._logger.critical(message)
            self._send_to_gui(message)
    
    def exception(self, message: str) -> None:
        if not self._initialized:
            return
        with self._lock:
            self._logger.exception(message)
            self._send_to_gui(message)
    
    def set_gui_callback(self, callback) -> None:
        """Set GUI callback for log messages."""
        with self._lock:
            self._gui_callback = callback
    
    def _send_to_gui(self, message: str) -> None:
        """Send message to GUI if callback is set."""
        if self._gui_callback:
            try:
                self._gui_callback(message)
            except Exception:
                # Ignore GUI callback errors to avoid breaking logging
                pass


def get_logger(name: str, level: str = LOG_LEVEL) -> ThreadSafeLogger:
    """Get a thread-safe logger instance."""
    return ThreadSafeLogger(name, level)
