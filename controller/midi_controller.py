"""
Main controller for MIDI mixer control application.
Coordinates between view, model services, and MIDI backend.
Implements MVC pattern with thread-safe communication.
"""
import threading
from typing import Optional, Dict, Any
import mido

from model.midi_backend import MidiBackend
from model.mute_service import MuteService
from model.scene_service import SceneService
from view.midi_view import MidiMixerView
from config.settings import NOTE_ON_TYPE, NOTE_OFF_TYPE
from utils.logger import get_logger


class MidiController:
    """
    Main controller implementing MVC pattern.
    Handles coordination between UI and MIDI services with thread safety.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Initialize components
        self.view = MidiMixerView()
        self.midi_backend = MidiBackend()
        
        # Services (initialized after mixer selection)
        self.mute_service: Optional[MuteService] = None
        self.scene_service: Optional[SceneService] = None
        
        # Connection state
        self.is_monitoring = False
        
        # Set up callbacks
        self._setup_callbacks()
        
        # Set message handler for MIDI backend
        self.midi_backend.set_message_handler(self._handle_midi_message)
        
        # Set up GUI update callback
        self.view.set_update_callback(self.update)
        
        self.logger.info("MidiController 초기화 완료")
    
    def _setup_callbacks(self) -> None:
        """Set up callbacks between view and controller."""
        self.view.set_connect_callback(self._on_connect)
        self.view.set_disconnect_callback(self._on_disconnect)
        self.view.set_refresh_ports_callback(self._on_refresh_ports)
        self.view.set_mixer_changed_callback(self._on_mixer_changed)
    
    def _on_connect(self) -> None:
        """Handle connection request from view."""
        try:
            params = self.view.get_connection_params()
            mixer = params["mixer"]
            input_port = params["input_port"]
            output_port = params["output_port"]
            channel = params["channel"]
            
            # Initialize services if not done
            if not self.mute_service or not self.scene_service:
                self._initialize_services(mixer)
            
            # Open MIDI ports
            input_success = self.midi_backend.open_input_port(input_port)
            output_success = self.midi_backend.open_output_port(output_port)
            
            if not input_success or not output_success:
                self.view.show_message("연결 오류", "MIDI 포트 연결에 실패했습니다.", "error")
                return
            
            # Start monitoring
            if self.midi_backend.start_monitoring():
                self.is_monitoring = True
                self.view.set_connection_state(True)
                self.view.clear_log()
                self.view.append_log(f"MIDI 모니터링 시작: 입력 '{input_port}', 출력 '{output_port}'")
                self.logger.info("MIDI 연결 성공")
            else:
                self.view.show_message("연결 오류", "MIDI 모니터링 시작에 실패했습니다.", "error")
                
        except Exception as e:
            self.logger.error(f"연결 오류: {e}")
            self.view.show_message("연결 오류", f"연결 중 오류가 발생했습니다: {e}", "error")
    
    def _on_disconnect(self) -> None:
        """Handle disconnection request from view."""
        try:
            self.midi_backend.stop_monitoring()
            self.is_monitoring = False
            self.view.set_connection_state(False)
            self.view.append_log("MIDI 모니터링 중지")
            self.logger.info("MIDI 연결 해제")
            
        except Exception as e:
            self.logger.error(f"연결 해제 오류: {e}")
    
    def _on_refresh_ports(self) -> None:
        """Handle port refresh request from view."""
        try:
            if self.is_monitoring:
                self._on_disconnect()
            
            # Get fresh port lists
            input_ports = self.midi_backend.get_input_ports()
            output_ports = self.midi_backend.get_output_ports()
            
            # Update view
            self.view.update_input_ports(input_ports)
            self.view.update_output_ports(output_ports)
            
            self.view.show_message("새로고침 완료", "MIDI 포트 목록을 새로고침했습니다.")
            
        except Exception as e:
            self.logger.error(f"포트 새로고침 오류: {e}")
            self.view.show_message("오류", f"포트 새로고침 중 오류가 발생했습니다: {e}", "error")
    
    def _on_mixer_changed(self, mixer_name: str) -> None:
        """Handle mixer selection change from view."""
        try:
            self.logger.info(f"믹서 변경: {mixer_name}")
            
            # Update services if they exist
            if self.mute_service:
                self.mute_service.update_mixer_config(mixer_name)
            if self.scene_service:
                self.scene_service.update_mixer_config(mixer_name)
                
        except Exception as e:
            self.logger.error(f"믹서 변경 오류: {e}")
            self.view.show_message("오류", f"믹서 설정 변경 중 오류가 발생했습니다: {e}", "error")
    
    def _initialize_services(self, mixer_name: str) -> None:
        """Initialize mute and scene services for selected mixer."""
        try:
            self.mute_service = MuteService(mixer_name, self.midi_backend)
            self.scene_service = SceneService(mixer_name, self.midi_backend)
            self.logger.info(f"서비스 초기화 완료: {mixer_name}")
            
        except Exception as e:
            self.logger.error(f"서비스 초기화 오류: {e}")
            raise
    
    def _handle_midi_message(self, message: mido.Message) -> None:
        """Handle incoming MIDI message (called from MIDI thread)."""
        try:
            # Log incoming message
            self.view.append_log(f"[입력] {message}")
            
            # Process note_on and note_off messages only
            if message.type not in [NOTE_ON_TYPE, NOTE_OFF_TYPE]:
                return
            
            # Get output channel from view (convert 1-based to 0-based)
            params = self.view.get_connection_params()
            output_channel = params["channel"] - 1
            
            # Route message based on channel
            if message.channel == 0:
                # Mute control
                effective_velocity = message.velocity if message.type == NOTE_ON_TYPE else 0
                if self.mute_service:
                    self.mute_service.handle_mute(message.note, effective_velocity, output_channel)
                    
            elif message.channel == 1:
                # Scene call (only on note_on with velocity > 0)
                if message.type == NOTE_ON_TYPE and message.velocity > 0:
                    if self.scene_service:
                        self.scene_service.handle_scene(message.note, output_channel)
            else:
                self.view.append_log(f"알 수 없는 채널 메시지 수신: {message.channel}")
                
        except Exception as e:
            self.logger.error(f"MIDI 메시지 처리 오류: {e}")
            self.view.append_log(f"메시지 처리 오류: {e}")
    
    def update(self) -> None:
        """Update controller state (called from main loop)."""
        if self.is_monitoring:
            # Process queued MIDI messages
            self.midi_backend.process_queued_messages()
    
    def initialize(self) -> None:
        """Initialize the controller (without starting GUI main loop)."""
        try:
            self.logger.info("컨트롤러 초기화 시작")
            
            # Initial port refresh
            self._on_refresh_ports()
            
            self.logger.info("컨트롤러 초기화 완료")
            
        except Exception as e:
            self.logger.error(f"컨트롤러 초기화 오류: {e}")
            raise
    
    def shutdown(self) -> None:
        """Shutdown the application."""
        try:
            if self.is_monitoring:
                self._on_disconnect()
            
            if self.mute_service:
                self.mute_service.shutdown()
            if self.scene_service:
                self.scene_service.shutdown()
            
            self.midi_backend.shutdown()
            self.view.quit()
            
            self.logger.info("애플리케이션 종료")
            
        except Exception as e:
            self.logger.error(f"종료 중 오류: {e}")
