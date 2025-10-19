"""
Base abstract class for MIDI services with GIL-safe threading considerations.
"""
from abc import ABC, abstractmethod
from typing import Optional, Any
import threading
from queue import Queue, Empty


class BaseMidiService(ABC):
    """
    Abstract base class for MIDI services.
    Designed to be GIL-safe with proper thread communication.
    """
    
    def __init__(self):
        self._message_queue: Queue[Any] = Queue()
        self._shutdown_event = threading.Event()
        self._thread_lock = threading.RLock()  # Use RLock for better thread safety
        self._initialized = False
    
    @abstractmethod
    def handle_mute(self, note: int, velocity: int, channel: int) -> None:
        """Handle mute control messages."""
        pass
    
    @abstractmethod
    def handle_scene(self, note: int, channel: int) -> None:
        """Handle scene call messages."""
        pass
    
    def initialize(self) -> bool:
        """Initialize the service. Override in subclasses if needed."""
        with self._thread_lock:
            if self._initialized:
                return True
            self._initialized = True
            return True
    
    def shutdown(self) -> None:
        """Safely shutdown the service."""
        with self._thread_lock:
            if not self._initialized:
                return
            self._shutdown_event.set()
            self._initialized = False
    
    def is_shutdown(self) -> bool:
        """Check if service is shutdown."""
        return self._shutdown_event.is_set()
    
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized
    
    def _process_message_queue(self) -> None:
        """Process queued messages. Override in subclasses if needed."""
        while not self._message_queue.empty():
            try:
                message = self._message_queue.get_nowait()
                # Process message here in subclasses
                self._message_queue.task_done()
            except Empty:
                break
            except Exception:
                # Log error but continue processing
                pass
