"""
DM3 OSC communication service.
Handles OSC communication with DM3 mixer for scene recall and mute control.
"""
import socket
import subprocess
import platform
import threading
import time
from typing import Optional, Dict, Any, Tuple
from pythonosc import udp_client

from model.base_service import BaseMidiService
from utils.logger import get_logger


class DM3OSCService(BaseMidiService):
    """
    Handles OSC communication with DM3 mixer.
    Thread-safe implementation with connection monitoring.
    """
    
    def __init__(self, mixer_name: str, midi_backend):
        super().__init__()
        self.logger = get_logger(__name__)
        self.mixer_name = mixer_name
        self.midi_backend = midi_backend
        
        # DM3 OSC client
        self.dm3_client: Optional[udp_client.SimpleUDPClient] = None
        self.dm3_ip = "192.168.4.2"  # DM3 mixer IP (default)
        self.dm3_port = 49900  # DM3 OSC port (default)
        
        # Connection state
        self.dm3_connected = False
        self.connection_monitor_active = False
        self.connection_monitor_thread: Optional[threading.Thread] = None
        self._connection_lock = threading.RLock()
        self._last_ping_time = 0.0
        self._ping_interval = 3.0  # Ping every 3 seconds
    
    def set_connection_params(self, ip: str, port: int) -> None:
        """Set DM3 connection parameters."""
        self.dm3_ip = ip
        self.dm3_port = port
        self.logger.info(f"DM3 연결 설정: {ip}:{port}")
    
    def connect(self) -> bool:
        """Connect to DM3 mixer via OSC."""
        with self._connection_lock:
            if self.dm3_connected:
                self.logger.info("DM3가 이미 연결되어 있습니다")
                return True
                
            try:
                self.logger.info(f"🔍 DM3 연결 시도: {self.dm3_ip}:{self.dm3_port}")
                
                # 1. Network connectivity test
                if not self.ping_host(self.dm3_ip):
                    raise Exception(f"Ping 테스트 실패: {self.dm3_ip} - 네트워크 연결을 확인하세요")
                
                # 2. Create OSC client
                self.dm3_client = udp_client.SimpleUDPClient(self.dm3_ip, self.dm3_port)
                
                # 3. Test OSC connection
                try:
                    self.dm3_client.send_message("/test_connection", "ping")
                    self.logger.info("✅ OSC 테스트 메시지 전송 완료")
                except Exception as osc_error:
                    self.logger.warning(f"⚠️ OSC 테스트 메시지 전송 실패: {osc_error}")
                    self.logger.info("OSC 전송 실패했지만 연결은 계속 진행합니다")
                
                # 4. Connection successful
                self.dm3_connected = True
                self.logger.info(f"🎉 DM3 믹서 연결 성공: {self.dm3_ip}:{self.dm3_port}")
                
                # 5. Start connection monitoring
                self.start_connection_monitor()
                
                return True
                
            except Exception as e:
                self.logger.error(f"❌ DM3 연결 실패: {e}")
                self.dm3_client = None
                self.dm3_connected = False
                return False
    
    def disconnect(self) -> None:
        """Disconnect from DM3 mixer."""
        with self._connection_lock:
            self.stop_connection_monitor()
            self.dm3_client = None
            self.dm3_connected = False
            self.logger.info("DM3 믹서 연결 해제됨")
    
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
    
    def start_connection_monitor(self) -> None:
        """Start connection monitoring thread."""
        if self.connection_monitor_active:
            return
        
        self.connection_monitor_active = True
        self.connection_monitor_thread = threading.Thread(
            target=self.connection_monitor, 
            daemon=True,
            name="DM3ConnectionMonitor"
        )
        self.connection_monitor_thread.start()
        self.logger.info("DM3 연결 상태 모니터링 시작")
    
    def stop_connection_monitor(self) -> None:
        """Stop connection monitoring thread."""
        self.connection_monitor_active = False
        if self.connection_monitor_thread and self.connection_monitor_thread.is_alive():
            self.connection_monitor_thread.join(timeout=2.0)
        self.logger.info("DM3 연결 상태 모니터링 중지")
    
    def connection_monitor(self) -> None:
        """Monitor DM3 connection status."""
        consecutive_failures = 0
        max_failures = 3
        
        while self.connection_monitor_active and self.dm3_connected:
            try:
                time.sleep(3)  # Check every 3 seconds
                
                if not self.dm3_connected:
                    break
                
                # Test connection
                ping_success = self.ping_host(self.dm3_ip)
                
                if ping_success:
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    self.logger.warning(f"⚠️ DM3 연결 실패 ({consecutive_failures}/{max_failures})")
                    
                    if consecutive_failures >= max_failures:
                        self.logger.error("🚨 DM3 연결이 완전히 끊어졌습니다.")
                        self.dm3_connected = False
                        self.dm3_client = None
                        break
                        
            except Exception as e:
                self.logger.error(f"DM3 연결 모니터링 오류: {e}")
                consecutive_failures += 1
                
                if consecutive_failures >= max_failures:
                    self.dm3_connected = False
                    self.dm3_client = None
                    break
    
    def send_osc_message(self, address: str, *args) -> bool:
        """Send OSC message to DM3."""
        with self._connection_lock:
            if not self.dm3_connected or not self.dm3_client:
                self.logger.warning("⚠️ DM3에 연결되지 않음")
                return False
            
            try:
                self.dm3_client.send_message(address, args)
                # DM3 OSC 전송 (로그 제거)
                return True
            except Exception as e:
                self.logger.error(f"❌ DM3 OSC 전송 실패: {e}")
                # Mark as disconnected on send failure
                self.dm3_connected = False
                return False
    
    def handle_mute(self, note: int, velocity: int, channel: int) -> None:
        """Handle mute control for DM3."""
        if not self.dm3_connected:
            return
        
        # DM3 mute control: note represents channel number (0-based)
        channel_num = note + 1  # Convert to 1-based channel number
        
        if velocity >= 1:
            # Mute channel
            self.mute_channel(channel_num)
        else:
            # Unmute channel
            self.unmute_channel(channel_num)
    
    def handle_scene(self, note: int, channel: int) -> None:
        """Handle scene recall for DM3."""
        if not self.dm3_connected:
            return
        
        # DM3 scene recall: note represents scene number (0-based)
        scene_number = note + 1  # Convert to 1-based scene number
        self.recall_scene_by_number(scene_number)
    
    def mute_channel(self, channel_num: int) -> None:
        """Mute specific channel on DM3."""
        try:
            # DM3 OSC address format: /yosc:req/set/MIXER:Current/InCh/Fader/On/<channel>/1 0
            address = f"/yosc:req/set/MIXER:Current/InCh/Fader/On/{channel_num}/1"
            self.send_osc_message(address, 0)  # 0 = OFF (mute)
            self.logger.info(f"🔇 DM3 {channel_num}번 채널 뮤트")
            
        except Exception as e:
            self.logger.error(f"❌ DM3 채널 뮤트 실패: {e}")
    
    def unmute_channel(self, channel_num: int) -> None:
        """Unmute specific channel on DM3."""
        try:
            # DM3 OSC address format: /yosc:req/set/MIXER:Current/InCh/Fader/On/<channel>/1 1
            address = f"/yosc:req/set/MIXER:Current/InCh/Fader/On/{channel_num}/1"
            self.send_osc_message(address, 1)  # 1 = ON (unmute)
            self.logger.info(f"🔊 DM3 {channel_num}번 채널 뮤트 해제")
            
        except Exception as e:
            self.logger.error(f"❌ DM3 채널 뮤트 해제 실패: {e}")
    
    def recall_scene_by_number(self, scene_number: int) -> None:
        """Recall scene by number on DM3."""
        try:
            # DM3 scene recall: scene_a format with 0-based index
            scene_name = "scene_a"
            scene_index = scene_number - 1  # Convert to 0-based index
            
            if scene_index < 0 or scene_index > 99:
                self.logger.warning(f"⚠️ 잘못된 씬 번호: {scene_number} (1-100 범위)")
                return
            
            # DM3 OSC address format: /yosc:req/ssrecall_ex "scene_a" <index>
            address = "/yosc:req/ssrecall_ex"
            self.send_osc_message(address, scene_name, scene_index)
            self.logger.info(f"🎬 DM3 씬 리콜: {scene_number}번 씬 (scene_a {scene_index:02d})")
            
        except Exception as e:
            self.logger.error(f"❌ DM3 씬 리콜 실패: {e}")
    
    def update_mixer_config(self, mixer_name: str) -> None:
        """Update mixer configuration (DM3 specific)."""
        self.mixer_name = mixer_name
        self.logger.info(f"DM3 믹서 설정 업데이트: {mixer_name}")
    
    def shutdown(self) -> None:
        """Shutdown the service."""
        self.disconnect()
        self.logger.info("DM3 OSC 서비스 종료")
