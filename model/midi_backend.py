"""
GIL-safe MIDI backend with proper thread management for macOS + mido environment.
"""
import mido
import threading
from typing import Optional, List, Callable, Any
from queue import Queue, Empty
import time

from config.settings import MIDI_THREAD_DAEMON, MIDI_THREAD_TIMEOUT
from utils.logger import get_logger


class MidiBackend:
    """
    Thread-safe MIDI backend that handles port management and message routing.
    Designed to minimize GIL contention on macOS.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.input_port: Optional[mido.ports.BaseInput] = None
        self.output_port: Optional[mido.ports.BaseOutput] = None
        
        # Thread-safe communication
        self._message_queue = Queue()
        self._control_queue = Queue()
        self._shutdown_event = threading.Event()
        self._thread_lock = threading.Lock()
        self._midi_thread: Optional[threading.Thread] = None
        
        # Callback handlers
        self._message_handler: Optional[Callable] = None
    
    def set_message_handler(self, handler: Callable[[Any], None]) -> None:
        """Set the message handler callback (called from main thread)."""
        self._message_handler = handler
    
    def get_input_ports(self) -> List[str]:
        """Get available MIDI input ports."""
        try:
            ports = mido.get_input_names()
            return ports if ports else ["사용 가능한 포트 없음"]
        except Exception as e:
            self.logger.error(f"입력 포트 가져오기 오류: {e}")
            return ["MIDI 포트 오류"]
    
    def get_output_ports(self) -> List[str]:
        """Get available MIDI output ports."""
        try:
            ports = mido.get_output_names()
            return ports if ports else ["사용 가능한 포트 없음"]
        except Exception as e:
            self.logger.error(f"출력 포트 가져오기 오류: {e}")
            return ["MIDI 포트 오류"]
    
    def open_input_port(self, port_name: str) -> bool:
        """Open MIDI input port with thread safety."""
        with self._thread_lock:
            if self.input_port:
                self.close_input_port()
            
            try:
                self.input_port = mido.open_input(port_name)
                self.logger.info(f"입력 포트 '{port_name}' 연결됨")
                return True
            except Exception as e:
                self.logger.error(f"입력 포트 '{port_name}' 연결 실패: {e}")
                return False
    
    def open_output_port(self, port_name: str) -> bool:
        """Open MIDI output port with thread safety."""
        with self._thread_lock:
            if self.output_port:
                self.close_output_port()
            
            try:
                self.output_port = mido.open_output(port_name)
                self.logger.info(f"출력 포트 '{port_name}' 연결됨")
                return True
            except Exception as e:
                self.logger.error(f"출력 포트 '{port_name}' 연결 실패: {e}")
                return False
    
    def close_input_port(self) -> None:
        """Close MIDI input port safely."""
        with self._thread_lock:
            if self.input_port:
                try:
                    self.input_port.close()
                except Exception as e:
                    self.logger.error(f"입력 포트 닫기 오류: {e}")
                finally:
                    self.input_port = None
    
    def close_output_port(self) -> None:
        """Close MIDI output port safely."""
        with self._thread_lock:
            if self.output_port:
                try:
                    self.output_port.close()
                except Exception as e:
                    self.logger.error(f"출력 포트 닫기 오류: {e}")
                finally:
                    self.output_port = None
    
    def start_monitoring(self) -> bool:
        """Start MIDI monitoring in separate thread."""
        if self._midi_thread and self._midi_thread.is_alive():
            self.logger.warning("MIDI 모니터링이 이미 실행 중입니다")
            return False
        
        if not self.input_port:
            self.logger.error("입력 포트가 연결되지 않았습니다")
            return False
        
        self._shutdown_event.clear()
        self._midi_thread = threading.Thread(
            target=self._midi_listener_loop,
            daemon=MIDI_THREAD_DAEMON,
            name="MidiListener"
        )
        self._midi_thread.start()
        self.logger.info("MIDI 모니터링 시작")
        return True
    
    def stop_monitoring(self) -> None:
        """Stop MIDI monitoring and cleanup."""
        self._shutdown_event.set()
        
        # Close input port to break the listener loop
        self.close_input_port()
        
        if self._midi_thread and self._midi_thread.is_alive():
            self._midi_thread.join(timeout=MIDI_THREAD_TIMEOUT)
        
        self.logger.info("MIDI 모니터링 중지")
    
    def _midi_listener_loop(self) -> None:
        """
        Main MIDI listener loop running in separate thread.
        Minimizes GIL contention by using short polling intervals.
        """
        try:
            if not self.input_port:
                return
            
            # Use timeout to allow periodic checking of shutdown event
            for message in self.input_port:
                if self._shutdown_event.is_set():
                    break
                
                # Queue message for main thread processing
                try:
                    self._message_queue.put_nowait(message)
                except:
                    # Queue full, skip message to avoid blocking
                    self.logger.warning("메시지 큐가 가득참, 메시지 건너뜀")
                
                # Small delay to yield GIL
                time.sleep(0.001)
                
        except Exception as e:
            self.logger.error(f"MIDI 리스너 오류: {e}")
        finally:
            self.logger.info("MIDI 리스너 스레드 종료")
    
    def process_queued_messages(self) -> None:
        """Process queued messages from main thread (called by controller)."""
        if not self._message_handler:
            return
        
        # Process all available messages
        while True:
            try:
                message = self._message_queue.get_nowait()
                self._message_handler(message)
            except Empty:
                break
            except Exception as e:
                self.logger.error(f"메시지 처리 오류: {e}")
    
    def send_control_change(self, control: int, value: int, channel: int) -> bool:
        """Send Control Change message thread-safely."""
        if not self.output_port:
            self.logger.error("출력 포트가 연결되지 않았습니다")
            return False
        
        try:
            msg = mido.Message('control_change', channel=channel, control=control, value=value)
            self.output_port.send(msg)
            self.logger.debug(f"CC 전송: ch={channel} ctl={control} val={value}")
            return True
        except Exception as e:
            self.logger.error(f"CC 전송 오류: {e}")
            return False
    
    def send_program_change(self, program: int, channel: int) -> bool:
        """Send Program Change message thread-safely."""
        if not self.output_port:
            self.logger.error("출력 포트가 연결되지 않았습니다")
            return False
        
        try:
            msg = mido.Message('program_change', channel=channel, program=program)
            self.output_port.send(msg)
            self.logger.debug(f"PC 전송: ch={channel} program={program}")
            return True
        except Exception as e:
            self.logger.error(f"PC 전송 오류: {e}")
            return False
    
    def send_note_on(self, note: int, velocity: int, channel: int) -> bool:
        """Send Note On message thread-safely."""
        if not self.output_port:
            self.logger.error("출력 포트가 연결되지 않았습니다")
            return False
        
        try:
            msg = mido.Message('note_on', channel=channel, note=note, velocity=velocity)
            self.output_port.send(msg)
            self.logger.debug(f"Note On 전송: ch={channel} note={note} vel={velocity}")
            return True
        except Exception as e:
            self.logger.error(f"Note On 전송 오류: {e}")
            return False
    
    def send_note_off(self, note: int, velocity: int, channel: int) -> bool:
        """Send Note Off message thread-safely."""
        if not self.output_port:
            self.logger.error("출력 포트가 연결되지 않았습니다")
            return False
        
        try:
            msg = mido.Message('note_off', channel=channel, note=note, velocity=velocity)
            self.output_port.send(msg)
            self.logger.debug(f"Note Off 전송: ch={channel} note={note} vel={velocity}")
            return True
        except Exception as e:
            self.logger.error(f"Note Off 전송 오류: {e}")
            return False
    
    def shutdown(self) -> None:
        """Complete shutdown of MIDI backend."""
        self.stop_monitoring()
        self.close_input_port()
        self.close_output_port()
        self.logger.info("MIDI 백엔드 종료")
