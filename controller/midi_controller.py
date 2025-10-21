"""
Main controller for MIDI mixer control application.
Coordinates between view, model services, and MIDI backend.
Implements MVC pattern with thread-safe communication.
"""
import threading
from typing import Optional, Dict, Any, List
import time
import mido

from model.midi_backend import MidiBackend
from model.dm3_osc_service import DM3OSCService
from model.qu5_midi_service import Qu5MIDIService
from view.midi_view import MidiMixerView
from config.settings import NOTE_ON_TYPE, NOTE_OFF_TYPE, PORT_WATCH_INTERVAL_SEC
from utils.logger import get_logger
from utils.prefs import load_prefs, save_prefs


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
        self.dm3_service: Optional[DM3OSCService] = None
        self.qu5_service: Optional[Qu5MIDIService] = None
        
        # Connection state
        self.is_monitoring = False
        self._initialized = False
        
        # Port change detection state
        self._last_input_ports: Optional[List[str]] = None
        self._last_output_ports: Optional[List[str]] = None
        self._last_port_scan_time: float = 0.0
        self._port_scan_interval_sec: float = PORT_WATCH_INTERVAL_SEC
        
        # Background watcher
        self._port_watcher_thread: Optional[threading.Thread] = None
        self._port_watcher_stop = threading.Event()
        self._controller_lock = threading.RLock()
        
        # Set up callbacks
        self._setup_callbacks()
        
        # Set message handler for MIDI backend
        self.midi_backend.set_message_handler(self._handle_midi_message)
        
        # Set up GUI update callback
        self.view.set_update_callback(self.update)
        
        # Note: Virtual MIDI port creation is deferred to initialize() method
        # to ensure it runs on the main thread and avoid GIL issues
        
        self.logger.info("MidiController 초기화 완료")
    
    def _setup_callbacks(self) -> None:
        """Set up callbacks between view and controller."""
        self.view.set_connect_callback(self._on_connect)
        self.view.set_disconnect_callback(self._on_disconnect)
        self.view.set_refresh_ports_callback(self._on_refresh_ports)
        self.view.set_mixer_changed_callback(self._on_mixer_changed)
    
    def _on_connect(self) -> None:
        """Handle connection request from view."""
        with self._controller_lock:
            try:
                params = self.view.get_connection_params()
                mixer = params["mixer"]
                
                # Initialize services if not done
                if not self.dm3_service or not self.qu5_service:
                    self._initialize_services(mixer)
                
                # Connect to appropriate mixer
                mixer_params = self.view.get_mixer_connection_params()
                connection_success = False
                
                if mixer == "DM3":
                    if self.dm3_service:
                        connection_success = self.dm3_service.connect()
                elif mixer in ["Qu-5", "Qu-6", "Qu-7"]:
                    if self.qu5_service:
                        connection_success = self.qu5_service.connect()
                
                if not connection_success:
                    self.view.show_message("연결 오류", f"{mixer} 믹서 연결에 실패했습니다.", "error")
                    return
                
                # Start monitoring
                if self.midi_backend.start_monitoring():
                    self.is_monitoring = True
                    self.view.set_connection_state(True)
                    self.view.clear_log()
                    self.view.append_log(f"🎉 {mixer} 믹서 연결 성공")
                    self.view.append_log(f"📡 가상 MIDI 포트 활성화: '{self.midi_backend.virtual_port_name}'")
                    self.view.append_log("프로프리젠터에서 가상 MIDI 포트를 선택하세요!")
                    self.logger.info(f"{mixer} 믹서 연결 성공")
                else:
                    self.view.show_message("연결 오류", "MIDI 모니터링 시작에 실패했습니다.", "error")
                    
            except Exception as e:
                self.logger.error(f"연결 오류: {e}")
                self.view.show_message("연결 오류", f"연결 중 오류가 발생했습니다: {e}", "error")
    
    def _on_disconnect(self) -> None:
        """Handle disconnection request from view."""
        with self._controller_lock:
            try:
                # Disconnect from mixer services
                if self.dm3_service:
                    self.dm3_service.disconnect()
                if self.qu5_service:
                    self.qu5_service.disconnect()
                
                self.midi_backend.stop_monitoring()
                self.is_monitoring = False
                self.view.set_connection_state(False)
                self.view.append_log("믹서 연결 해제됨")
                self.logger.info("믹서 연결 해제")
                
            except Exception as e:
                self.logger.error(f"연결 해제 오류: {e}")
    
    def _on_refresh_ports(self) -> None:
        """Handle port refresh request from view (virtual ports only)."""
        try:
            # For virtual ports, we just need to update the virtual port status
            if self.midi_backend.virtual_port_active:
                self.view.update_virtual_port_status(self.midi_backend.virtual_port_name, True)
                self.logger.info("가상 MIDI 포트 새로고침 완료")
            else:
                self.view.update_virtual_port_status(self.midi_backend.virtual_port_name, False)
                self.logger.warning("가상 MIDI 포트가 비활성 상태입니다")
        except Exception as e:
            self.logger.error(f"포트 새로고침 오류: {e}")
    
    def _on_mixer_changed(self, mixer_name: str) -> None:
        """Handle mixer selection change from view."""
        try:
            self.logger.info(f"믹서 변경: {mixer_name}")
            
            # Update services if they exist
            if self.dm3_service:
                self.dm3_service.update_mixer_config(mixer_name)
            if self.qu5_service:
                self.qu5_service.update_mixer_config(mixer_name)
                
        except Exception as e:
            self.logger.error(f"믹서 변경 오류: {e}")
            self.view.show_message("오류", f"믹서 설정 변경 중 오류가 발생했습니다: {e}", "error")
    
    def _initialize_services(self, mixer_name: str) -> None:
        """Initialize mixer services for selected mixer."""
        try:
            if mixer_name == "DM3":
                self.dm3_service = DM3OSCService(mixer_name, self.midi_backend)
                # Set DM3 connection parameters from view
                mixer_params = self.view.get_mixer_connection_params()
                if mixer_params:
                    self.dm3_service.set_connection_params(
                        mixer_params.get("dm3_ip", "192.168.4.2"),
                        mixer_params.get("dm3_port", 49900)
                    )
            elif mixer_name in ["Qu-5", "Qu-6", "Qu-7"]:
                self.qu5_service = Qu5MIDIService(mixer_name, self.midi_backend)
                # Set Qu-5 connection parameters from view
                mixer_params = self.view.get_mixer_connection_params()
                if mixer_params:
                    self.qu5_service.set_connection_params(
                        mixer_params.get("qu5_ip", "192.168.5.10"),
                        mixer_params.get("qu5_port", 51325),
                        mixer_params.get("qu5_channel", 1),
                        mixer_params.get("use_tcp_midi", True)
                    )
            
            self.logger.info(f"서비스 초기화 완료: {mixer_name}")
            
        except Exception as e:
            self.logger.error(f"서비스 초기화 오류: {e}")
            raise
    
    def _handle_midi_message(self, message: mido.Message) -> None:
        """Handle incoming MIDI message (called from MIDI thread)."""
        try:
            # Log incoming message
            self.view.append_log(f"🎵 MIDI 수신: {message}")
            
            # Process note_on and note_off messages only
            if message.type not in [NOTE_ON_TYPE, NOTE_OFF_TYPE]:
                return
            
            # Get mixer type and MIDI channel from view
            params = self.view.get_connection_params()
            mixer = params["mixer"]
            mixer_midi_channel = params["midi_channel"]
            
            # Route message based on channel and mixer type
            # Channel 0 = Soft key control, Channel 1 = Scene recall, Channel 2 = Mute control
            if message.channel == 0:
                # Soft key control (for Qu-5/6/7)
                if message.type == NOTE_ON_TYPE and message.velocity > 0:
                    if mixer in ["Qu-5", "Qu-6", "Qu-7"] and self.qu5_service:
                        self.qu5_service.handle_softkey(message.note, message.channel, mixer_midi_channel)
                        
            elif message.channel == 1:
                # Scene recall
                if message.type == NOTE_ON_TYPE and message.velocity > 0:
                    if mixer == "DM3" and self.dm3_service:
                        self.dm3_service.handle_scene(message.note, message.channel)
                    elif mixer in ["Qu-5", "Qu-6", "Qu-7"] and self.qu5_service:
                        self.qu5_service.handle_scene(message.note, message.channel, mixer_midi_channel)
                        
            elif message.channel == 2:
                # Mute control
                effective_velocity = message.velocity if message.type == NOTE_ON_TYPE else 0
                if mixer == "DM3" and self.dm3_service:
                    self.dm3_service.handle_mute(message.note, effective_velocity, message.channel)
                elif mixer in ["Qu-5", "Qu-6", "Qu-7"] and self.qu5_service:
                    self.qu5_service.handle_mute(message.note, effective_velocity, message.channel, mixer_midi_channel)
                        
            else:
                self.view.append_log(f"ℹ️ 처리하지 않는 채널: {message.channel} (채널 0,1,2만 처리)")
                
        except Exception as e:
            self.logger.error(f"MIDI 메시지 처리 오류: {e}")
            self.view.append_log(f"메시지 처리 오류: {e}")
    
    def update(self) -> None:
        """Update controller state (called from main loop)."""
        if self.is_monitoring:
            # Process queued MIDI messages
            self.midi_backend.process_queued_messages()
            return
        # Port polling moved to background watcher thread
    
    def initialize(self) -> None:
        """Initialize the controller (without starting GUI main loop)."""
        with self._controller_lock:
            if self._initialized:
                self.logger.info("컨트롤러가 이미 초기화되었습니다")
                return
                
            try:
                self.logger.info("컨트롤러 초기화 시작")
                
                # 0) Create virtual MIDI ports first (must be on main thread to avoid GIL issues)
                if self.midi_backend.create_virtual_ports():
                    self.view.update_virtual_port_status(self.midi_backend.virtual_port_name, True)
                    self.logger.info("가상 MIDI 포트 생성 성공")
                else:
                    self.view.update_virtual_port_status(self.midi_backend.virtual_port_name, False)
                    self.logger.warning("가상 MIDI 포트 생성 실패 - 시뮬레이션 모드로 실행")
                
                # 1) 저장된 설정 로드하여 View에 적용 (가능한 경우)
                try:
                    prefs = load_prefs()
                    mixer = prefs.get("mixer")
                    input_port = prefs.get("input_port")
                    output_port = prefs.get("output_port")
                    channel = prefs.get("channel")

                    # Mixer 우선 적용
                    if isinstance(mixer, str) and mixer:
                        self.view.mixer_var.set(mixer)
                        # 믹서 변경 콜백 호출하여 내부 서비스 구성을 업데이트
                        try:
                            self._on_mixer_changed(mixer)
                        except Exception:
                            pass

                    # 채널 적용 (유효 범위 체크는 view 검증에 맡김)
                    if isinstance(channel, int) and channel:
                        self.view.channel_var.set(str(channel))

                    # Virtual ports are handled automatically, no need for port scanning
                    self.logger.info("가상 MIDI 포트 사용으로 포트 스캔 생략")
                except Exception as e:
                    self.logger.warning(f"환경설정 로드 중 경고: {e}")

                # Initial port refresh must run on Tk main loop to avoid GIL issues
                try:
                    self.view.root.after(0, self._on_refresh_ports)
                except Exception as e:
                    # Fallback if root is not ready (should not happen)
                    self.logger.warning(f"초기 새로고침 스케줄 실패, 즉시 시도: {e}")
                    self._on_refresh_ports()
                
                # Start background port watcher
                self._start_port_watcher()

                self._initialized = True
                self.logger.info("컨트롤러 초기화 완료")
                
            except Exception as e:
                self.logger.error(f"컨트롤러 초기화 오류: {e}")
                raise
    
    def shutdown(self) -> None:
        """Shutdown the application."""
        with self._controller_lock:
            if not self._initialized:
                return
                
            try:
                # stop watcher first
                self._stop_port_watcher()
                if self.is_monitoring:
                    self._on_disconnect()
                
                # 현재 설정 저장
                try:
                    params = self.view.get_connection_params()
                    # channel은 int, 나머지는 str
                    prefs = {
                        "mixer": params.get("mixer"),
                        "input_port": params.get("input_port"),
                        "output_port": params.get("output_port"),
                        "channel": params.get("channel"),
                    }
                    if not save_prefs(prefs):
                        self.logger.warning("환경설정 저장 실패")
                    else:
                        self.logger.info("환경설정 저장 완료")
                except Exception as e:
                    self.logger.warning(f"환경설정 저장 중 경고: {e}")

                if self.dm3_service:
                    self.dm3_service.shutdown()
                if self.qu5_service:
                    self.qu5_service.shutdown()
                
                self.midi_backend.shutdown()
                self.view.quit()
                
                self._initialized = False
                self.logger.info("애플리케이션 종료")
                
            except Exception as e:
                self.logger.error(f"종료 중 오류: {e}")

    def _start_port_watcher(self) -> None:
        if self._port_watcher_thread and self._port_watcher_thread.is_alive():
            return
        self._port_watcher_stop.clear()

        def _watch():
            while not self._port_watcher_stop.is_set():
                try:
                    # For virtual ports, we only need to check if they're still active
                    if not self.midi_backend.virtual_port_active:
                        self.logger.warning("가상 MIDI 포트가 비활성 상태로 변경됨")
                        # Update GUI to reflect inactive state
                        def _update_status():
                            try:
                                self.view.update_virtual_port_status(self.midi_backend.virtual_port_name, False)
                            except Exception as e:
                                self.logger.error(f"가상 포트 상태 업데이트 오류: {e}")
                        self.view.root.after_idle(_update_status)

                    # throttle - check less frequently for virtual ports
                    time.sleep(self._port_scan_interval_sec * 2)  # Check every 6 seconds instead of 3
                except Exception as e:
                    self.logger.error(f"포트 감시 오류: {e}")
                    time.sleep(self._port_scan_interval_sec)

        self._port_watcher_thread = threading.Thread(target=_watch, daemon=True, name="PortWatcher")
        self._port_watcher_thread.start()

    def _stop_port_watcher(self) -> None:
        self._port_watcher_stop.set()
        if self._port_watcher_thread and self._port_watcher_thread.is_alive():
            self._port_watcher_thread.join(timeout=2.0)
