"""
GIL-safe MIDI backend with virtual port support for macOS + mido environment.
Supports both DM3 (OSC) and Qu-5 (MIDI) mixers through virtual MIDI ports.
"""
import mido
import threading
from typing import Optional, List, Callable, Any, Union
from queue import Queue, Empty
import time

from config.settings import MIDI_THREAD_DAEMON, MIDI_THREAD_TIMEOUT
from utils.logger import get_logger

# Try to import rtmidi, fallback to simulation if not available
try:
    import rtmidi
    # Test if rtmidi actually works (architecture compatibility check)
    test_out = rtmidi.MidiOut()
    test_out.close_port()
    del test_out
    RTMIDI_AVAILABLE = True
    print("✅ rtmidi 패키지가 정상적으로 로드되었습니다.")
except (ImportError, Exception) as e:
    RTMIDI_AVAILABLE = False
    print(f"⚠️ rtmidi 패키지를 사용할 수 없습니다: {e}")
    print("가상 MIDI 포트 기능이 시뮬레이션 모드로 실행됩니다.")


class MidiBackend:
    """
    Thread-safe MIDI backend that handles virtual port management and message routing.
    Designed to minimize GIL contention on macOS and support both DM3 and Qu-5 mixers.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Virtual MIDI ports (rtmidi)
        self.virtual_midi_out: Optional[rtmidi.MidiOut] = None
        self.virtual_midi_in: Optional[rtmidi.MidiIn] = None
        self.virtual_port_name = "MIDI Mixer Control"
        self.virtual_port_active = False
        
        # Thread-safe communication
        self._message_queue: Queue[mido.Message] = Queue()
        self._control_queue: Queue[Any] = Queue()
        self._shutdown_event = threading.Event()
        self._thread_lock = threading.RLock()  # Use RLock for better thread safety
        self._midi_thread: Optional[threading.Thread] = None
        
        # Callback handlers
        self._message_handler: Optional[Callable[[mido.Message], None]] = None
        self._initialized = False
    
    def set_message_handler(self, handler: Callable[[mido.Message], None]) -> None:
        """Set the message handler callback (called from main thread)."""
        with self._thread_lock:
            self._message_handler = handler
    
    def get_input_ports(self) -> List[str]:
        """Get available MIDI input ports (virtual port only)."""
        try:
            # Virtual port is always available when active
            if self.virtual_port_active:
                return [f"{self.virtual_port_name} In"]
            else:
                return [f"{self.virtual_port_name} In (비활성)"]
        except Exception as e:
            self.logger.error(f"입력 포트 가져오기 오류: {e}")
            return ["MIDI 포트 오류"]
    
    def get_output_ports(self) -> List[str]:
        """Get available MIDI output ports (virtual port only)."""
        try:
            # Virtual port is always available when active
            if self.virtual_port_active:
                return [f"{self.virtual_port_name} Out"]
            else:
                return [f"{self.virtual_port_name} Out (비활성)"]
        except Exception as e:
            self.logger.error(f"출력 포트 가져오기 오류: {e}")
            return ["MIDI 포트 오류"]
    
    def create_virtual_ports(self) -> bool:
        """Create virtual MIDI ports in a separate thread to avoid GIL issues."""
        with self._thread_lock:
            if self._initialized:
                return self.virtual_port_active
                
            if not RTMIDI_AVAILABLE:
                self.logger.warning("rtmidi가 사용할 수 없어 가상 포트를 시뮬레이션 모드로 실행합니다.")
                self.virtual_port_active = True  # Simulate active state
                self._initialized = True
                return True
            
            try:
                # Clean up existing ports first
                self.cleanup_virtual_ports()
                
                # Create virtual MIDI ports in a separate thread to avoid GIL issues
                def create_ports_in_thread():
                    try:
                        # Create virtual MIDI output port (for presenter connection)
                        self.virtual_midi_out = rtmidi.MidiOut()
                        self.virtual_midi_out.open_virtual_port(f"{self.virtual_port_name} Out")
                        self.logger.info(f"가상 출력 포트 생성: '{self.virtual_port_name} Out'")
                        
                        # Create virtual MIDI input port (for receiving from presenter)
                        self.virtual_midi_in = rtmidi.MidiIn()
                        self.virtual_midi_in.open_virtual_port(f"{self.virtual_port_name} In")
                        self.virtual_midi_in.set_callback(self._virtual_midi_callback)
                        # 가상 입력 포트 생성 (로그 제거)
                        
                        with self._thread_lock:
                            self.virtual_port_active = True
                        # 가상 MIDI 포트 생성 완료 (로그 제거)
                        # 프로프리젠터에서 가상 MIDI 포트를 선택하세요! (로그 제거)
                        
                    except Exception as e:
                        self.logger.error(f"가상 MIDI 포트 생성 실패: {e}")
                        self.cleanup_virtual_ports()
                        # Fallback to simulation mode
                        with self._thread_lock:
                            self.virtual_port_active = True
                        self.logger.info(f"가상 MIDI(S) 포트 시뮬레이션 모드 활성화: '{self.virtual_port_name}'")
                
                # Start port creation in separate thread
                port_thread = threading.Thread(target=create_ports_in_thread, daemon=True, name="VirtualPortCreation")
                port_thread.start()
                
                # Mark as active immediately (ports will be created in background)
                self.virtual_port_active = True
                self._initialized = True
                # 가상 MIDI 포트 생성 시작 (로그 제거)
                
                return True
                
            except Exception as e:
                self.logger.error(f"가상 MIDI 포트 초기화 실패: {e}")
                self.cleanup_virtual_ports()
                # Fallback to simulation mode
                self.virtual_port_active = True
                self._initialized = True
                return True
    
    def _ensure_ports_created(self):
        """Ensure virtual MIDI ports are created (lazy initialization)."""
        if self.virtual_midi_out and self.virtual_midi_in:
            return True  # Already created
        
        if not RTMIDI_AVAILABLE:
            return False
        
        try:
            # Create virtual MIDI ports only when needed
            if not self.virtual_midi_out:
                self.virtual_midi_out = rtmidi.MidiOut()
                self.virtual_midi_out.open_virtual_port(f"{self.virtual_port_name} Out")
                self.logger.info(f"가상 출력 포트 생성: '{self.virtual_port_name} Out'")
            
            if not self.virtual_midi_in:
                self.virtual_midi_in = rtmidi.MidiIn()
                self.virtual_midi_in.open_virtual_port(f"{self.virtual_port_name} In")
                self.virtual_midi_in.set_callback(self._virtual_midi_callback)
                self.logger.info(f"가상 입력 포트 생성: '{self.virtual_port_name} In'")
            
            return True
            
        except Exception as e:
            self.logger.error(f"지연된 가상 MIDI 포트 생성 실패: {e}")
            return False
    
    def cleanup_virtual_ports(self) -> None:
        """Clean up virtual MIDI ports."""
        with self._thread_lock:
            try:
                if self.virtual_midi_out:
                    try:
                        self.virtual_midi_out.close_port()
                    except Exception:
                        pass  # Ignore cleanup errors
                    self.virtual_midi_out = None
                
                if self.virtual_midi_in:
                    try:
                        self.virtual_midi_in.close_port()
                    except Exception:
                        pass  # Ignore cleanup errors
                    self.virtual_midi_in = None
                
                self.virtual_port_active = False
                self._initialized = False
                
            except Exception as e:
                self.logger.error(f"가상 MIDI 포트 정리 오류: {e}")
    
    def _virtual_midi_callback(self, message, data):
        """GIL-safe callback for virtual MIDI input messages."""
        try:
            # Convert rtmidi message to mido message (GIL-safe operation)
            if not message or len(message) == 0:
                return
                
            msg = mido.Message.from_bytes(message[0])
            
            # Queue message for main thread processing (thread-safe)
            try:
                self._message_queue.put_nowait(msg)
                # MIDI 메시지 큐에 추가 (로그 제거)
            except Exception as queue_error:
                self.logger.warning(f"메시지 큐 오류: {queue_error}, 메시지 건너뜀")
                
        except Exception as e:
            self.logger.error(f"가상 MIDI 콜백 오류: {e}")
            # Don't let callback exceptions crash the application
    
    def open_input_port(self, port_name: str) -> bool:
        """Virtual port is always 'open' when active."""
        return self.virtual_port_active
    
    def open_output_port(self, port_name: str) -> bool:
        """Virtual port is always 'open' when active."""
        return self.virtual_port_active
    
    def start_monitoring(self) -> bool:
        """Start MIDI monitoring (virtual port is always ready)."""
        if self._midi_thread and self._midi_thread.is_alive():
            self.logger.warning("MIDI 모니터링이 이미 실행 중입니다")
            return False
        
        if not self.virtual_port_active:
            self.logger.error("가상 MIDI 포트가 활성화되지 않았습니다")
            return False
        
        self._shutdown_event.clear()
        self.logger.info("MIDI 모니터링 시작 (가상 포트)")
        return True
    
    def stop_monitoring(self) -> None:
        """Stop MIDI monitoring and cleanup."""
        self._shutdown_event.set()
        
        if self._midi_thread and self._midi_thread.is_alive():
            self._midi_thread.join(timeout=MIDI_THREAD_TIMEOUT)
        
        self.logger.info("MIDI 모니터링 중지")
    
    # Virtual port doesn't need a separate listener loop
    # Messages are received via callback
    
    def process_queued_messages(self) -> None:
        """Process queued messages from main thread (called by controller)."""
        if not self._message_handler:
            return
        
        # Process all available messages (limit to prevent blocking)
        max_messages = 100  # Process max 100 messages per call
        processed = 0
        
        while processed < max_messages:
            try:
                message = self._message_queue.get_nowait()
                self._message_handler(message)
                processed += 1
            except Empty:
                break
            except Exception as e:
                self.logger.error(f"메시지 처리 오류: {e}")
                break
    
    def send_control_change(self, control: int, value: int, channel: int) -> bool:
        """Send Control Change message to virtual port."""
        if not RTMIDI_AVAILABLE:
            self.logger.debug(f"CC 시뮬레이션: ch={channel} ctl={control} val={value}")
            return True
        
        # Ensure ports are created
        if not self._ensure_ports_created():
            self.logger.debug(f"CC 시뮬레이션 (포트 생성 실패): ch={channel} ctl={control} val={value}")
            return True
        
        try:
            msg = mido.Message('control_change', channel=channel, control=control, value=value)
            self.virtual_midi_out.send_message(msg.bytes())
            self.logger.debug(f"CC 전송: ch={channel} ctl={control} val={value}")
            return True
        except Exception as e:
            self.logger.error(f"CC 전송 오류: {e}")
            return False
    
    def send_program_change(self, program: int, channel: int) -> bool:
        """Send Program Change message to virtual port."""
        if not RTMIDI_AVAILABLE:
            self.logger.debug(f"PC 시뮬레이션: ch={channel} program={program}")
            return True
        
        # Ensure ports are created
        if not self._ensure_ports_created():
            self.logger.debug(f"PC 시뮬레이션 (포트 생성 실패): ch={channel} program={program}")
            return True
        
        try:
            msg = mido.Message('program_change', channel=channel, program=program)
            self.virtual_midi_out.send_message(msg.bytes())
            self.logger.debug(f"PC 전송: ch={channel} program={program}")
            return True
        except Exception as e:
            self.logger.error(f"PC 전송 오류: {e}")
            return False
    
    def send_note_on(self, note: int, velocity: int, channel: int) -> bool:
        """Send Note On message to virtual port."""
        if not RTMIDI_AVAILABLE:
            self.logger.debug(f"Note On 시뮬레이션: ch={channel} note={note} vel={velocity}")
            return True
        
        # Ensure ports are created
        if not self._ensure_ports_created():
            self.logger.debug(f"Note On 시뮬레이션 (포트 생성 실패): ch={channel} note={note} vel={velocity}")
            return True
        
        try:
            msg = mido.Message('note_on', channel=channel, note=note, velocity=velocity)
            self.virtual_midi_out.send_message(msg.bytes())
            self.logger.debug(f"Note On 전송: ch={channel} note={note} vel={velocity}")
            return True
        except Exception as e:
            self.logger.error(f"Note On 전송 오류: {e}")
            return False
    
    def send_note_off(self, note: int, velocity: int, channel: int) -> bool:
        """Send Note Off message to virtual port."""
        if not RTMIDI_AVAILABLE:
            self.logger.debug(f"Note Off 시뮬레이션: ch={channel} note={note} vel={velocity}")
            return True
        
        # Ensure ports are created
        if not self._ensure_ports_created():
            self.logger.debug(f"Note Off 시뮬레이션 (포트 생성 실패): ch={channel} note={note} vel={velocity}")
            return True
        
        try:
            msg = mido.Message('note_off', channel=channel, note=note, velocity=velocity)
            self.virtual_midi_out.send_message(msg.bytes())
            self.logger.debug(f"Note Off 전송: ch={channel} note={note} vel={velocity}")
            return True
        except Exception as e:
            self.logger.error(f"Note Off 전송 오류: {e}")
            return False
    
    def shutdown(self) -> None:
        """Complete shutdown of MIDI backend."""
        with self._thread_lock:
            if not self._initialized:
                return
                
            self.stop_monitoring()
            self.cleanup_virtual_ports()
            self.logger.info("MIDI 백엔드 종료")
