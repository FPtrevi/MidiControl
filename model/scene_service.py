"""
Scene call service for mixer scene management.
"""
from typing import Optional, Dict, Any
from model.base_service import BaseMidiService
from config.mixer_config import get_mixer_config
from config.settings import SCENE_NUMBER_RANGE
from utils.logger import get_logger


class SceneService(BaseMidiService):
    """
    Handles scene call operations with mixer-specific protocols.
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
        """SceneService doesn't handle mute operations."""
        pass
    
    def handle_scene(self, note: int, channel: int) -> None:
        """Handle scene call based on mixer protocol."""
        protocol = self.config.get("scene_protocol", "unknown")
        
        if protocol == "bank_select":
            self._handle_bank_select_scene(note, channel)
        elif protocol == "program_change":
            self._handle_program_change_scene(note, channel)
        else:
            self.logger.error(f"지원하지 않는 씬 프로토콜: {protocol}")
    
    def _handle_bank_select_scene(self, note: int, channel: int) -> None:
        """
        Handle scene call using Bank Select + Program Change (Qu series).
        
        Sequence:
        1. CC#0 (Bank Select MSB) = 0
        2. CC#32 (Bank Select LSB) = 0  
        3. Program Change = scene_number - 1
        """
        scene_number = note + 1  # note=0 → scene 1
        
        # Validate scene number
        min_scene, max_scene = SCENE_NUMBER_RANGE
        if not (min_scene <= scene_number <= max_scene):
            self.logger.error(f"유효하지 않은 씬 번호: {scene_number}")
            return
        
        # Get bank select parameters from config
        bank_config = self.config.get("bank_select", {})
        bank_msb = bank_config.get("msb", 0)
        bank_lsb = bank_config.get("lsb", 0)
        
        # Send Bank Select sequence
        success1 = self.midi_backend.send_control_change(0, bank_msb, channel)
        success2 = self.midi_backend.send_control_change(32, bank_lsb, channel)
        success3 = self.midi_backend.send_program_change(scene_number - 1, channel)
        
        if all([success1, success2, success3]):
            self.logger.info(f"씬 호출 성공: 씬 {scene_number} (Bank:{bank_msb}, PC:{scene_number-1})")
        else:
            self.logger.error("씬 호출 전송 실패")
    
    def _handle_program_change_scene(self, note: int, channel: int) -> None:
        """
        Handle scene call using Program Change only (legacy mixers).
        """
        scene_number = note + 1  # note=0 → scene 1
        
        # Validate scene number
        min_scene, max_scene = SCENE_NUMBER_RANGE
        if not (min_scene <= scene_number <= max_scene):
            self.logger.error(f"유효하지 않은 씬 번호: {scene_number}")
            return
        
        # Send Program Change only
        success = self.midi_backend.send_program_change(scene_number - 1, channel)
        
        if success:
            self.logger.info(f"씬 호출 성공: 씬 {scene_number} (PC:{scene_number-1})")
        else:
            self.logger.error("씬 호출 전송 실패")
    
    def update_mixer_config(self, mixer_name: str) -> None:
        """Update mixer configuration."""
        self.mixer_name = mixer_name
        self.config = get_mixer_config(mixer_name)
        
        if not self.config:
            self.logger.error(f"지원하지 않는 믹서: {mixer_name}")
            raise ValueError(f"Unsupported mixer: {mixer_name}")
        
        self.logger.info(f"믹서 설정 업데이트: {mixer_name}")
