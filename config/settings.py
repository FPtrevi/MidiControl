"""
Application configuration settings.
"""
import os

# MIDI Settings
DEFAULT_MIDI_CHANNEL = 1
MIDI_CHANNEL_RANGE = (1, 16)
SCENE_NUMBER_RANGE = (1, 128)

# GUI Settings
WINDOW_TITLE = "MIDI 믹서 설정"
WINDOW_SIZE = (320, 480)
WINDOW_RESIZABLE = (False, True)

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Threading
MIDI_THREAD_DAEMON = True
MIDI_THREAD_TIMEOUT = 1.0
PORT_WATCH_INTERVAL_SEC = float(os.getenv("PORT_WATCH_INTERVAL_SEC", "1.0"))

# MIDI Message Types
NOTE_ON_TYPE = "note_on"
NOTE_OFF_TYPE = "note_off"
CONTROL_CHANGE_TYPE = "control_change"
PROGRAM_CHANGE_TYPE = "program_change"
