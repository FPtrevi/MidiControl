"""
Qu-5 MIDI communication service.
Handles MIDI communication with Qu-5/6/7 mixer via TCP/IP or USB MIDI.
"""
import socket
import subprocess
import platform
import threading
import time
import mido
from typing import Optional, Dict, Any, List, Tuple

from model.base_service import BaseMidiService
from utils.logger import get_logger


class Qu5MIDIService(BaseMidiService):
    """
    Handles MIDI communication with Qu-5/6/7 mixer.
    Supports both TCP/IP MIDI and USB MIDI connections.
    """
    
    def __init__(self, mixer_name: str, midi_backend):
        super().__init__()
        self.logger = get_logger(__name__)
        self.mixer_name = mixer_name
        self.midi_backend = midi_backend
        
        # Qu-5 connection parameters
        self.qu5_ip = "192.168.5.10"  # Qu-5 mixer IP (default)
        self.qu5_port = 51325  # Qu-5 MIDI port (TCP/IP)
        self.qu5_midi_channel = 1  # Qu-5 MIDI channel
        
        # Connection type
        self.use_tcp_midi = True  # TCP/IP MIDI vs USB MIDI
        
        # Network connection
        self.qu5_socket: Optional[socket.socket] = None
        self.qu5_connected = False
        self._connection_lock = threading.RLock()
        self._last_ping_time = 0.0
        self._ping_interval = 3.0  # Ping every 3 seconds
    
    def set_connection_params(self, ip: str, port: int, channel: int, use_tcp: bool = True) -> None:
        """Set Qu-5 connection parameters."""
        self.qu5_ip = ip
        self.qu5_port = port
        self.qu5_midi_channel = channel
        self.use_tcp_midi = use_tcp
        self.logger.info(f"Qu-5 연결 설정: {ip}:{port}, 채널:{channel}, TCP/IP:{use_tcp}")
    
    def connect(self) -> bool:
        """Connect to Qu-5 mixer."""
        with self._connection_lock:
            if self.qu5_connected:
                self.logger.info("Qu-5가 이미 연결되어 있습니다")
                return True
                
            try:
                if self.use_tcp_midi:
                    return self._connect_tcp_midi()
                else:
                    return self._connect_usb_midi()
            except Exception as e:
                self.logger.error(f"❌ Qu-5 연결 실패: {e}")
                return False
    
    def _connect_tcp_midi(self) -> bool:
        """Connect to Qu-5 via TCP/IP MIDI."""
        try:
            self.logger.info(f"🔍 Qu-5 TCP/IP MIDI 연결 시도: {self.qu5_ip}:{self.qu5_port}")
            
            # 1. Network connectivity test
            if not self.ping_host(self.qu5_ip):
                raise Exception(f"Ping 테스트 실패: {self.qu5_ip}")
            
            # 2. TCP connection test
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.settimeout(3)
            result = test_sock.connect_ex((self.qu5_ip, self.qu5_port))
            test_sock.close()
            
            if result != 0:
                raise Exception(f"TCP 포트 연결 실패: {self.qu5_ip}:{self.qu5_port}")
            
            # 3. Create TCP socket
            self.qu5_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.qu5_socket.settimeout(5)
            self.qu5_socket.connect((self.qu5_ip, self.qu5_port))
            
            self.qu5_connected = True
            self.logger.info(f"🎉 Qu-5 TCP/IP MIDI 연결 성공: {self.qu5_ip}:{self.qu5_port}")
            return True
            
        except Exception as e:
            if self.qu5_socket:
                self.qu5_socket.close()
                self.qu5_socket = None
            self.qu5_connected = False
            raise e
    
    def _connect_usb_midi(self) -> bool:
        """Connect to Qu-5 via USB MIDI (placeholder - would need mido output port)."""
        try:
            self.logger.info("🔍 Qu-5 USB MIDI 연결 시도...")
            
            # USB MIDI connection would require finding the Qu-5 USB MIDI port
            # For now, we'll simulate success but this would need actual implementation
            self.qu5_connected = True
            self.logger.info("🎉 Qu-5 USB MIDI 연결 성공 (시뮬레이션)")
            return True
            
        except Exception as e:
            self.qu5_connected = False
            raise e
    
    def disconnect(self) -> None:
        """Disconnect from Qu-5 mixer."""
        with self._connection_lock:
            if self.qu5_socket:
                try:
                    self.qu5_socket.close()
                except Exception:
                    pass  # Ignore errors during cleanup
                self.qu5_socket = None
            
            self.qu5_connected = False
            self.logger.info("Qu-5 믹서 연결 해제됨")
    
    def ping_host(self, ip: str) -> bool:
        """Test host connectivity with ping (with caching)."""
        current_time = time.time()
        
        # Use cached result if ping was done recently
        if current_time - self._last_ping_time < self._ping_interval:
            return True  # Assume still connected if pinged recently
            
        try:
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", "1", "-w", "2000", ip]
            else:
                cmd = ["ping", "-c", "1", "-W", "2", ip]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
            success = result.returncode == 0
            
            if success:
                self._last_ping_time = current_time
                
            return success
            
        except Exception as e:
            self.logger.error(f"Ping 테스트 예외: {e}")
            return False
    
    def send_midi_message(self, message) -> bool:
        """Send MIDI message to Qu-5."""
        with self._connection_lock:
            if not self.qu5_connected:
                self.logger.warning("⚠️ Qu-5에 연결되지 않음")
                return False
            
            try:
                # Prepare raw bytes and hex dump for logging
                midi_bytes = bytes(message.bytes())
                hex_dump = ' '.join(f"{b:02X}" for b in midi_bytes)
                
                if self.use_tcp_midi and self.qu5_socket:
                    # TCP/IP MIDI transmission
                    self.qu5_socket.send(midi_bytes)
                    self.logger.info(
                        f"➡️ [TX][TCP] type={message.type} ch={getattr(message, 'channel', 'n/a')} data=[{hex_dump}]"
                    )
                    return True
                else:
                    # USB MIDI transmission would go here
                    self.logger.info(
                        f"➡️ [TX][USB] type={message.type} ch={getattr(message, 'channel', 'n/a')} data=[{hex_dump}]"
                    )
                    return True
                    
            except Exception as e:
                self.logger.error(f"❌ Qu-5 MIDI 전송 실패: {e}")
                # Mark as disconnected on send failure
                self.qu5_connected = False
                return False
    
    def handle_mute(self, note: int, velocity: int, channel: int, mixer_midi_channel: int = None) -> None:
        """Handle mute control for Qu-5 using NRPN."""
        if not self.qu5_connected:
            return
        
        # Use provided MIDI channel or fall back to configured one
        midi_channel = mixer_midi_channel if mixer_midi_channel is not None else self.qu5_midi_channel
        
        # Qu-5 mute control: note represents channel number (0-based)
        # Note 0-15 represents mixer channels 1-16
        if note < 0 or note > 15:
            self.logger.warning(f"⚠️ 잘못된 채널 번호: {note} (0-15 범위여야 함)")
            return
            
        channel_num = note + 1  # Convert to 1-based channel number
        mute_on_off = 1 if velocity >= 1 else 0
        
        self.logger.info(f"🔇 Qu-5 뮤트 제어: 채널 {channel_num}, 뮤트: {mute_on_off}, MIDI 채널: {midi_channel}")
        self.send_nrpn_mute_sequence(channel_num, mute_on_off, midi_channel)
    
    def handle_scene(self, note: int, channel: int, mixer_midi_channel: int = None) -> None:
        """Handle scene recall for Qu-5."""
        if not self.qu5_connected:
            return
        
        # Use provided MIDI channel or fall back to configured one
        midi_channel = mixer_midi_channel if mixer_midi_channel is not None else self.qu5_midi_channel
        
        # Qu-5 scene recall: note represents scene number (0-based from source)
        if note < 0 or note > 99:  # Qu-5 supports up to 100 scenes
            self.logger.warning(f"⚠️ 잘못된 씬 번호: {note} (0-99 범위여야 함)")
            return
            
        # Note 0 -> Scene 1, Note 1 -> Scene 2 ... (+1 offset required by mixer)
        scene_number = note + 1
        self.logger.info(f"🎬 Qu-5 씬 리콜: {scene_number}번 씬, MIDI 채널: {midi_channel}")
        self.recall_scene_by_number(scene_number, midi_channel)
    
    def handle_softkey(self, note: int, channel: int, mixer_midi_channel: int = None) -> None:
        """Handle soft key control for Qu-5."""
        if not self.qu5_connected:
            return
        
        # Use provided MIDI channel or fall back to configured one
        midi_channel = mixer_midi_channel if mixer_midi_channel is not None else self.qu5_midi_channel
        
        # Qu-5 soft key control: note represents soft key number (0-based)
        if note < 0 or note > 7:  # Qu-5 has 8 soft keys
            self.logger.warning(f"⚠️ 잘못된 소프트키 번호: {note} (0-7 범위여야 함)")
            return
            
        # Note 0-7 directly corresponds to soft key 0-7 (0-based)
        softkey_number = note  # Keep as 0-based for Qu-5
        self.logger.info(f"🔘 Qu-5 소프트키 제어: {softkey_number}번 소프트키 (0-based), MIDI 채널: {midi_channel}")
        self.send_softkey_command(softkey_number, midi_channel)
    
    def send_nrpn_mute_sequence(self, channel_num: int, mute_value: int, mixer_midi_channel: int = None) -> None:
        """Send NRPN mute sequence to Qu-5."""
        try:
            # Use provided MIDI channel or fall back to configured one
            midi_channel = (mixer_midi_channel if mixer_midi_channel is not None else self.qu5_midi_channel) - 1  # Convert to 0-based MIDI channel
            
            self.logger.info(
                f"🧩 NRPN 뮤트 시퀀스 시작: target_ch={channel_num} (midi_ch={midi_channel+1}), mute={mute_value}"
            )
            
            # Qu-5 NRPN mute sequence for specific channel:
            # CC 99 = 0 (MSB) - NRPN parameter number MSB
            # CC 98 = channel_num-1 (LSB) - Channel number (0-based)
            # CC 6 = 0 (Data Entry MSB) - Mute parameter
            # CC 38 = mute_value (1=mute, 0=unmute) - Mute value
            
            sequence: List[Tuple[str, int, int, int]] = [
                ('control_change', 99, 0, midi_channel),           # NRPN MSB = 0
                ('control_change', 98, channel_num - 1, midi_channel),  # Channel number (0-based)
                ('control_change', 6, 0, midi_channel),            # Data Entry MSB = 0
                ('control_change', 38, mute_value, midi_channel)   # Mute value
            ]
            
            for msg_type, control, value, ch in sequence:
                msg = mido.Message(msg_type, channel=ch, control=control, value=value)
                if not self.send_midi_message(msg):
                    self.logger.error(f"NRPN CC#{control} 전송 실패")
                    return
                # Small delay between messages for proper sequencing
                time.sleep(0.01)
            
            action = "뮤트" if mute_value else "뮤트 해제"
            self.logger.info(f"🔇 Qu-5 {channel_num}번 채널 {action} 완료")
            
        except Exception as e:
            self.logger.error(f"❌ Qu-5 NRPN 뮤트 시퀀스 실패: {e}")
    
    def send_softkey_command(self, softkey_number: int, mixer_midi_channel: int = None) -> None:
        """Send soft key command to Qu-5 using Note On/Off (notes start at 0x30)."""
        try:
            # Use provided MIDI channel or fall back to configured one
            midi_channel = (mixer_midi_channel if mixer_midi_channel is not None else self.qu5_midi_channel) - 1  # Convert to 0-based MIDI channel
            
            self.logger.info(
                f"🔘 소프트키 트리거 시작: softkey_index={softkey_number} (0-based), midi_ch={midi_channel+1}"
            )
            
            # Qu-5 soft key control uses Note On/Off with notes starting at 0x30 for SoftKey 1
            # softkey_number is 0-based from input; compute MIDI note number:
            midi_note = 0x30 + softkey_number
            
            note_on = mido.Message('note_on', channel=midi_channel, note=midi_note, velocity=127)
            note_off = mido.Message('note_off', channel=midi_channel, note=midi_note, velocity=0)
            
            ok_on = self.send_midi_message(note_on)
            time.sleep(0.02)
            ok_off = self.send_midi_message(note_off)
            
            if ok_on and ok_off:
                self.logger.info(f"🔘 Qu-5 소프트키 트리거 완료: idx={softkey_number}, note=0x{midi_note:02X}")
            else:
                self.logger.error("❌ Qu-5 소프트키 Note On/Off 전송 실패")
            
        except Exception as e:
            self.logger.error(f"❌ Qu-5 소프트키 명령 실패: {e}")
    
    def recall_scene_by_number(self, scene_number: int, mixer_midi_channel: int = None) -> None:
        """Recall scene by number on Qu-5 using Program Change only."""
        try:
            # Use provided MIDI channel or fall back to configured one
            midi_channel = (mixer_midi_channel if mixer_midi_channel is not None else self.qu5_midi_channel) - 1  # Convert to 0-based MIDI channel
            
            self.logger.info(
                f"🎬 씬 리콜 시작: scene={scene_number}, midi_ch={midi_channel+1} (Program Change)"
            )
            
            # Scene recall via Program Change: program is (scene_number - 1)
            program_msg = mido.Message('program_change', channel=midi_channel, program=max(0, scene_number - 1))
            if self.send_midi_message(program_msg):
                self.logger.info(f"🎬 Qu-5 {scene_number}번 씬 리콜 완료 (PC={scene_number - 1})")
            else:
                self.logger.error("❌ Program Change 전송 실패")
            
        except Exception as e:
            self.logger.error(f"❌ Qu-5 씬 리콜 실패: {e}")
    
    def update_mixer_config(self, mixer_name: str) -> None:
        """Update mixer configuration (Qu-5 specific)."""
        self.mixer_name = mixer_name
        self.logger.info(f"Qu-5 믹서 설정 업데이트: {mixer_name}")
    
    def shutdown(self) -> None:
        """Shutdown the service."""
        self.disconnect()
        self.logger.info("Qu-5 MIDI 서비스 종료")
