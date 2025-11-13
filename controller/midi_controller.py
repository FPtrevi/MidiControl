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
        
        # Set up logger GUI callbacks
        self.logger.set_gui_callback(self.view.append_log)
        self.midi_backend.logger.set_gui_callback(self.view.append_log)
        
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
        
        # MidiController 초기화 완료 (로그 제거)
    
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
                elif mixer == "Qu-5/6/7":
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
                    
                    # 연결 성공 시 현재 설정 저장
                    self._save_current_settings()
                    
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
                # 가상 MIDI 포트 새로고침 완료 (로그 제거)
            else:
                self.view.update_virtual_port_status(self.midi_backend.virtual_port_name, False)
                self.logger.warning("가상 MIDI 포트가 비활성 상태입니다")
        except Exception as e:
            self.logger.error(f"포트 새로고침 오류: {e}")
    
    def _on_mixer_changed(self, mixer_name: str) -> None:
        """Handle mixer selection change from view."""
        try:
            # 믹서 변경 (로그 제거)
            
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
                # Set GUI callback for service logger
                self.dm3_service.logger.set_gui_callback(self.view.append_log)
                # Set DM3 connection parameters from view
                mixer_params = self.view.get_mixer_connection_params()
                if mixer_params:
                    self.dm3_service.set_connection_params(
                        mixer_params.get("dm3_ip", "192.168.4.2"),
                        mixer_params.get("dm3_port", 49900)
                    )
            elif mixer_name == "Qu-5/6/7":
                self.qu5_service = Qu5MIDIService(mixer_name, self.midi_backend)
                # Set GUI callback for service logger
                self.qu5_service.logger.set_gui_callback(self.view.append_log)
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
                    if mixer == "Qu-5/6/7" and self.qu5_service:
                        self.qu5_service.handle_softkey(message.note, message.channel, mixer_midi_channel)
                        
            elif message.channel == 1:
                # Scene recall
                if message.type == NOTE_ON_TYPE and message.velocity > 0:
                    if mixer == "DM3" and self.dm3_service:
                        self.dm3_service.handle_scene(message.note, message.channel)
                    elif mixer == "Qu-5/6/7" and self.qu5_service:
                        self.qu5_service.handle_scene(message.note, message.channel, mixer_midi_channel)
                        
            elif message.channel == 2:
                # Mute control
                effective_velocity = message.velocity if message.type == NOTE_ON_TYPE else 0
                if mixer == "DM3" and self.dm3_service:
                    self.dm3_service.handle_mute(message.note, effective_velocity, message.channel)
                elif mixer == "Qu-5/6/7" and self.qu5_service:
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
                # 컨트롤러 초기화 시작 (로그 제거)
                
                # 0) Create virtual MIDI ports first (must be on main thread to avoid GIL issues)
                if self.midi_backend.create_virtual_ports():
                    self.view.update_virtual_port_status(self.midi_backend.virtual_port_name, True)
                    # 가상 MIDI 포트 생성 성공 (로그 제거)
                else:
                    self.view.update_virtual_port_status(self.midi_backend.virtual_port_name, False)
                    self.logger.warning("가상 MIDI 포트 생성 실패 - 시뮬레이션 모드로 실행")
                
                # 1) View 초기화 시점에서 이미 설정이 로드되므로 믹서 변경 콜백만 호출
                # 믹서 타입이 로드된 경우 해당 믹서로 서비스 초기화
                mixer = self.view.mixer_var.get()
                if mixer in ["DM3", "Qu-5/6/7"]:
                    self.view.root.after(100, lambda: self._on_mixer_changed(mixer))

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
                # 컨트롤러 초기화 완료 (로그 제거)
                
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
                
                # 앱 종료 시 현재 설정 저장 (연결 성공 여부와 관계없이)
                try:
                    self._save_current_settings()
                except Exception as e:
                    self.logger.warning(f"종료 시 설정 저장 중 경고: {e}")

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
    
    def _load_user_settings(self) -> None:
        """GUI 초기화 후 저장된 사용자 설정을 로드하여 적용."""
        try:
            prefs = load_prefs()
            
            # 믹서 타입 로드 및 적용
            mixer = prefs.get("mixer")
            if isinstance(mixer, str) and mixer in ["DM3", "Qu-5/6/7"]:
                self.view.mixer_var.set(mixer)
                # 믹서 변경 콜백 호출하여 내부 서비스 구성을 업데이트
                self._on_mixer_changed(mixer)
                self.logger.info(f"저장된 믹서 설정 복원: {mixer}")
            
            # MIDI 채널 로드 및 적용
            midi_channel = prefs.get("midi_channel")
            if isinstance(midi_channel, int) and 1 <= midi_channel <= 16:
                self.view.midi_channel_var.set(str(midi_channel))
                self.logger.info(f"저장된 MIDI 채널 복원: {midi_channel}")
            
            # DM3 설정 로드 및 적용
            dm3_ip = prefs.get("dm3_ip")
            dm3_port = prefs.get("dm3_port")
            if isinstance(dm3_ip, str) and dm3_ip:
                self.view.dm3_ip_var.set(dm3_ip)
            if isinstance(dm3_port, int) and 1 <= dm3_port <= 65535:
                self.view.dm3_port_var.set(str(dm3_port))
            
            # Qu-5/6/7 설정 로드 및 적용
            qu5_ip = prefs.get("qu5_ip")
            qu5_port = prefs.get("qu5_port")
            qu5_channel = prefs.get("qu5_channel")
            use_tcp_midi = prefs.get("use_tcp_midi")
            
            if isinstance(qu5_ip, str) and qu5_ip:
                self.view.qu5_ip_var.set(qu5_ip)
            if isinstance(qu5_port, int) and 1 <= qu5_port <= 65535:
                self.view.qu5_port_var.set(str(qu5_port))
            # qu5_channel을 midi_channel_var에 설정 (GUI에서 qu5_channel_var 제거됨)
            if isinstance(qu5_channel, int) and 1 <= qu5_channel <= 16:
                self.view.midi_channel_var.set(str(qu5_channel))
            if isinstance(use_tcp_midi, bool):
                self.view.use_tcp_midi_var.set(use_tcp_midi)
            
            self.logger.info("사용자 설정 로드 완료")
            
        except Exception as e:
            self.logger.warning(f"사용자 설정 로드 중 경고: {e}")
    
    def _save_current_settings(self) -> None:
        """연결 성공 시 현재 설정을 저장."""
        try:
            # GUI에서 현재 설정값 가져오기
            mixer = self.view.mixer_var.get()
            midi_channel = int(self.view.midi_channel_var.get())
            
            # 믹서별 IP 주소와 포트 설정 가져오기
            mixer_params = self.view.get_mixer_connection_params()
            
            prefs = {
                "mixer": mixer,
                "midi_channel": midi_channel,
            }
            
            # 믹서별 설정 추가
            if mixer == "DM3":
                prefs.update({
                    "dm3_ip": mixer_params.get("dm3_ip", "192.168.4.2"),
                    "dm3_port": mixer_params.get("dm3_port", 49900)
                })
            elif mixer == "Qu-5/6/7":
                prefs.update({
                    "qu5_ip": mixer_params.get("qu5_ip", "192.168.5.10"),
                    "qu5_port": mixer_params.get("qu5_port", 51325),
                    "qu5_channel": mixer_params.get("qu5_channel", 1),
                    "use_tcp_midi": mixer_params.get("use_tcp_midi", True)
                })
            
            if save_prefs(prefs):
                self.logger.info("연결 성공 시 설정 저장 완료")
            else:
                self.logger.warning("연결 성공 시 설정 저장 실패")
                
        except Exception as e:
            self.logger.warning(f"연결 성공 시 설정 저장 중 경고: {e}")
