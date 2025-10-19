#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DM3 믹서용 MIDI-OSC 컨트롤러
MIDI 신호를 받아서 DM3 믹서에 OSC 신호를 전송합니다.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pythonosc import udp_client
import mido
import rtmidi
import threading
import time
import json
import socket
import subprocess
import platform

class DM3MIDIController:
    def __init__(self, root):
        self.root = root
        self.root.title("DM3 MIDI-OSC 컨트롤러")
        self.root.geometry("800x600")
        
        # DM3 믹서 OSC 클라이언트 설정
        self.dm3_client = None
        self.dm3_ip = tk.StringVar(value="192.168.4.2")  # DM3 믹서 IP
        self.dm3_port = tk.StringVar(value="49900")  # DM3 OSC 포트
        
        # MIDI 설정 (가상 MIDI 포트만 사용)
        # self.midi_input = None
        # self.midi_input_port = tk.StringVar()
        # self.midi_running = False
        # self.midi_thread = None
        
        # 가상 MIDI 포트 설정
        self.virtual_midi_out = None
        self.virtual_midi_in = None
        self.virtual_port_name = "DM3 Controller"
        self.virtual_port_active = False
        
        # 로그 창
        self.log_text = None
        
        # GUI 구성
        self.setup_gui()
        
        # 연결 상태
        self.dm3_connected = False
        self.connection_monitor_active = False
        
        # 가상 MIDI 포트 생성 (GUI 초기화 후에 실행)
        self.root.after(100, self.delayed_initialization)
    
    def setup_gui(self):
        """GUI를 구성합니다."""
        
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # DM3 믹서 설정 프레임
        dm3_frame = ttk.LabelFrame(main_frame, text="DM3 믹서 설정", padding="5")
        dm3_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(dm3_frame, text="IP 주소:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(dm3_frame, textvariable=self.dm3_ip, width=15).grid(row=0, column=1, padx=(5, 10))
        
        ttk.Label(dm3_frame, text="포트:").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(dm3_frame, textvariable=self.dm3_port, width=10).grid(row=0, column=3, padx=(5, 10))
        
        ttk.Button(dm3_frame, text="DM3 연결", command=self.connect_dm3).grid(row=0, column=4, padx=(5, 0))
        ttk.Button(dm3_frame, text="DM3 연결 해제", command=self.disconnect_dm3).grid(row=0, column=5, padx=(5, 0))
        
        # DM3 상태 표시
        self.dm3_status_label = ttk.Label(dm3_frame, text="DM3 연결 안됨", foreground="red")
        self.dm3_status_label.grid(row=0, column=6, padx=(10, 0))
        
        # 가상 MIDI 포트 설정 프레임 (제거됨)
        # midi_frame = ttk.LabelFrame(main_frame, text="가상 MIDI 포트 설정", padding="5")
        # midi_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        # 
        # ttk.Label(midi_frame, text="가상 MIDI 포트:").grid(row=0, column=0, sticky=tk.W)
        # self.virtual_port_status_label = ttk.Label(midi_frame, text="가상 포트 비활성", foreground="red")
        # self.virtual_port_status_label.grid(row=0, column=1, padx=(5, 10))
        # 
        # ttk.Button(midi_frame, text="가상 포트 생성", 
        #           command=self.create_virtual_midi_port).grid(row=0, column=2, padx=(5, 0))
        # ttk.Button(midi_frame, text="가상 포트 삭제", 
        #           command=self.delete_virtual_midi_port).grid(row=0, column=3, padx=(5, 0))
        
        # DM3 컨트롤 패널 (주석처리)
        # control_frame = ttk.LabelFrame(main_frame, text="DM3 믹서 컨트롤", padding="5")
        # control_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        # 
        # # 채널 뮤트 버튼들
        # mute_frame = ttk.Frame(control_frame)
        # mute_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        # 
        # ttk.Label(mute_frame, text="채널 뮤트:").grid(row=0, column=0, sticky=tk.W)
        # 
        # # 테스트 버튼들
        # ttk.Button(mute_frame, text="네트워크 테스트", 
        #           command=self.test_network).grid(row=1, column=0, padx=2, pady=2)
        # ttk.Button(mute_frame, text="DM3 테스트", 
        #           command=self.test_dm3_connection).grid(row=1, column=1, padx=2, pady=2)
        # 
        # # 간단한 UDK1 테스트 버튼
        # ttk.Button(mute_frame, text="🔘 UDK1 테스트", 
        #           command=self.simple_udk1_test).grid(row=1, column=2, padx=2, pady=2)
        # 
        # # MIDI 시뮬레이션 테스트 버튼
        # ttk.Button(mute_frame, text="🎵 MIDI 테스트", 
        #           command=self.test_midi_simulation).grid(row=1, column=3, padx=2, pady=2)
        # 
        # # 1-16번 채널 뮤트 버튼들
        # for i in range(1, 17):
        #     row = (i - 1) // 8 + 2  # 테스트 버튼 때문에 +2
        #     col = (i - 1) % 8
        #     ttk.Button(mute_frame, text=f"Ch{i} 뮤트", 
        #               command=lambda ch=i: self.mute_channel(ch)).grid(row=row, column=col, padx=2, pady=2)
        # 
        # # 페이더 레벨 컨트롤
        # fader_frame = ttk.Frame(control_frame)
        # fader_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        # 
        # ttk.Label(fader_frame, text="1번 채널 페이더:").grid(row=0, column=0, sticky=tk.W)
        # self.fader_var = tk.DoubleVar(value=0.0)
        # self.fader_scale = ttk.Scale(fader_frame, from_=-60.0, to=10.0, variable=self.fader_var, 
        #                            orient=tk.HORIZONTAL, length=300, command=self.on_fader_change)
        # self.fader_scale.grid(row=0, column=1, padx=(5, 5))
        # 
        # self.fader_label = ttk.Label(fader_frame, text="0.0 dB")
        # self.fader_label.grid(row=0, column=2)
        # 
        # # 씬 컨트롤
        # scene_frame = ttk.Frame(control_frame)
        # scene_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        # 
        # ttk.Label(scene_frame, text="씬 불러오기:").grid(row=0, column=0, sticky=tk.W)
        # 
        # # 씬 선택 콤보박스
        # self.scene_var = tk.StringVar(value="scene_a")
        # self.scene_combo = ttk.Combobox(scene_frame, textvariable=self.scene_var, width=10, state="readonly")
        # self.scene_combo['values'] = ("scene_a", "scene_b", "scene_c", "scene_d", "scene_e", "scene_f")
        # self.scene_combo.grid(row=0, column=1, padx=(5, 5))
        # 
        # # 씬 번호 입력
        # ttk.Label(scene_frame, text="번호:").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        # self.scene_num_var = tk.StringVar(value="0")
        # scene_num_entry = ttk.Entry(scene_frame, textvariable=self.scene_num_var, width=5)
        # scene_num_entry.grid(row=0, column=3, padx=(5, 5))
        # 
        # # 씬 불러오기 버튼
        # ttk.Button(scene_frame, text="씬 불러오기", 
        #           command=self.recall_scene).grid(row=0, column=4, padx=(5, 5))
        # 
        # # 빠른 씬 버튼들 (A씬 0-7번)
        # quick_scene_frame = ttk.Frame(scene_frame)
        # quick_scene_frame.grid(row=1, column=0, columnspan=5, sticky=(tk.W, tk.E), pady=(5, 0))
        # 
        # ttk.Label(quick_scene_frame, text="A씬:").grid(row=0, column=0, sticky=tk.W)
        # for i in range(0, 8):
        #     ttk.Button(quick_scene_frame, text=f"A{i:02d}", 
        #               command=lambda num=i: self.quick_recall_scene("scene_a", num)).grid(row=0, column=i+1, padx=1)
        # 
        # # 빠른 씬 버튼들 (B씬 0-7번)
        # ttk.Label(quick_scene_frame, text="B씬:").grid(row=1, column=0, sticky=tk.W)
        # for i in range(0, 8):
        #     ttk.Button(quick_scene_frame, text=f"B{i:02d}", 
        #               command=lambda num=i: self.quick_recall_scene("scene_b", num)).grid(row=1, column=i+1, padx=1)
        
        # MIDI 매핑 정보 (주석처리)
        # mapping_frame = ttk.LabelFrame(main_frame, text="MIDI 매핑 정보", padding="5")
        # mapping_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        # 
        # mapping_text = """
        # MIDI 매핑:
        # User Defined Keys (Channel 0):
        # - MIDI Note 1-16 (Channel 0): User Defined Key 1-16 트리거
        # 
        # 채널 뮤트 (Channel 1+):
        # - MIDI Note 36-51 (C2-G3): 1-16번 채널 뮤트 토글
        # - MIDI CC 1 (Modulation): 1번 채널 페이더 레벨 (0-127 → -60dB ~ +10dB)
        # 
        # 씬 컨트롤:
        # - 씬 선택: scene_a, scene_b, scene_c, scene_d, scene_e, scene_f
        # - 씬 번호: 0-99
        # - 빠른 씬: A00-A07, B00-B07 버튼으로 즉시 실행
        # 
        # 프로프리젠터 예시:
        # - note_on channel=0 note=1 velocity=1 → User Defined Key 1 트리거
        # - note_on channel=1 note=36 velocity=1 → 1번 채널 뮤트
        # """
        # 
        # mapping_label = ttk.Label(mapping_frame, text=mapping_text.strip(), justify=tk.LEFT)
        # mapping_label.grid(row=0, column=0, sticky=tk.W)
        
        # 로그 창
        log_frame = ttk.LabelFrame(main_frame, text="로그", padding="5")
        log_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 로그 지우기 버튼
        ttk.Button(log_frame, text="로그 지우기", command=self.clear_log).grid(row=1, column=0, pady=(5, 0))
        
        # 그리드 가중치 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
    
    def delayed_initialization(self):
        """GUI 초기화 후 지연된 초기화 작업을 수행합니다."""
        try:
            # 가상 MIDI 포트 생성
            self.create_virtual_midi_port()
        except Exception as e:
            self.log_message(f"초기화 중 오류 발생: {e}")
    
    # def update_midi_ports(self):
    #     """MIDI 입력 포트 목록을 업데이트합니다."""
    #     try:
    #         ports = mido.get_input_names()
    #         self.midi_port_combo['values'] = ports
    #         if ports and not self.midi_input_port.get():
    #             self.midi_input_port.set(ports[0])
    #         self.log_message(f"MIDI 포트 목록 업데이트: {len(ports)}개 포트 발견")
    #     except Exception as e:
    #         self.log_message(f"MIDI 포트 목록 업데이트 실패: {e}")
    
    def create_virtual_midi_port(self):
        """가상 MIDI 포트를 생성합니다."""
        try:
            # 기존 포트가 있으면 먼저 삭제
            if self.virtual_port_active:
                self.delete_virtual_midi_port()
            
            # rtmidi 초기화를 별도 스레드에서 수행
            def create_ports():
                try:
                    # 가상 MIDI 출력 포트 생성 (프로프리젠터가 연결할 포트)
                    self.virtual_midi_out = rtmidi.MidiOut()
                    self.virtual_midi_out.open_virtual_port(f"{self.virtual_port_name} Out")
                    
                    # 가상 MIDI 입력 포트 생성 (프로프리젠터에서 받을 포트)
                    self.virtual_midi_in = rtmidi.MidiIn()
                    self.virtual_midi_in.open_virtual_port(f"{self.virtual_port_name} In")
                    
                    # 콜백 함수 설정
                    self.virtual_midi_in.set_callback(self.virtual_midi_callback)
                    
                    # GUI 업데이트는 메인 스레드에서
                    self.root.after(0, self.on_virtual_port_created)
                    
                except Exception as e:
                    self.root.after(0, lambda: self.on_virtual_port_error(e))
            
            # 별도 스레드에서 포트 생성
            threading.Thread(target=create_ports, daemon=True).start()
            
        except Exception as e:
            self.log_message(f"❌ 가상 MIDI 포트 생성 실패: {e}")
            self.virtual_port_active = False
    
    def on_virtual_port_created(self):
        """가상 MIDI 포트 생성 성공 시 GUI 업데이트"""
        self.virtual_port_active = True
        self.log_message(f"✅ 가상 MIDI 포트 생성 성공: '{self.virtual_port_name}'")
        self.log_message(f"   - 출력 포트: '{self.virtual_port_name} Out' (프로프리젠터가 연결)")
        self.log_message(f"   - 입력 포트: '{self.virtual_port_name} In' (프로프리젠터에서 수신)")
        self.log_message("프로프리젠터에서 'DM3 Controller Out' 포트를 선택하세요!")
    
    def on_virtual_port_error(self, error):
        """가상 MIDI 포트 생성 실패 시 GUI 업데이트"""
        self.log_message(f"❌ 가상 MIDI 포트 생성 실패: {error}")
        self.virtual_port_active = False
    
    def delete_virtual_midi_port(self):
        """가상 MIDI 포트를 삭제합니다."""
        try:
            # rtmidi 정리를 별도 스레드에서 수행
            def cleanup_ports():
                try:
                    if self.virtual_midi_out:
                        self.virtual_midi_out.close_port()
                        self.virtual_midi_out = None
                    
                    if self.virtual_midi_in:
                        self.virtual_midi_in.close_port()
                        self.virtual_midi_in = None
                    
                    # GUI 업데이트는 메인 스레드에서
                    self.root.after(0, self.on_virtual_port_deleted)
                    
                except Exception as e:
                    self.root.after(0, lambda: self.log_message(f"가상 MIDI 포트 삭제 실패: {e}"))
            
            # 별도 스레드에서 포트 삭제
            threading.Thread(target=cleanup_ports, daemon=True).start()
            
        except Exception as e:
            self.log_message(f"가상 MIDI 포트 삭제 실패: {e}")
    
    def on_virtual_port_deleted(self):
        """가상 MIDI 포트 삭제 완료 시 GUI 업데이트"""
        self.virtual_port_active = False
        self.log_message("가상 MIDI 포트 삭제됨")
    
    def virtual_midi_callback(self, message, data):
        """가상 MIDI 포트에서 메시지를 받았을 때 호출되는 콜백 함수"""
        try:
            # rtmidi 메시지를 mido 메시지로 변환
            msg = mido.Message.from_bytes(message[0])
            
            # GUI 업데이트는 메인 스레드에서 수행
            self.root.after(0, lambda: self.process_midi_message(msg))
            
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"가상 MIDI 콜백 오류: {e}"))
    
    def connect_dm3(self):
        """DM3 믹서에 연결합니다."""
        try:
            ip = self.dm3_ip.get()
            port = int(self.dm3_port.get())
            
            # 1. 네트워크 연결 테스트
            self.log_message(f"🔍 DM3 연결 테스트 시작: {ip}:{port}")
            
            # 2. 소켓 연결 테스트 (UDP)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)  # 3초 타임아웃
            
            # 3. 실제 연결 가능한지 테스트
            try:
                # 호스트 해석 테스트
                socket.gethostbyname(ip)
                self.log_message(f"✅ 호스트 해석 성공: {ip}")
                
                # Ping 테스트 (필수)
                self.log_message(f"Ping 테스트 시작: {ip}")
                ping_success = self.ping_host(ip, debug=True)
                if ping_success:
                    self.log_message(f"✅ Ping 테스트 성공: {ip}")
                else:
                    sock.close()
                    raise Exception(f"Ping 테스트 실패: {ip} - 네트워크 연결을 확인하세요")
                    
            except socket.gaierror as e:
                sock.close()
                raise Exception(f"호스트를 찾을 수 없습니다: {ip}")
            
            # 4. OSC 클라이언트 생성
            self.dm3_client = udp_client.SimpleUDPClient(ip, port)
            
            # 5. 추가 연결 확인 (소켓 바인딩 테스트)
            try:
                # 로컬 소켓 바인딩 테스트
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                test_sock.settimeout(1)
                test_sock.bind(('', 0))  # 임시 포트에 바인딩
                test_sock.close()
                self.log_message("✅ 네트워크 소켓 테스트 성공")
                
                # OSC 테스트 메시지 전송 (UDP는 연결 없이도 전송 가능)
                try:
                    self.dm3_client.send_message("/test_connection", "ping")
                    self.log_message("✅ OSC 테스트 메시지 전송 완료")
                except Exception as osc_error:
                    self.log_message(f"⚠️ OSC 테스트 메시지 전송 실패: {osc_error}")
                    self.log_message("OSC 전송 실패했지만 연결은 계속 진행합니다")
                
            except Exception as e:
                sock.close()
                raise Exception(f"네트워크 연결 테스트 실패: {e}")
            
            sock.close()
            
            # 6. 모든 테스트 통과 - 연결 성공
            self.dm3_connected = True
            self.dm3_status_label.config(text="DM3 연결됨", foreground="green")
            self.log_message(f"🎉 DM3 믹서 연결 성공: {ip}:{port}")
            self.log_message("모든 연결 테스트를 통과했습니다!")
            
            # 7. 연결 상태 모니터링 시작
            self.start_connection_monitor()
            
        except Exception as e:
            # 연결 실패 시 상태 초기화
            self.dm3_client = None
            self.dm3_connected = False
            self.dm3_status_label.config(text="DM3 연결 안됨", foreground="red")
            messagebox.showerror("연결 오류", f"DM3 믹서 연결 실패: {e}")
            self.log_message(f"❌ DM3 연결 실패: {e}")
    
    def ping_host(self, ip, debug=False):
        """호스트에 ping을 보내서 연결 가능성을 테스트합니다."""
        try:
            # 운영체제에 따라 ping 명령어 다르게 처리
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", "1", "-w", "2000", ip]  # 2초 타임아웃
            else:
                cmd = ["ping", "-c", "1", "-W", "2", ip]  # 2초 타임아웃
            
            # ping 실행 (전체 타임아웃 4초)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
            
            # 디버깅을 위한 상세 로그 (디버그 모드일 때만)
            if debug and result.returncode != 0:
                # 실패한 경우에만 상세 로그 표시
                self.log_message(f"Ping 명령어: {' '.join(cmd)}")
                self.log_message(f"Ping 리턴 코드: {result.returncode}")
                self.log_message(f"Ping 출력: {result.stdout.strip()}")
                if result.stderr:
                    self.log_message(f"Ping 에러: {result.stderr.strip()}")
            
            # ping 결과를 더 정확하게 분석
            success = result.returncode == 0
            
            # 출력 메시지에서 추가 확인 (macOS/Linux)
            if platform.system().lower() != "windows" and success:
                # 다양한 ping 성공 패턴 확인
                ping_success_patterns = [
                    "1 received",
                    "1 packets received", 
                    "bytes from",
                    "time=",
                    "time<1ms"
                ]
                
                ping_success = any(pattern in result.stdout for pattern in ping_success_patterns)
                if not ping_success:
                    success = False
            
            return success
            
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            self.log_message(f"Ping 테스트 예외 발생: {e}")
            return False
    
    def start_connection_monitor(self):
        """연결 상태 모니터링을 시작합니다."""
        if not self.connection_monitor_active:
            self.connection_monitor_active = True
            monitor_thread = threading.Thread(target=self.connection_monitor, daemon=True)
            monitor_thread.start()
            self.log_message("연결 상태 모니터링 시작")
    
    def stop_connection_monitor(self):
        """연결 상태 모니터링을 중지합니다."""
        self.connection_monitor_active = False
        self.log_message("연결 상태 모니터링 중지")
    
    def connection_monitor(self):
        """연결 상태를 주기적으로 모니터링합니다."""
        consecutive_failures = 0
        max_failures = 3  # 3번 연속 실패하면 연결 해제
        last_status = "connected"  # 마지막 상태 추적
        
        while self.connection_monitor_active and self.dm3_connected:
            try:
                time.sleep(3)  # 3초마다 체크 (더 빠른 감지)
                
                if not self.dm3_connected:
                    break
                
                # 연결 테스트
                ip = self.dm3_ip.get()
                ping_success = self.ping_host(ip)
                
                if ping_success:
                    # 연결 성공
                    consecutive_failures = 0
                    
                    # 상태가 바뀔 때만 로그 출력
                    if last_status != "connected":
                        self.log_message("✅ 연결 상태 복구: 정상")
                        last_status = "connected"
                    
                    self.dm3_status_label.config(text="DM3 연결됨", foreground="green")
                else:
                    # 연결 실패
                    consecutive_failures += 1
                    
                    # 상태가 바뀔 때만 로그 출력
                    if last_status != "unstable" and last_status != "failed":
                        self.log_message(f"⚠️ 연결 상태 불안정 감지 ({consecutive_failures}/{max_failures})")
                        last_status = "unstable"
                    else:
                        self.log_message(f"❌ 연결 실패 ({consecutive_failures}/{max_failures}): ping 타임아웃")
                    
                    if consecutive_failures >= max_failures:
                        # 연속으로 3번 실패하면 연결 해제
                        self.log_message("🚨 연결이 완전히 끊어졌습니다. 연결을 해제합니다.")
                        self.dm3_status_label.config(text="DM3 연결 실패", foreground="red")
                        self.dm3_connected = False
                        self.dm3_client = None
                        break
                    else:
                        # 아직 기회가 있으면 불안정 상태로 표시
                        self.dm3_status_label.config(text="DM3 연결 불안정", foreground="orange")
                        
            except Exception as e:
                consecutive_failures += 1
                
                # 예외 발생 시에만 로그 출력 (연속 발생 방지)
                if last_status != "error":
                    self.log_message(f"연결 모니터링 오류 ({consecutive_failures}/{max_failures}): {e}")
                    last_status = "error"
                
                if consecutive_failures >= max_failures:
                    self.log_message("🚨 연결 모니터링 오류로 연결을 해제합니다.")
                    self.dm3_status_label.config(text="DM3 연결 실패", foreground="red")
                    self.dm3_connected = False
                    self.dm3_client = None
                    break
                else:
                    self.dm3_status_label.config(text="DM3 연결 불안정", foreground="orange")
    
    def disconnect_dm3(self):
        """DM3 믹서 연결을 해제합니다."""
        # 연결 상태 모니터링 중지
        self.stop_connection_monitor()
        
        # 연결 해제
        self.dm3_client = None
        self.dm3_connected = False
        self.dm3_status_label.config(text="DM3 연결 안됨", foreground="red")
        self.log_message("DM3 믹서 연결 해제됨")
    
    def send_dm3_osc(self, address, *args):
        """DM3 믹서에 OSC 메시지를 전송합니다."""
        if not self.dm3_connected or not self.dm3_client:
            self.log_message("⚠️ 경고: DM3 믹서에 연결되지 않음")
            return
        
        try:
            self.dm3_client.send_message(address, args)
            self.log_message(f"📡 DM3 전송 성공: {address} -> {args}")
            self.log_message(f"   📍 DM3 IP: {self.dm3_ip.get()}:{self.dm3_port.get()}")
        except Exception as e:
            self.log_message(f"❌ DM3 전송 실패: {e}")
            self.log_message(f"   📍 주소: {address}")
            self.log_message(f"   📍 인수: {args}")
            self.log_message(f"   📍 DM3 IP: {self.dm3_ip.get()}:{self.dm3_port.get()}")
    
    def test_network(self):
        """네트워크 연결을 테스트합니다."""
        self.log_message("=== 네트워크 연결 테스트 시작 ===")
        
        ip = self.dm3_ip.get()
        port = int(self.dm3_port.get())
        
        try:
            # 1. 소켓 연결 테스트
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)  # 3초 타임아웃
            
            # UDP 소켓은 실제로 연결하지 않고 바인딩만 테스트
            self.log_message(f"DM3 IP 주소 확인: {ip}")
            self.log_message(f"DM3 포트 확인: {port}")
            
            # 2. 로컬 네트워크 인터페이스 확인
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            self.log_message(f"로컬 IP: {local_ip}")
            
            sock.close()
            self.log_message("네트워크 연결 테스트 성공")
            
        except Exception as e:
            self.log_message(f"네트워크 연결 테스트 실패: {e}")
        
        self.log_message("=== 네트워크 연결 테스트 완료 ===")
    
    def test_dm3_connection(self):
        """DM3 연결 테스트를 수행합니다."""
        self.log_message("=== DM3 연결 테스트 시작 ===")
        
        # 1. 간단한 OSC 메시지 전송 테스트
        try:
            test_address = "/test"
            self.send_dm3_osc(test_address, "Hello DM3")
            self.log_message("테스트 메시지 전송 완료")
        except Exception as e:
            self.log_message(f"테스트 메시지 전송 실패: {e}")
        
        # 2. 1번 채널 뮤트 테스트
        try:
            self.log_message("1번 채널 뮤트 테스트...")
            self.mute_channel(1)
            time.sleep(0.5)
            self.log_message("1번 채널 뮤트 해제 테스트...")
            self.unmute_channel(1)
        except Exception as e:
            self.log_message(f"채널 뮤트 테스트 실패: {e}")
        
        self.log_message("=== DM3 연결 테스트 완료 ===")
    
    def recall_scene(self):
        """선택된 씬을 불러옵니다."""
        scene_name = self.scene_var.get()
        scene_num = self.scene_num_var.get()
        
        try:
            scene_num_int = int(scene_num)
            if scene_num_int < 0 or scene_num_int > 99:
                messagebox.showerror("오류", "씬 번호는 0-99 사이여야 합니다.")
                return
            
            # DM3 OSC 주소 형식: /yosc:req/ssrecall_ex "scene_a" <번호>
            address = "/yosc:req/ssrecall_ex"
            self.send_dm3_osc(address, scene_name, scene_num_int)
            self.log_message(f"🎬 씬 불러오기: {scene_name} {scene_num_int:02d}")
            
        except ValueError:
            messagebox.showerror("오류", "씬 번호는 숫자여야 합니다.")
    
    def recall_scene_by_number(self, scene_number):
        """씬 번호로 씬을 불러옵니다 (프로프리젠터용)."""
        try:
            self.log_message(f"🔍 씬 리콜 시작: {scene_number}번 씬")
            
            # 씬 번호를 scene_a 형식으로 변환 (1번 씬 = scene_a 0번)
            scene_name = "scene_a"
            scene_index = scene_number - 1  # 1번 씬 -> 0번 인덱스
            
            self.log_message(f"🔍 변환된 값: scene_name={scene_name}, scene_index={scene_index}")
            
            if scene_index < 0 or scene_index > 99:
                self.log_message(f"⚠️ 잘못된 씬 번호: {scene_number} (1-100 범위)")
                return
            
            # DM3 OSC 주소 형식: /yosc:req/ssrecall_ex "scene_a" <번호>
            address = "/yosc:req/ssrecall_ex"
            self.log_message(f"🔍 OSC 전송 준비: address={address}, args=({scene_name}, {scene_index})")
            
            self.send_dm3_osc(address, scene_name, scene_index)
            self.log_message(f"🎬 프로프리젠터 씬 리콜 완료: {scene_number}번 씬 (scene_a {scene_index:02d})")
            
        except Exception as e:
            self.log_message(f"❌ 씬 리콜 실패: {e}")
            import traceback
            self.log_message(f"❌ 상세 오류: {traceback.format_exc()}")
    
    def quick_recall_scene(self, scene_name, scene_num):
        """빠른 씬 불러오기 (빠른 버튼용)"""
        # DM3 OSC 주소 형식: /yosc:req/ssrecall_ex "scene_a" <번호>
        address = "/yosc:req/ssrecall_ex"
        self.send_dm3_osc(address, scene_name, scene_num)
        self.log_message(f"🎬 빠른 씬 불러오기: {scene_name} {scene_num:02d}")
    
    def mute_channel(self, channel_num):
        """특정 채널을 뮤트합니다."""
        try:
            self.log_message(f"🔍 채널 뮤트 시작: {channel_num}번 채널")
            
            # DM3 OSC 주소 형식: /yosc:req/set/MIXER:Current/InCh/Fader/On/<channel>/1 0
            address = f"/yosc:req/set/MIXER:Current/InCh/Fader/On/{channel_num}/1"
            self.log_message(f"🔍 OSC 전송 준비: address={address}, value=0")
            
            self.send_dm3_osc(address, 0)  # 0 = OFF (뮤트)
            self.log_message(f"🔇 {channel_num}번 채널 뮤트 완료 - 주소: {address}, 값: 0")
            
        except Exception as e:
            self.log_message(f"❌ 채널 뮤트 실패: {e}")
            import traceback
            self.log_message(f"❌ 상세 오류: {traceback.format_exc()}")
    
    def unmute_channel(self, channel_num):
        """특정 채널의 뮤트를 해제합니다."""
        try:
            self.log_message(f"🔍 채널 뮤트 해제 시작: {channel_num}번 채널")
            
            # DM3 OSC 주소 형식: /yosc:req/set/MIXER:Current/InCh/Fader/On/<channel>/1 1
            address = f"/yosc:req/set/MIXER:Current/InCh/Fader/On/{channel_num}/1"
            self.log_message(f"🔍 OSC 전송 준비: address={address}, value=1")
            
            self.send_dm3_osc(address, 1)  # 1 = ON (뮤트 해제)
            self.log_message(f"🔊 {channel_num}번 채널 뮤트 해제 완료 - 주소: {address}, 값: 1")
            
        except Exception as e:
            self.log_message(f"❌ 채널 뮤트 해제 실패: {e}")
            import traceback
            self.log_message(f"❌ 상세 오류: {traceback.format_exc()}")
    
    def set_channel_level(self, channel_num, level_db):
        """채널 페이더 레벨을 설정합니다."""
        # DM3 OSC 주소 형식: /yosc:req/set/MIXER:Current/InCh/Fader/Level/<channel>/1 <value>
        # level_db를 DM3 값으로 변환 (-60dB ~ +10dB → -32768 ~ 1000)
        if level_db <= -60:
            dm3_value = -32768
        elif level_db >= 10:
            dm3_value = 1000
        else:
            # 선형 변환: -60dB ~ +10dB → -32768 ~ 1000
            dm3_value = int(-32768 + (level_db + 60) * (1000 + 32768) / 70)
        
        address = f"/yosc:req/set/MIXER:Current/InCh/Fader/Level/{channel_num}/1"
        self.send_dm3_osc(address, dm3_value)
        self.log_message(f"🎚️ {channel_num}번 채널 레벨: {level_db:.1f}dB (DM3값: {dm3_value})")
    
    def trigger_user_defined_key(self, key_number):
        """User Defined Key를 트리거합니다."""
        # DM3 OSC 주소 형식: /yosc:req/trigger/UserDefinedKey/<key_number>
        address = f"/yosc:req/trigger/UserDefinedKey/{key_number}"
        self.send_dm3_osc(address)
        self.log_message(f"🔘 User Defined Key {key_number} 트리거됨 - 주소: {address}")
    
    def simple_udk1_test(self):
        """간단한 UDK1 테스트 - 모든 가능한 OSC 형식을 순차적으로 테스트"""
        self.log_message("=== UDK1 간단 테스트 시작 ===")
        
        # DM3 연결 확인
        if not self.dm3_connected:
            self.log_message("❌ DM3에 연결되지 않음. 먼저 DM3를 연결하세요.")
            return
        
        # 다양한 OSC 형식들을 순차적으로 테스트
        test_commands = [
            ("표준 형식", "/yosc:req/trigger/UserDefinedKey/1"),
            ("간단 형식", "/yosc:req/UserDefinedKey/1"),
            ("UDK 형식", "/yosc:req/trigger/UDK/1"),
            ("UDK 간단", "/yosc:req/UDK/1"),
            ("UserKey 형식", "/yosc:req/trigger/UserKey/1"),
            ("UserKey 간단", "/yosc:req/UserKey/1"),
            ("다른 형식1", "/yosc:req/UserDefinedKey/1/trigger"),
            ("다른 형식2", "/yosc:req/UDK/1/trigger"),
            ("다른 형식3", "/yosc:req/UserKey/1/trigger"),
            ("다른 형식4", "/yosc:req/trigger/UserDefinedKey/1/1")
        ]
        
        self.log_message(f"총 {len(test_commands)}가지 형식을 테스트합니다...")
        self.log_message("DM3에서 User Defined Key 1번이 작동하는지 확인하세요!")
        
        for i, (name, address) in enumerate(test_commands, 1):
            try:
                self.log_message(f"[{i}/{len(test_commands)}] {name}: {address}")
                self.send_dm3_osc(address)
                time.sleep(0.5)  # 0.5초 간격으로 테스트
            except Exception as e:
                self.log_message(f"❌ {name} 테스트 실패: {e}")
        
        self.log_message("=== UDK1 테스트 완료 ===")
        self.log_message("💡 DM3에서 어떤 형식이 작동했는지 확인하고 알려주세요!")
    
    def test_midi_simulation(self):
        """MIDI 신호 시뮬레이션 테스트"""
        self.log_message("=== MIDI 시뮬레이션 테스트 시작 ===")
        
        # DM3 연결 확인
        if not self.dm3_connected:
            self.log_message("❌ DM3에 연결되지 않음. 먼저 DM3를 연결하세요.")
            return
        
        # 테스트할 MIDI 메시지들
        test_messages = [
            # 씬 리콜 테스트 (Channel 1)
            ("note_on", 1, 0, 1, "1번 씬 리콜"),
            ("note_on", 1, 1, 1, "2번 씬 리콜"),
            
            # 채널 뮤트 테스트 (Channel 2) - note_on = 뮤트, note_off = 뮤트 해제
            ("note_on", 2, 0, 1, "1번 채널 뮤트"),
            ("note_off", 2, 0, 64, "1번 채널 뮤트 해제"),
            ("note_on", 2, 1, 1, "2번 채널 뮤트"),
            ("note_off", 2, 1, 64, "2번 채널 뮤트 해제"),
        ]
        
        self.log_message(f"총 {len(test_messages)}개의 MIDI 메시지를 시뮬레이션합니다...")
        
        for i, (msg_type, channel, note, velocity, description) in enumerate(test_messages, 1):
            try:
                self.log_message(f"[{i}/{len(test_messages)}] {description}")
                
                # mido 메시지 생성
                if msg_type == "note_on":
                    msg = mido.Message('note_on', channel=channel, note=note, velocity=velocity)
                elif msg_type == "note_off":
                    msg = mido.Message('note_off', channel=channel, note=note, velocity=velocity)
                else:
                    continue
                
                # MIDI 메시지 처리
                self.process_midi_message(msg)
                time.sleep(1)  # 1초 간격으로 테스트
                
            except Exception as e:
                self.log_message(f"❌ {description} 테스트 실패: {e}")
        
        self.log_message("=== MIDI 시뮬레이션 테스트 완료 ===")
        self.log_message("💡 로그를 확인하여 각 단계가 정상적으로 처리되었는지 확인하세요!")
    
    def on_fader_change(self, value):
        """페이더 슬라이더 값이 변경될 때 호출됩니다."""
        level_db = float(value)
        self.fader_label.config(text=f"{level_db:.1f} dB")
        
        # 실시간으로 1번 채널 레벨 설정
        if self.dm3_connected:
            self.set_channel_level(1, level_db)
    
    # def start_midi(self):
    #     """MIDI 입력을 시작합니다."""
    #     if self.midi_running:
    #         return
    #     
    #     port_name = self.midi_input_port.get()
    #     if not port_name:
    #         messagebox.showwarning("경고", "MIDI 입력 포트를 선택하세요.")
    #         return
    #     
    #     try:
    #         self.midi_input = mido.open_input(port_name)
    #         self.midi_running = True
    #         self.midi_thread = threading.Thread(target=self.midi_listener, daemon=True)
    #         self.midi_thread.start()
    #         
    #         self.midi_status_label.config(text="MIDI 실행중", foreground="green")
    #         self.log_message(f"MIDI 입력 시작: {port_name}")
    #         
    #     except Exception as e:
    #         messagebox.showerror("MIDI 오류", f"MIDI 입력 시작 실패: {e}")
    #         self.log_message(f"MIDI 시작 실패: {e}")
    # 
    # def stop_midi(self):
    #     """MIDI 입력을 중지합니다."""
    #     self.midi_running = False
    #     if self.midi_input:
    #         self.midi_input.close()
    #         self.midi_input = None
    #     
    #     self.midi_status_label.config(text="MIDI 중지됨", foreground="red")
    #     self.log_message("MIDI 입력 중지됨")
    
    def cleanup_virtual_ports(self):
        """가상 MIDI 포트를 정리합니다."""
        try:
            if self.virtual_port_active:
                # 동기적으로 포트 정리 (프로그램 종료 시)
                if self.virtual_midi_out:
                    try:
                        self.virtual_midi_out.close_port()
                    except:
                        pass
                    self.virtual_midi_out = None
                
                if self.virtual_midi_in:
                    try:
                        self.virtual_midi_in.close_port()
                    except:
                        pass
                    self.virtual_midi_in = None
                
                self.virtual_port_active = False
                self.log_message("가상 MIDI 포트 정리 완료")
        except Exception as e:
            self.log_message(f"가상 MIDI 포트 정리 중 오류: {e}")
    
    # def midi_listener(self):
    #     """MIDI 메시지를 수신하고 처리합니다."""
    #     while self.midi_running and self.midi_input:
    #         try:
    #             for msg in self.midi_input.iter_pending():
    #                 self.process_midi_message(msg)
    #             time.sleep(0.01)  # CPU 사용량 조절
    #         except Exception as e:
    #             self.log_message(f"MIDI 수신 오류: {e}")
    #             break
    
    def process_midi_message(self, msg):
        """프로프리젠터에서 받은 MIDI 메시지를 처리합니다."""
        self.log_message(f"🎵 MIDI 수신: {msg}")
        
        # DM3 연결 상태 확인
        if not self.dm3_connected:
            self.log_message("⚠️ DM3가 연결되지 않음 - MIDI 신호를 처리할 수 없습니다")
            return
        
        # 프로프리젠터 규칙에 따른 처리
        if msg.type == 'note_on' and msg.velocity > 0:
            # 씬 리콜 (Channel 1)
            if msg.channel == 1:
                scene_number = msg.note + 1  # note=0 -> 1번 씬, note=1 -> 2번 씬
                self.log_message(f"🎬 씬 리콜 요청: {scene_number}번 씬 (note={msg.note})")
                self.recall_scene_by_number(scene_number)
            
            # 채널 뮤트 (Channel 2) - note_on = 뮤트
            elif msg.channel == 2:
                channel_number = msg.note + 1  # note=0 -> 1번 채널, note=1 -> 2번 채널
                self.log_message(f"🔇 채널 뮤트 요청: {channel_number}번 채널 (note_on, velocity={msg.velocity})")
                self.mute_channel(channel_number)
            
            else:
                self.log_message(f"ℹ️ note_on 채널 {msg.channel} - 처리하지 않음 (채널 1,2만 처리)")
        
        elif msg.type == 'note_off':
            # 채널 뮤트 해제 (Channel 2) - note_off = 뮤트 해제
            if msg.channel == 2:
                channel_number = msg.note + 1  # note=0 -> 1번 채널, note=1 -> 2번 채널
                self.log_message(f"🔊 채널 뮤트 해제 요청: {channel_number}번 채널 (note_off, velocity={msg.velocity})")
                self.unmute_channel(channel_number)
            else:
                self.log_message(f"ℹ️ note_off 채널 {msg.channel} - 처리하지 않음 (채널 2만 처리)")
        
        else:
            self.log_message(f"ℹ️ 처리하지 않는 MIDI 타입: {msg.type}")
    
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
    app = DM3MIDIController(root)
    
    # 창 닫기 이벤트 처리
    def on_closing():
        # app.stop_midi()  # 더 이상 사용하지 않음
        app.disconnect_dm3()
        app.stop_connection_monitor()
        app.cleanup_virtual_ports()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
