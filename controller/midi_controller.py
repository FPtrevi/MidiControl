"""
Main controller for MIDI mixer control application.
Coordinates between view, model services, and MIDI backend.
Implements MVC pattern with thread-safe communication.
"""
import threading
from typing import Optional, Dict, Any
import time
import mido

from model.midi_backend import MidiBackend
from model.mute_service import MuteService
from model.scene_service import SceneService
from model.softkey_service import SoftKeyService
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
        self.mute_service: Optional[MuteService] = None
        self.scene_service: Optional[SceneService] = None
        self.softkey_service: Optional[SoftKeyService] = None
        
        # Connection state
        self.is_monitoring = False
        # Port change detection state
        self._last_input_ports: Optional[list[str]] = None
        self._last_output_ports: Optional[list[str]] = None
        self._last_port_scan_time: float = 0.0
        self._port_scan_interval_sec: float = PORT_WATCH_INTERVAL_SEC
        # Background watcher
        self._port_watcher_thread: Optional[threading.Thread] = None
        self._port_watcher_stop = threading.Event()
        
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
            if not self.mute_service or not self.scene_service or not self.softkey_service:
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
        """Handle port refresh request from view. Run scan off the Tk thread."""
        def _scan_and_update():
            try:
                if self.is_monitoring:
                    # ensure disconnect happens on Tk thread
                    self.view.root.after(0, self._on_disconnect)

                input_ports = self.midi_backend.get_input_ports()
                output_ports = self.midi_backend.get_output_ports()

                def _apply():
                    self.view.update_input_ports(input_ports)
                    self.view.update_output_ports(output_ports)
                self.view.root.after(0, _apply)

                # Save last lists
                self._last_input_ports = input_ports
                self._last_output_ports = output_ports
            except Exception as e:
                self.logger.error(f"포트 새로고침 오류: {e}")

        threading.Thread(target=_scan_and_update, daemon=True, name="PortRefresh").start()
    
    def _on_mixer_changed(self, mixer_name: str) -> None:
        """Handle mixer selection change from view."""
        try:
            self.logger.info(f"믹서 변경: {mixer_name}")
            
            # Update services if they exist
            if self.mute_service:
                self.mute_service.update_mixer_config(mixer_name)
            if self.scene_service:
                self.scene_service.update_mixer_config(mixer_name)
            if self.softkey_service:
                self.softkey_service.update_mixer_config(mixer_name)
                
        except Exception as e:
            self.logger.error(f"믹서 변경 오류: {e}")
            self.view.show_message("오류", f"믹서 설정 변경 중 오류가 발생했습니다: {e}", "error")
    
    def _initialize_services(self, mixer_name: str) -> None:
        """Initialize mute, scene, and softkey services for selected mixer."""
        try:
            self.mute_service = MuteService(mixer_name, self.midi_backend)
            self.scene_service = SceneService(mixer_name, self.midi_backend)
            self.softkey_service = SoftKeyService(mixer_name, self.midi_backend)
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
            
            # Route message based on channel (new mapping)
            if message.channel == 0:
                # Soft key control (was mute)
                effective_velocity = message.velocity if message.type == NOTE_ON_TYPE else 0
                if self.softkey_service:
                    self.softkey_service.handle_softkey(message.note, effective_velocity, output_channel)
                    
            elif message.channel == 1:
                # Scene call (unchanged)
                if message.type == NOTE_ON_TYPE and message.velocity > 0:
                    if self.scene_service:
                        self.scene_service.handle_scene(message.note, output_channel)
                        
            elif message.channel == 2:
                # Mute control (was channel 0)
                effective_velocity = message.velocity if message.type == NOTE_ON_TYPE else 0
                if self.mute_service:
                    self.mute_service.handle_mute(message.note, effective_velocity, output_channel)
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
            return
        # Port polling moved to background watcher thread
    
    def initialize(self) -> None:
        """Initialize the controller (without starting GUI main loop)."""
        try:
            self.logger.info("컨트롤러 초기화 시작")
            
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

                # 포트 목록을 먼저 스캔한 뒤, 해당 값이 목록에 없으면 첫 번째 항목으로 fallback
                def _apply_ports_when_ready():
                    try:
                        inputs = self.midi_backend.get_input_ports()
                        outputs = self.midi_backend.get_output_ports()
                        self.view.update_input_ports(inputs)
                        self.view.update_output_ports(outputs)

                        # 입력 포트 복원 또는 첫 항목
                        if isinstance(input_port, str) and input_port in inputs:
                            self.view.input_midi_var.set(input_port)
                        else:
                            # update_input_ports에서 이미 첫 항목으로 fallback하므로 별도 처리 불필요
                            pass

                        # 출력 포트 복원 또는 첫 항목
                        if isinstance(output_port, str) and output_port in outputs:
                            self.view.output_midi_var.set(output_port)
                        else:
                            # 요구사항: 저장된 출력 포트가 없으면 첫번째 목록 값이 선택되도록 유지
                            pass
                    except Exception as e:
                        self.logger.error(f"초기 포트 적용 오류: {e}")

                # Tk 스레드에서 안전하게 적용
                self.view.root.after(0, _apply_ports_when_ready)
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

            self.logger.info("컨트롤러 초기화 완료")
            
        except Exception as e:
            self.logger.error(f"컨트롤러 초기화 오류: {e}")
            raise
    
    def shutdown(self) -> None:
        """Shutdown the application."""
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

            if self.mute_service:
                self.mute_service.shutdown()
            if self.scene_service:
                self.scene_service.shutdown()
            
            self.midi_backend.shutdown()
            self.view.quit()
            
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
                    current_inputs = self.midi_backend.get_input_ports()
                    current_outputs = self.midi_backend.get_output_ports()

                    changed = False
                    if self._last_input_ports is None or self._last_input_ports != current_inputs:
                        self._last_input_ports = current_inputs
                        changed = True
                        self.view.root.after(0, lambda: self.view.update_input_ports(current_inputs))

                    if self._last_output_ports is None or self._last_output_ports != current_outputs:
                        self._last_output_ports = current_outputs
                        changed = True
                        self.view.root.after(0, lambda: self.view.update_output_ports(current_outputs))

                    # throttle
                    time.sleep(self._port_scan_interval_sec)
                except Exception as e:
                    self.logger.error(f"포트 감시 오류: {e}")
                    time.sleep(self._port_scan_interval_sec)

        self._port_watcher_thread = threading.Thread(target=_watch, daemon=True, name="PortWatcher")
        self._port_watcher_thread.start()

    def _stop_port_watcher(self) -> None:
        self._port_watcher_stop.set()
        if self._port_watcher_thread and self._port_watcher_thread.is_alive():
            self._port_watcher_thread.join(timeout=2.0)
