#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qu-5/6/7 믹서용 MIDI 컨트롤러
Allen & Heath Qu-5/6/7 믹서를 MIDI 신호로 제어합니다.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import mido
import threading
import time
import socket
import subprocess
import platform

class Qu5MIDIController:
    def __init__(self, root):
        self.root = root
        self.root.title("Qu-5/6/7 MIDI 컨트롤러")
        self.root.geometry("600x500")
        
        # Qu-5 믹서 설정
        self.qu5_ip = tk.StringVar(value="192.168.5.10")  # Qu-5 믹서 IP
        self.qu5_port = tk.StringVar(value="51325")  # Qu-5 MIDI 포트 (TCP/IP)
        self.qu5_midi_channel = tk.StringVar(value="1")  # Qu-5 MIDI 채널
        
        # MIDI 메시지 전송 방식 (TCP/IP vs USB MIDI)
        self.use_tcp_midi = tk.BooleanVar(value=True)  # TCP/IP MIDI 사용 여부
        
        # MIDI 설정
        self.midi_input = None
        self.midi_input_port = tk.StringVar()
        self.midi_running = False
        self.midi_thread = None
        
        # Qu-5 MIDI 출력 (USB MIDI용)
        self.qu5_midi_output = None
        
        # 네트워크 연결
        self.qu5_socket = None
        self.qu5_connected = False
        
        # 로그 창
        self.log_text = None
        
        # GUI 구성
        self.setup_gui()
        
        # MIDI 입력 포트 목록 업데이트
        self.update_midi_ports()
    
    def setup_gui(self):
        """GUI를 구성합니다."""
        
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Qu-5 믹서 설정 프레임
        qu5_frame = ttk.LabelFrame(main_frame, text="Qu-5/6/7 믹서 설정", padding="5")
        qu5_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(qu5_frame, text="IP 주소:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(qu5_frame, textvariable=self.qu5_ip, width=15).grid(row=0, column=1, padx=(5, 10))
        
        ttk.Label(qu5_frame, text="포트:").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(qu5_frame, textvariable=self.qu5_port, width=10).grid(row=0, column=3, padx=(5, 10))
        
        ttk.Label(qu5_frame, text="MIDI 채널:").grid(row=0, column=4, sticky=tk.W)
        ttk.Entry(qu5_frame, textvariable=self.qu5_midi_channel, width=5).grid(row=0, column=5, padx=(5, 10))
        
        # 연결 방식 선택
        ttk.Checkbutton(qu5_frame, text="TCP/IP MIDI", variable=self.use_tcp_midi).grid(row=0, column=6, padx=(5, 0))
        
        ttk.Button(qu5_frame, text="Qu-5 연결", command=self.connect_qu5).grid(row=0, column=7, padx=(5, 0))
        ttk.Button(qu5_frame, text="Qu-5 연결 해제", command=self.disconnect_qu5).grid(row=0, column=8, padx=(5, 0))
        
        # Qu-5 상태 표시
        self.qu5_status_label = ttk.Label(qu5_frame, text="Qu-5 연결 안됨", foreground="red")
        self.qu5_status_label.grid(row=0, column=9, padx=(10, 0))
        
        # MIDI 설정 프레임
        midi_frame = ttk.LabelFrame(main_frame, text="MIDI 설정", padding="5")
        midi_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(midi_frame, text="MIDI 입력:").grid(row=0, column=0, sticky=tk.W)
        self.midi_port_combo = ttk.Combobox(midi_frame, textvariable=self.midi_input_port, width=30, state="readonly")
        self.midi_port_combo.grid(row=0, column=1, padx=(5, 10))
        
        ttk.Button(midi_frame, text="포트 새로고침", command=self.update_midi_ports).grid(row=0, column=2, padx=(5, 0))
        ttk.Button(midi_frame, text="MIDI 시작", command=self.start_midi).grid(row=0, column=3, padx=(5, 0))
        ttk.Button(midi_frame, text="MIDI 중지", command=self.stop_midi).grid(row=0, column=4, padx=(5, 0))
        
        # MIDI 상태 표시
        self.midi_status_label = ttk.Label(midi_frame, text="MIDI 중지됨", foreground="red")
        self.midi_status_label.grid(row=0, column=5, padx=(10, 0))
        
        # 테스트 컨트롤 프레임
        test_frame = ttk.LabelFrame(main_frame, text="테스트 컨트롤", padding="5")
        test_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 1번 채널 뮤트 테스트
        ttk.Label(test_frame, text="1번 채널 뮤트 테스트:").grid(row=0, column=0, sticky=tk.W)
        ttk.Button(test_frame, text="1번 채널 뮤트", 
                  command=self.mute_channel_1).grid(row=0, column=1, padx=(5, 5))
        ttk.Button(test_frame, text="1번 채널 뮤트 해제", 
                  command=self.unmute_channel_1).grid(row=0, column=2, padx=(5, 5))
        
        # 네트워크 테스트
        ttk.Button(test_frame, text="네트워크 테스트", 
                  command=self.test_network).grid(row=1, column=0, padx=(5, 5), pady=(5, 0))
        ttk.Button(test_frame, text="MIDI 테스트", 
                  command=self.test_midi).grid(row=1, column=1, padx=(5, 5), pady=(5, 0))
        
        # MIDI 매핑 정보
        mapping_frame = ttk.LabelFrame(main_frame, text="Qu-5/6/7 MIDI 매핑 정보", padding="5")
        mapping_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        mapping_text = """
Qu-5/6/7 MIDI 매핑 (NRPN 방식):
- 1번 채널 뮤트: NRPN 시퀀스 (CC 99, 98, 6, 38)
- MIDI 채널: 1 (기본값)
- 연결 방식: TCP/IP 또는 USB MIDI

NRPN 뮤트 시퀀스:
- CC 99 = 0 (MSB)
- CC 98 = 0 (LSB)
- CC 6 = 0 (Data Entry MSB)
- CC 38 = 1 (뮤트) 또는 0 (뮤트 해제)

실제 전송 예시:
- 뮤트: ch=0 ctl=99 val=0, ch=0 ctl=98 val=0, ch=0 ctl=6 val=0, ch=0 ctl=38 val=1
- 뮤트 해제: ch=0 ctl=99 val=0, ch=0 ctl=98 val=0, ch=0 ctl=6 val=0, ch=0 ctl=38 val=0
        """
        
        mapping_label = ttk.Label(mapping_frame, text=mapping_text.strip(), justify=tk.LEFT)
        mapping_label.grid(row=0, column=0, sticky=tk.W)
        
        # 로그 창
        log_frame = ttk.LabelFrame(main_frame, text="로그", padding="5")
        log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, width=70)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 로그 지우기 버튼
        ttk.Button(log_frame, text="로그 지우기", command=self.clear_log).grid(row=1, column=0, pady=(5, 0))
        
        # 그리드 가중치 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
    
    def update_midi_ports(self):
        """MIDI 입력 포트 목록을 업데이트합니다."""
        try:
            ports = mido.get_input_names()
            self.midi_port_combo['values'] = ports
            if ports and not self.midi_input_port.get():
                self.midi_input_port.set(ports[0])
            self.log_message(f"MIDI 포트 목록 업데이트: {len(ports)}개 포트 발견")
        except Exception as e:
            self.log_message(f"MIDI 포트 목록 업데이트 실패: {e}")
    
    def connect_qu5(self):
        """Qu-5 믹서에 연결합니다 (TCP/IP 또는 USB MIDI)."""
        try:
            if self.use_tcp_midi.get():
                # TCP/IP MIDI 연결
                ip = self.qu5_ip.get()
                port = int(self.qu5_port.get())
                
                self.log_message(f"🔍 Qu-5 TCP/IP MIDI 연결 시도: {ip}:{port}")
                
                # TCP/IP 소켓 연결
                self.qu5_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.qu5_socket.settimeout(5)  # 5초 타임아웃
                
                # 연결 시도
                self.qu5_socket.connect((ip, port))
                
                # 연결 성공
                self.qu5_connected = True
                self.qu5_status_label.config(text="Qu-5 TCP/IP 연결됨", foreground="green")
                self.log_message(f"🎉 Qu-5 TCP/IP MIDI 연결 성공: {ip}:{port}")
                
            else:
                # USB MIDI 연결
                self.log_message("🔍 Qu-5 USB MIDI 연결 시도...")
                
                # Qu-5 USB MIDI 출력 포트 찾기
                output_ports = mido.get_output_names()
                qu5_port = None
                
                for port in output_ports:
                    if 'qu' in port.lower() or 'qu-5' in port.lower() or 'qu-6' in port.lower() or 'qu-7' in port.lower():
                        qu5_port = port
                        break
                
                if qu5_port:
                    self.qu5_midi_output = mido.open_output(qu5_port)
                    self.qu5_connected = True
                    self.qu5_status_label.config(text="Qu-5 USB MIDI 연결됨", foreground="green")
                    self.log_message(f"🎉 Qu-5 USB MIDI 연결 성공: {qu5_port}")
                else:
                    raise Exception("Qu-5 USB MIDI 포트를 찾을 수 없습니다. 사용 가능한 포트: " + str(output_ports))
            
        except Exception as e:
            # 연결 실패 시 상태 초기화
            if self.qu5_socket:
                self.qu5_socket.close()
                self.qu5_socket = None
            if self.qu5_midi_output:
                self.qu5_midi_output.close()
                self.qu5_midi_output = None
                
            self.qu5_connected = False
            self.qu5_status_label.config(text="Qu-5 연결 안됨", foreground="red")
            messagebox.showerror("연결 오류", f"Qu-5 믹서 연결 실패: {e}")
            self.log_message(f"❌ Qu-5 연결 실패: {e}")
    
    def disconnect_qu5(self):
        """Qu-5 믹서 연결을 해제합니다."""
        if self.qu5_socket:
            self.qu5_socket.close()
            self.qu5_socket = None
        
        if self.qu5_midi_output:
            self.qu5_midi_output.close()
            self.qu5_midi_output = None
        
        self.qu5_connected = False
        self.qu5_status_label.config(text="Qu-5 연결 안됨", foreground="red")
        self.log_message("Qu-5 믹서 연결 해제됨")
    
    def send_qu5_midi(self, midi_message):
        """Qu-5 믹서에 MIDI 메시지를 전송합니다."""
        if self.use_tcp_midi.get():
            # TCP/IP MIDI 전송
            if not self.qu5_connected or not self.qu5_socket:
                self.log_message("경고: Qu-5 믹서에 TCP/IP 연결되지 않음")
                return False
            
            try:
                # MIDI 메시지를 바이트로 변환하여 전송
                midi_bytes_list = midi_message.bytes()  # 리스트 반환
                midi_bytes = bytes(midi_bytes_list)     # 바이트 객체로 변환
                self.qu5_socket.send(midi_bytes)
                self.log_message(f"Qu-5 TCP/IP MIDI 전송 성공: {midi_message}")
                self.log_message(f"  - 바이트: {midi_bytes.hex().upper()}")
                return True
            except Exception as e:
                self.log_message(f"Qu-5 TCP/IP MIDI 전송 실패: {e}")
                return False
        else:
            # USB MIDI 전송
            if not self.qu5_midi_output:
                self.log_message("경고: Qu-5 USB MIDI 출력 포트가 설정되지 않음")
                return False
            
            try:
                self.qu5_midi_output.send(midi_message)
                self.log_message(f"Qu-5 USB MIDI 전송 성공: {midi_message}")
                return True
            except Exception as e:
                self.log_message(f"Qu-5 USB MIDI 전송 실패: {e}")
                return False
    
    def mute_channel_1(self):
        """1번 채널을 뮤트합니다 (NRPN 방식)."""
        try:
            midi_channel = int(self.qu5_midi_channel.get()) - 1  # MIDI 채널은 0-15
            
            self.log_message(f"🔇 1번 채널 뮤트 시도 - MIDI 채널: {midi_channel}")
            self.log_message("NRPN 뮤트 전송: 채널1 켜기")
            
            # NRPN 뮤트 시퀀스 전송
            success = self.send_nrpn_mute_sequence(midi_channel, mute=True)
            
            if success:
                self.log_message("✅ 1번 채널 뮤트됨")
        except Exception as e:
            self.log_message(f"1번 채널 뮤트 실패: {e}")
    
    def unmute_channel_1(self):
        """1번 채널의 뮤트를 해제합니다 (NRPN 방식)."""
        try:
            midi_channel = int(self.qu5_midi_channel.get()) - 1  # MIDI 채널은 0-15
            
            self.log_message(f"🔊 1번 채널 뮤트 해제 시도 - MIDI 채널: {midi_channel}")
            self.log_message("NRPN 뮤트 전송: 채널1 끄기")
            
            # NRPN 뮤트 해제 시퀀스 전송
            success = self.send_nrpn_mute_sequence(midi_channel, mute=False)
            
            if success:
                self.log_message("✅ 1번 채널 뮤트 해제됨")
        except Exception as e:
            self.log_message(f"1번 채널 뮤트 해제 실패: {e}")
    
    def send_nrpn_mute_sequence(self, midi_channel, mute=True):
        """NRPN 뮤트 시퀀스를 전송합니다."""
        try:
            # NRPN 뮤트 시퀀스:
            # CC 99 = 0 (MSB)
            # CC 98 = 0 (LSB) 
            # CC 6 = 0 (Data Entry MSB)
            # CC 38 = 1 (뮤트) 또는 0 (뮤트 해제)
            
            # CC 99 전송
            cc99_msg = mido.Message('control_change', channel=midi_channel, control=99, value=0)
            self.log_message(f"CC 전송: ch={midi_channel} ctl=99 val=0")
            if not self.send_qu5_midi(cc99_msg):
                return False
            
            # CC 98 전송
            cc98_msg = mido.Message('control_change', channel=midi_channel, control=98, value=0)
            self.log_message(f"CC 전송: ch={midi_channel} ctl=98 val=0")
            if not self.send_qu5_midi(cc98_msg):
                return False
            
            # CC 6 전송
            cc6_msg = mido.Message('control_change', channel=midi_channel, control=6, value=0)
            self.log_message(f"CC 전송: ch={midi_channel} ctl=6 val=0")
            if not self.send_qu5_midi(cc6_msg):
                return False
            
            # CC 38 전송 (뮤트 상태)
            mute_value = 1 if mute else 0
            cc38_msg = mido.Message('control_change', channel=midi_channel, control=38, value=mute_value)
            self.log_message(f"CC 전송: ch={midi_channel} ctl=38 val={mute_value}")
            if not self.send_qu5_midi(cc38_msg):
                return False
            
            return True
            
        except Exception as e:
            self.log_message(f"NRPN 뮤트 시퀀스 전송 실패: {e}")
            return False
    
    def test_network(self):
        """네트워크 연결을 테스트합니다."""
        self.log_message("=== 네트워크 연결 테스트 시작 ===")
        
        ip = self.qu5_ip.get()
        port = int(self.qu5_port.get())
        
        try:
            # Ping 테스트
            self.log_message(f"Ping 테스트: {ip}")
            ping_success = self.ping_host(ip)
            if ping_success:
                self.log_message("✅ Ping 테스트 성공")
            else:
                self.log_message("❌ Ping 테스트 실패")
            
            # TCP 포트 테스트
            self.log_message(f"TCP 포트 테스트: {ip}:{port}")
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.settimeout(3)
            result = test_sock.connect_ex((ip, port))
            test_sock.close()
            
            if result == 0:
                self.log_message("✅ TCP 포트 연결 가능")
            else:
                self.log_message("❌ TCP 포트 연결 실패")
                
        except Exception as e:
            self.log_message(f"네트워크 테스트 실패: {e}")
        
        self.log_message("=== 네트워크 연결 테스트 완료 ===")
    
    def test_midi(self):
        """MIDI 연결을 테스트합니다."""
        self.log_message("=== MIDI 테스트 시작 ===")
        
        if not self.qu5_connected:
            self.log_message("❌ Qu-5에 연결되지 않음")
            return
        
        # 1번 채널 뮤트 테스트
        self.log_message("1번 채널 뮤트 테스트...")
        self.mute_channel_1()
        time.sleep(1)
        
        self.log_message("1번 채널 뮤트 해제 테스트...")
        self.unmute_channel_1()
        
        self.log_message("=== MIDI 테스트 완료 ===")
    
    def ping_host(self, ip):
        """호스트에 ping을 보내서 연결 가능성을 테스트합니다."""
        try:
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", "1", "-w", "2000", ip]
            else:
                cmd = ["ping", "-c", "1", "-W", "2", ip]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
            return result.returncode == 0
            
        except Exception as e:
            self.log_message(f"Ping 테스트 예외: {e}")
            return False
    
    def start_midi(self):
        """MIDI 입력을 시작합니다."""
        if self.midi_running:
            return
        
        port_name = self.midi_input_port.get()
        if not port_name:
            messagebox.showwarning("경고", "MIDI 입력 포트를 선택하세요.")
            return
        
        try:
            self.midi_input = mido.open_input(port_name)
            self.midi_running = True
            self.midi_thread = threading.Thread(target=self.midi_listener, daemon=True)
            self.midi_thread.start()
            
            self.midi_status_label.config(text="MIDI 실행중", foreground="green")
            self.log_message(f"MIDI 입력 시작: {port_name}")
            
        except Exception as e:
            messagebox.showerror("MIDI 오류", f"MIDI 입력 시작 실패: {e}")
            self.log_message(f"MIDI 시작 실패: {e}")
    
    def stop_midi(self):
        """MIDI 입력을 중지합니다."""
        self.midi_running = False
        if self.midi_input:
            self.midi_input.close()
            self.midi_input = None
        
        self.midi_status_label.config(text="MIDI 중지됨", foreground="red")
        self.log_message("MIDI 입력 중지됨")
    
    def midi_listener(self):
        """MIDI 메시지를 수신하고 처리합니다."""
        while self.midi_running and self.midi_input:
            try:
                for msg in self.midi_input.iter_pending():
                    self.process_midi_message(msg)
                time.sleep(0.01)
            except Exception as e:
                self.log_message(f"MIDI 수신 오류: {e}")
                break
    
    def process_midi_message(self, msg):
        """MIDI 메시지를 처리합니다."""
        self.log_message(f"MIDI 수신: {msg}")
        
        # 여기에 MIDI 메시지 처리 로직을 추가할 수 있습니다
        # 예: 특정 MIDI Note를 받으면 Qu-5에 전달
    
    def log_message(self, message):
        """로그 메시지를 추가합니다."""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
    
    def clear_log(self):
        """로그를 지웁니다."""
        self.log_text.delete(1.0, tk.END)

def main():
    """메인 함수"""
    root = tk.Tk()
    app = Qu5MIDIController(root)
    
    # 창 닫기 이벤트 처리
    def on_closing():
        app.stop_midi()
        app.disconnect_qu5()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
