import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from midi_handler import MidiHandler # 새로 작성한 midi_handler 모듈 임포트

class MidiMixerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MIDI 믹서 컨트롤러")
        self.geometry("450x550") # 좀 더 여유있는 크기로 조정
        self.resizable(False, False)
        
        # MIDI 핸들러 인스턴스 생성
        self.midi_handler = MidiHandler()
        
        # 모니터링 상태 (True: 시작됨, False: 중지됨)
        self.monitoring = False
        
        # GUI 요소 생성
        self.create_widgets()
        
        # 종료 시 자원 정리 (매우 중요)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def create_widgets(self):
        """GUI 위젯들을 생성하고 배치합니다."""
        
        # --- 믹서 설정 프레임 ---
        mixer_frame = ttk.LabelFrame(self, text="믹서 설정")
        mixer_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        # 믹서 선택 드롭다운
        ttk.Label(mixer_frame, text="믹서 선택:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.mixer_var = tk.StringVar()
        mixer_dropdown = ttk.Combobox(mixer_frame, textvariable=self.mixer_var, state="readonly")
        mixer_dropdown['values'] = ("Qu 5/6/7",)
        mixer_dropdown.current(0)
        mixer_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # MIDI 채널 입력
        ttk.Label(mixer_frame, text="MIDI 채널 (1~16):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.channel_var = tk.StringVar(value="1") # 기본값 1
        channel_entry = ttk.Entry(mixer_frame, textvariable=self.channel_var, width=5)
        channel_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        mixer_frame.grid_columnconfigure(1, weight=1) # 컬럼 1이 확장되도록 설정

        # --- MIDI 포트 설정 프레임 ---
        port_frame = ttk.LabelFrame(self, text="MIDI 포트 설정")
        port_frame.pack(fill="x", padx=10, pady=5)
        
        # 입력 MIDI 포트 선택
        ttk.Label(port_frame, text="입력 MIDI 포트:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.input_midi_var = tk.StringVar()
        self.input_midi_dropdown = ttk.Combobox(port_frame, textvariable=self.input_midi_var, state="readonly")
        self.input_midi_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # 출력 MIDI 포트 선택
        ttk.Label(port_frame, text="출력 MIDI 포트:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.output_midi_var = tk.StringVar()
        self.output_midi_dropdown = ttk.Combobox(port_frame, textvariable=self.output_midi_var, state="readonly")
        self.output_midi_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        port_frame.grid_columnconfigure(1, weight=1) # 컬럼 1이 확장되도록 설정

        # --- 제어 버튼 프레임 ---
        control_btn_frame = ttk.Frame(self)
        control_btn_frame.pack(fill="x", padx=10, pady=5)
        
        # 포트 새로고침 버튼
        refresh_btn = ttk.Button(control_btn_frame, text="포트 새로고침", command=self.refresh_ports)
        refresh_btn.pack(side="left", expand=True, fill="x", padx=5)
        
        # 모니터링 시작/중지 버튼 (텍스트 변경될 예정)
        self.monitor_btn = ttk.Button(control_btn_frame, text="MIDI 모니터링 시작", command=self.toggle_monitoring)
        self.monitor_btn.pack(side="left", expand=True, fill="x", padx=5)

        # --- 씬 제어 프레임 (추후 확장을 위해 미리 생성) ---
        scene_control_frame = ttk.LabelFrame(self, text="씬 제어")
        scene_control_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(scene_control_frame, text="씬 번호:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.scene_var = tk.StringVar(value="1")
        ttk.Entry(scene_control_frame, textvariable=self.scene_var, width=5).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Button(scene_control_frame, text="씬 호출", command=self.call_scene).grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        scene_control_frame.grid_columnconfigure(1, weight=1)


        # --- MIDI 신호 로그 영역 ---
        log_frame = ttk.LabelFrame(self, text="MIDI 신호 로그")
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 텍스트 위젯과 스크롤바 연결
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.log_text = tk.Text(log_frame, height=10, wrap="word", yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)
        
        # 초기 포트 목록 로드
        self.refresh_ports()
    
    def refresh_ports(self):
        """사용 가능한 MIDI 포트 목록을 새로고침하고 GUI에 업데이트합니다."""
        # 모니터링 중이라면 중지
        if self.monitoring:
            self.toggle_monitoring() # 모니터링 중지 함수 호출
        
        # 입력 포트 목록 가져오기 및 GUI 업데이트
        input_ports = self.midi_handler.get_input_ports()
        self.input_midi_dropdown['values'] = input_ports
        if input_ports and self.input_midi_var.get() not in input_ports:
            # 이전에 선택된 포트가 없거나, 현재 목록에 없으면 첫 번째 선택
            self.input_midi_var.set(input_ports[0])
        elif not input_ports: # 포트가 아예 없으면
            self.input_midi_var.set("사용 가능한 포트 없음")
        
        # 출력 포트 목록 가져오기 및 GUI 업데이트
        output_ports = self.midi_handler.get_output_ports()
        self.output_midi_dropdown['values'] = output_ports
        if output_ports and self.output_midi_var.get() not in output_ports:
            self.output_midi_var.set(output_ports[0])
        elif not output_ports: # 포트가 아예 없으면
            self.output_midi_var.set("사용 가능한 포트 없음")
        
        self.log("MIDI 포트 목록을 새로고침했습니다.")
        
    def toggle_monitoring(self):
        """MIDI 모니터링 시작/중지 상태를 전환합니다."""
        if self.monitoring:
            # --- 모니터링 중지 ---
            self.midi_handler.close_all_ports()
            self.monitoring = False
            self.monitor_btn.config(text="MIDI 모니터링 시작")
            self.log("MIDI 모니터링을 중지했습니다.")
        else:
            # --- 모니터링 시작 ---
            input_port_name = self.input_midi_var.get()
            output_port_name = self.output_midi_var.get()
            
            # 유효성 검사: 입력 포트
            if input_port_name in ["사용 가능한 포트 없음", "MIDI 포트 오류"]:
                messagebox.showerror("포트 오류", "유효한 MIDI 입력 포트를 선택해주세요.")
                return
            
            # 유효성 검사: 채널 번호
            try:
                channel_int = int(self.channel_var.get())
                if not (1 <= channel_int <= 16):
                    raise ValueError
            except ValueError:
                messagebox.showerror("입력 오류", "MIDI 채널 번호는 1에서 16 사이의 숫자여야 합니다.")
                return
            
            # 입력 포트 열기 시도
            if not self.midi_handler.open_input_port(input_port_name, self.on_midi_message_received):
                messagebox.showerror("연결 오류", f"입력 포트 '{input_port_name}'를 열 수 없습니다.")
                return
            
            # 출력 포트 열기 시도 (선택 사항)
            if output_port_name not in ["사용 가능한 포트 없음", "MIDI 포트 오류"]:
                self.midi_handler.open_output_port(output_port_name)
            
            self.monitoring = True
            self.monitor_btn.config(text="MIDI 모니터링 중지")
            self.log_text.delete(1.0, tk.END) # 로그창 비우기
            self.log(f"MIDI 모니터링 시작: 입력='{input_port_name}', 채널='{channel_int}'")

    def on_midi_message_received(self, msg):
        """MIDI 메시지 수신 시 호출되는 콜백 (MidiHandler에서 스레드로 호출됨)"""
        # GUI 업데이트는 Tkinter 메인 스레드에서만 안전하므로 self.after 사용
        self.after(0, lambda: self.log(f"MIDI 수신: {msg}"))

    def call_scene(self):
        """GUI에서 '씬 호출' 버튼 클릭 시 Qu5 믹서 씬을 호출합니다."""
        if not self.monitoring or not self.midi_handler._output_port:
            messagebox.showerror("오류", "먼저 MIDI 모니터링을 시작하고 유효한 출력 포트가 연결되어야 합니다.")
            return

        try:
            scene_number = int(self.scene_var.get())
            if not (1 <= scene_number <= 300): # Qu5 씬 범위 (예시)
                raise ValueError
        except ValueError:
            messagebox.showerror("입력 오류", "유효한 씬 번호 (1~300)를 입력하세요.")
            return
        
        try:
            # MIDI 채널은 GUI에서 설정된 값을 사용
            midi_channel = int(self.channel_var.get()) - 1 # Mido 채널은 0부터 시작
        except ValueError:
            messagebox.showerror("입력 오류", "유효한 MIDI 채널을 설정해주세요.")
            return

        if self.midi_handler.send_scene_change(scene_number, channel=midi_channel):
            self.log(f"씬 {scene_number} 호출 명령 전송 완료.")
        else:
            self.log(f"씬 {scene_number} 호출 명령 전송 실패.")

    def log(self, message):
        """로그 영역에 메시지를 추가하고 스크롤합니다."""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END) # 항상 최신 메시지가 보이도록 스크롤

    def on_closing(self):
        """애플리케이션 종료 시 MIDI 포트 및 스레드를 정리합니다."""
        self.midi_handler.close_all_ports()
        self.destroy() # Tkinter 창 닫기