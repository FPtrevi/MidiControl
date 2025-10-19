"""
Application configuration settings.
"""
import os
from typing import Tuple, Dict, Any

# MIDI Settings
DEFAULT_MIDI_CHANNEL: int = 1
MIDI_CHANNEL_RANGE: Tuple[int, int] = (1, 16)
SCENE_NUMBER_RANGE: Tuple[int, int] = (1, 128)

# GUI Settings
WINDOW_TITLE: str = "MIDI 믹서 설정"
WINDOW_SIZE: Tuple[int, int] = (320, 480)
WINDOW_RESIZABLE: Tuple[bool, bool] = (False, True)

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Threading
MIDI_THREAD_DAEMON: bool = True
MIDI_THREAD_TIMEOUT: float = 1.0
PORT_WATCH_INTERVAL_SEC: float = float(os.getenv("PORT_WATCH_INTERVAL_SEC", "1.0"))

# MIDI Message Types
NOTE_ON_TYPE: str = "note_on"
NOTE_OFF_TYPE: str = "note_off"
CONTROL_CHANGE_TYPE: str = "control_change"
PROGRAM_CHANGE_TYPE: str = "program_change"

# Network Settings
DEFAULT_DM3_IP: str = "192.168.4.2"
DEFAULT_DM3_PORT: int = 49900
DEFAULT_QU5_IP: str = "192.168.5.10"
DEFAULT_QU5_PORT: int = 51325
DEFAULT_QU5_CHANNEL: int = 1

# Performance Settings
MAX_MIDI_MESSAGES_PER_UPDATE: int = 100
GUI_UPDATE_INTERVAL_MS: int = 10
PING_CACHE_INTERVAL_SEC: float = 3.0

# Validation Settings
VALID_MIXER_TYPES: Tuple[str, ...] = ("DM3", "Qu-5", "Qu-6", "Qu-7")
VALID_LOG_LEVELS: Tuple[str, ...] = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

def get_config() -> Dict[str, Any]:
    """Get all configuration settings as a dictionary."""
    return {
        "midi": {
            "default_channel": DEFAULT_MIDI_CHANNEL,
            "channel_range": MIDI_CHANNEL_RANGE,
            "scene_range": SCENE_NUMBER_RANGE,
        },
        "gui": {
            "title": WINDOW_TITLE,
            "size": WINDOW_SIZE,
            "resizable": WINDOW_RESIZABLE,
        },
        "logging": {
            "level": LOG_LEVEL,
            "format": LOG_FORMAT,
        },
        "threading": {
            "midi_daemon": MIDI_THREAD_DAEMON,
            "midi_timeout": MIDI_THREAD_TIMEOUT,
            "port_watch_interval": PORT_WATCH_INTERVAL_SEC,
        },
        "network": {
            "dm3_ip": DEFAULT_DM3_IP,
            "dm3_port": DEFAULT_DM3_PORT,
            "qu5_ip": DEFAULT_QU5_IP,
            "qu5_port": DEFAULT_QU5_PORT,
            "qu5_channel": DEFAULT_QU5_CHANNEL,
        },
        "performance": {
            "max_midi_messages": MAX_MIDI_MESSAGES_PER_UPDATE,
            "gui_update_interval": GUI_UPDATE_INTERVAL_MS,
            "ping_cache_interval": PING_CACHE_INTERVAL_SEC,
        },
    }

def validate_config() -> bool:
    """Validate configuration settings."""
    try:
        # Validate log level
        if LOG_LEVEL not in VALID_LOG_LEVELS:
            return False
        
        # Validate ranges
        if not (1 <= DEFAULT_MIDI_CHANNEL <= 16):
            return False
        
        if not (1 <= MIDI_CHANNEL_RANGE[0] <= MIDI_CHANNEL_RANGE[1] <= 16):
            return False
        
        if not (1 <= SCENE_NUMBER_RANGE[0] <= SCENE_NUMBER_RANGE[1] <= 128):
            return False
        
        # Validate network settings
        if not (1 <= DEFAULT_DM3_PORT <= 65535):
            return False
        
        if not (1 <= DEFAULT_QU5_PORT <= 65535):
            return False
        
        if not (1 <= DEFAULT_QU5_CHANNEL <= 16):
            return False
        
        return True
    except Exception:
        return False
