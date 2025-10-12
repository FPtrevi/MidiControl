"""
Base abstract class for MIDI services with GIL-safe threading considerations.
"""
from abc import ABC, abstractmethod
from typing import Optional
import threading
from queue import Queue


class BaseMidiService(ABC):
    """
    Abstract base class for MIDI services.
    Designed to be GIL-safe with proper thread communication.
    """
    
    def __init__(self):
        self._message_queue = Queue()
        self._shutdown_event = threading.Event()
        self._thread_lock = threading.Lock()
    
    @abstractmethod
    def handle_mute(self, note: int, velocity: int, channel: int) -> None:
        """Handle mute control messages."""
        pass
    
    @abstractmethod
    def handle_scene(self, note: int, channel: int) -> None:
        """Handle scene call messages."""
        pass
    
    def shutdown(self) -> None:
        """Safely shutdown the service."""
        with self._thread_lock:
            self._shutdown_event.set()
    
    def is_shutdown(self) -> bool:
        """Check if service is shutdown."""
        return self._shutdown_event.is_set()
