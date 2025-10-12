"""
Mute control service with NRPN support for Qu series mixers.
"""
from typing import Optional, Dict, Any
from model.base_service import BaseMidiService
from config.mixer_config import get_mixer_config
from utils.logger import get_logger


class MuteService(BaseMidiService):
    """
    Handles mute control operations with mixer-specific protocols.
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
        """Handle mute control based on mixer protocol."""
        protocol = self.config.get("mute_protocol", "unknown")
        
        if protocol == "nrpn":
            self._handle_nrpn_mute(note, velocity, channel)
        elif protocol == "cc":
            self._handle_cc_mute(note, velocity, channel)
        else:
            self.logger.error(f"지원하지 않는 뮤트 프로토콜: {protocol}")
    
    def handle_scene(self, note: int, channel: int) -> None:
        """MuteService doesn't handle scene calls."""
        pass
    
    def _handle_nrpn_mute(self, note: int, velocity: int, channel: int) -> None:
        """
        Handle mute using NRPN protocol (Qu series).
        
        NRPN sequence:
        1. CC#99 (NRPN MSB) = parameter_msb
        2. CC#98 (NRPN LSB) = parameter_lsb  
        3. CC#6  (Data Entry MSB) = 0
        4. CC#38 (Data Entry LSB) = mute_value (1=on, 0=off)
        """
        mute_on_off = 1 if velocity >= 1 else 0
        
        # Get NRPN parameters from config
        nrpn_params = self.config.get("nrpn_params", {})
        parameter_msb = nrpn_params.get("msb", 0x00)
        parameter_lsb = note & 0x7F  # Input channel index (0-based)
        
        # Send NRPN sequence
        sequence = nrpn_params.get("mute_sequence", [99, 98, 6, 38])
        values = [parameter_msb, parameter_lsb, 0, mute_on_off]
        
        for cc, value in zip(sequence, values):
            success = self.midi_backend.send_control_change(cc, value, channel)
            if not success:
                self.logger.error(f"NRPN CC#{cc} 전송 실패")
                return
        
        self.logger.info(f"NRPN 뮤트 전송: 채널{note+1} {'켜기' if mute_on_off else '끄기'}")
    
    def _handle_cc_mute(self, note: int, velocity: int, channel: int) -> None:
        """
        Handle mute using simple CC protocol (legacy mixers).
        """
        mute_on_off = 127 if velocity >= 1 else 0
        
        # Use CC#26 for mute control
        success = self.midi_backend.send_control_change(26, mute_on_off, channel)
        
        if success:
            self.logger.info(f"CC 뮤트 전송: 채널{note+1} {'켜기' if mute_on_off else '끄기'}")
        else:
            self.logger.error("CC 뮤트 전송 실패")
    
    def update_mixer_config(self, mixer_name: str) -> None:
        """Update mixer configuration."""
        self.mixer_name = mixer_name
        self.config = get_mixer_config(mixer_name)
        
        if not self.config:
            self.logger.error(f"지원하지 않는 믹서: {mixer_name}")
            raise ValueError(f"Unsupported mixer: {mixer_name}")
        
        self.logger.info(f"믹서 설정 업데이트: {mixer_name}")
