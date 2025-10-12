"""
Soft key control service for Qu series mixers.
Based on Allen & Heath Qu 5/6/7 MIDI Protocol documentation.
"""
from typing import Optional, Dict, Any
from model.base_service import BaseMidiService
from config.mixer_config import get_mixer_config
from config.settings import SCENE_NUMBER_RANGE
from utils.logger import get_logger


class SoftKeyService(BaseMidiService):
    """
    Handles soft key control operations for Qu series mixers.
    Thread-safe implementation for macOS + mido environment.
    """
    
    def __init__(self, mixer_name: str, midi_backend):
        super().__init__()
        self.logger = get_logger(__name__)
        self.mixer_name = mixer_name
        self.midi_backend = midi_backend
        self.config = get_mixer_config(mixer_name)
        
        if not self.config:
            self.logger.error(f"지원하지 않는 믹서: {mixer_name}")
            raise ValueError(f"Unsupported mixer: {mixer_name}")
    
    def handle_mute(self, note: int, velocity: int, channel: int) -> None:
        """SoftKeyService doesn't handle mute operations."""
        pass
    
    def handle_scene(self, note: int, channel: int) -> None:
        """SoftKeyService doesn't handle scene operations."""
        pass
    
    def handle_softkey(self, note: int, velocity: int, channel: int) -> None:
        """Handle soft key control based on mixer protocol."""
        protocol = self.config.get("softkey_protocol", "unknown")
        
        if protocol == "cc":
            self._handle_cc_softkey(note, velocity, channel)
        elif protocol == "nrpn":
            self._handle_nrpn_softkey(note, velocity, channel)
        else:
            self.logger.error(f"지원하지 않는 소프트키 프로토콜: {protocol}")
    
    def _handle_cc_softkey(self, note: int, velocity: int, channel: int) -> None:
        """
        Handle soft key using Note On/Off protocol.
        Based on Qu 5/6/7 documentation, soft keys use Note 48-59 (0x30-0x3B).
        - Soft Key 1: Note 48 (0x30)
        - Soft Key 7: Note 54 (0x36)
        - Soft Key 12: Note 59 (0x3B)
        """
        # Soft key number (1-12 for Qu series)
        softkey_number = note + 1
        
        # Validate soft key number
        if not (1 <= softkey_number <= 12):
            self.logger.error(f"유효하지 않은 소프트키 번호: {softkey_number}")
            return
        
        # Soft keys use Note 48-59 (0x30-0x3B) for Soft Keys 1-12
        note_number = 48 + (softkey_number - 1)  # Note 48 for key 1, 59 for key 12
        
        # Send Note On or Note Off based on velocity
        if velocity >= 1:
            # Press: Send Note On with velocity 127 (0x7F)
            success = self.midi_backend.send_note_on(note_number, 127, channel)
            action = "Press"
        else:
            # Release: Send Note Off with velocity 0
            success = self.midi_backend.send_note_off(note_number, 0, channel)
            action = "Release"
        
        if success:
            self.logger.info(f"소프트키 {action}: 키 {softkey_number} (Note {note_number} = 0x{note_number:02X})")
        else:
            self.logger.error("소프트키 전송 실패")
    
    def _handle_nrpn_softkey(self, note: int, velocity: int, channel: int) -> None:
        """
        Handle soft key using NRPN protocol (if supported).
        """
        # Soft key number (1-12 for Qu series)
        softkey_number = note + 1
        
        # Validate soft key number
        if not (1 <= softkey_number <= 12):
            self.logger.error(f"유효하지 않은 소프트키 번호: {softkey_number}")
            return
        
        # Get NRPN parameters from config
        nrpn_params = self.config.get("softkey_nrpn_params", {})
        parameter_msb = nrpn_params.get("msb", 0x01)  # Soft key parameter group
        parameter_lsb = softkey_number - 1  # Soft key index (0-based)
        
        # Soft key press/release value
        press_value = 1 if velocity >= 1 else 0
        
        # Send NRPN sequence
        sequence = nrpn_params.get("sequence", [99, 98, 6, 38])
        values = [parameter_msb, parameter_lsb, 0, press_value]
        
        for cc, value in zip(sequence, values):
            success = self.midi_backend.send_control_change(cc, value, channel)
            if not success:
                self.logger.error(f"NRPN CC#{cc} 전송 실패")
                return
        
        action = "Press" if press_value == 1 else "Release"
        self.logger.info(f"NRPN 소프트키 {action}: 키 {softkey_number}")
    
    def update_mixer_config(self, mixer_name: str) -> None:
        """Update mixer configuration."""
        self.mixer_name = mixer_name
        self.config = get_mixer_config(mixer_name)
        
        if not self.config:
            self.logger.error(f"지원하지 않는 믹서: {mixer_name}")
            raise ValueError(f"Unsupported mixer: {mixer_name}")
        
        self.logger.info(f"믹서 설정 업데이트: {mixer_name}")
