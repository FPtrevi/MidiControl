
# import tkinter as tk
# from tkinter import ttk
# from tkinter import messagebox
# import mido

# class MidiMixerSelector(tk.Tk):
#     def __init__(self):
#         super().__init__()
#         self.title("MIDI 믹서 설정")
#         self.geometry("320x480")  # 드롭다운 2개 추가로 살짝 높이 확장
#         self.resizable(False, False)
        
#         # 믹서 선택 라벨 및 드롭다운
#         mixer_label = ttk.Label(self, text="믹서 선택:")
#         mixer_label.pack(pady=(20, 5))

#         self.mixer_var = tk.StringVar()
#         mixer_dropdown = ttk.Combobox(self, textvariable=self.mixer_var, state="readonly")
#         mixer_dropdown['values'] = ("Qu 5/6/7",)
#         mixer_dropdown.current(0)
#         mixer_dropdown.pack()

#         # 입력 미디 라벨 및 드롭다운
#         input_midi_label = ttk.Label(self, text="입력 미디:")
#         input_midi_label.pack(pady=(15, 5))

#         self.input_midi_var = tk.StringVar()
#         self.input_midi_dropdown = ttk.Combobox(self, textvariable=self.input_midi_var, state="readonly")
#         # MIDI 입력 포트 목록 가져오기
#         input_ports = self.get_midi_input_ports()
#         self.input_midi_dropdown['values'] = input_ports
#         if input_ports:
#             self.input_midi_var.set(input_ports[0])
#         self.input_midi_dropdown.pack()

#         # MIDI 채널 라벨 및 텍스트 박스
#         channel_label = ttk.Label(self, text="MIDI 채널 번호 (1~16):")
#         channel_label.pack(pady=(15, 5))

#         self.channel_var = tk.StringVar(value="1")  # 기본값 1로 설정
#         channel_entry = ttk.Entry(self, textvariable=self.channel_var, width=10)
#         channel_entry.pack()

#         # 출력 미디 라벨 및 드롭다운
#         output_midi_label = ttk.Label(self, text="출력 미디:")
#         output_midi_label.pack(pady=(15, 5))

#         self.output_midi_var = tk.StringVar()
#         self.output_midi_dropdown = ttk.Combobox(self, textvariable=self.output_midi_var, state="readonly")
#         # MIDI 출력 포트 목록 가져오기
#         output_ports = self.get_midi_output_ports()
#         self.output_midi_dropdown['values'] = output_ports
#         if output_ports:
#             self.output_midi_var.set(output_ports[0])
#         self.output_midi_dropdown.pack()

#         # 새로고침 버튼
#         refresh_btn = ttk.Button(self, text="포트 새로고침", command=self.refresh_ports)
#         refresh_btn.pack(pady=(10, 5))

#         # 확인 버튼
#         confirm_btn = ttk.Button(self, text="연결", command=self.confirm)
#         confirm_btn.pack(pady=5)

#     def get_midi_input_ports(self):
#         """사용 가능한 MIDI 입력 포트 목록 가져오기"""
#         try:
#             ports = mido.get_input_names()
#             return ports if ports else ["사용 가능한 포트 없음"]
#         except:
#             return ["MIDI 포트 오류"]
    
#     def get_midi_output_ports(self):
#         """사용 가능한 MIDI 출력 포트 목록 가져오기"""
#         try:
#             ports = mido.get_output_names()
#             return ports if ports else ["사용 가능한 포트 없음"]
#         except:
#             return ["MIDI 포트 오류"]
    
#     def refresh_ports(self):
#         """MIDI 포트 목록 새로고침"""
#         # 입력 포트 업데이트
#         input_ports = self.get_midi_input_ports()
#         self.input_midi_dropdown['values'] = input_ports
#         if input_ports and self.input_midi_var.get() not in input_ports:
#             self.input_midi_var.set(input_ports[0])
        
#         # 출력 포트 업데이트
#         output_ports = self.get_midi_output_ports()
#         self.output_midi_dropdown['values'] = output_ports
#         if output_ports and self.output_midi_var.get() not in output_ports:
#             self.output_midi_var.set(output_ports[0])
        
#         messagebox.showinfo("새로고침 완료", "MIDI 포트 목록을 새로고침했습니다.")

#     def confirm(self):
#         mixer = self.mixer_var.get()
#         input_midi = self.input_midi_var.get()
#         channel = self.channel_var.get()
#         output_midi = self.output_midi_var.get()

#         if not channel.isdigit() or not (1 <= int(channel) <= 16):
#             messagebox.showerror("입력 오류", "MIDI 채널 번호는 1에서 16 사이의 숫자여야 합니다.")
#             return
        
#         messagebox.showinfo(
#             "설정 완료", 
#             f"믹서: {mixer}\n입력 미디: {input_midi}\nMIDI 채널: {channel}\n출력 미디: {output_midi}"
#         )

# if __name__ == "__main__":
#     app = MidiMixerSelector()
#     app.mainloop()

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import mido
import threading
import time

class MidiMixerSelector(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MIDI 믹서 설정")
        self.geometry("320x480") # 초기 크기를 좀 더 여유있게
        self.resizable(False, False)
        
        # MIDI 모니터링 상태 변수
        self.is_monitoring = False
        self.midi_thread = None # MIDI 수신을 담당할 스레드
        self.input_port = None  # 현재 열려있는 MIDI 입력 포트 객체
        
        # --- GUI 위젯 생성 ---
        
        # 믹서 선택 라벨 및 드롭다운
        mixer_label = ttk.Label(self, text="믹서 선택:")
        mixer_label.pack(pady=(20, 5))

        self.mixer_var = tk.StringVar()
        mixer_dropdown = ttk.Combobox(self, textvariable=self.mixer_var, state="readonly")
        mixer_dropdown['values'] = ("Qu 5/6/7",)
        mixer_dropdown.current(0)
        mixer_dropdown.pack()

        # 입력 미디 라벨 및 드롭다운
        input_midi_label = ttk.Label(self, text="입력 미디:")
        input_midi_label.pack(pady=(15, 5))

        self.input_midi_var = tk.StringVar()
        self.input_midi_dropdown = ttk.Combobox(self, textvariable=self.input_midi_var, state="readonly")
        input_ports = self.get_midi_input_ports() # MIDI 입력 포트 목록 가져오기
        self.input_midi_dropdown['values'] = input_ports
        if input_ports:
            self.input_midi_var.set(input_ports[0])
        self.input_midi_dropdown.pack()

        # MIDI 채널 라벨 및 텍스트 박스
        channel_label = ttk.Label(self, text="MIDI 채널 번호 (1~16):")
        channel_label.pack(pady=(15, 5))

        self.channel_var = tk.StringVar(value="1") # 기본값 1로 설정
        channel_entry = ttk.Entry(self, textvariable=self.channel_var, width=10)
        channel_entry.pack()

        # 출력 미디 라벨 및 드롭다운
        output_midi_label = ttk.Label(self, text="출력 미디:")
        output_midi_label.pack(pady=(15, 5))

        self.output_midi_var = tk.StringVar()
        self.output_midi_dropdown = ttk.Combobox(self, textvariable=self.output_midi_var, state="readonly")
        output_ports = self.get_midi_output_ports() # MIDI 출력 포트 목록 가져오기
        self.output_midi_dropdown['values'] = output_ports
        if output_ports:
            self.output_midi_var.set(output_ports[0])
        self.output_midi_dropdown.pack()

        # 새로고침 버튼
        refresh_btn = ttk.Button(self, text="포트 새로고침", command=self.refresh_ports)
        refresh_btn.pack(pady=(10, 5))

        # 연결/중지 버튼 (상태에 따라 텍스트 변경)
        self.connect_btn = ttk.Button(self, text="연결", command=self.toggle_connection)
        self.connect_btn.pack(pady=5)
        
        # MIDI 로그 영역 추가
        log_label = ttk.Label(self, text="MIDI 로그:")
        log_label.pack(pady=(15, 5))
        
        # 로그 텍스트 영역과 스크롤바
        log_frame = ttk.Frame(self)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.log_text = tk.Text(log_frame, height=10, width=30, yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)
        
        # 앱 종료 시 스레드 정리 및 포트 닫기
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def get_midi_input_ports(self):
        """사용 가능한 MIDI 입력 포트 목록 가져오기"""
        try:
            ports = mido.get_input_names()
            return ports if ports else ["사용 가능한 포트 없음"]
        except Exception as e:
            # print(f"입력 포트 가져오기 오류: {e}") # 디버깅용
            return ["MIDI 포트 오류"]
    
    def get_midi_output_ports(self):
        """사용 가능한 MIDI 출력 포트 목록 가져오기"""
        try:
            ports = mido.get_output_names()
            return ports if ports else ["사용 가능한 포트 없음"]
        except Exception as e:
            # print(f"출력 포트 가져오기 오류: {e}") # 디버깅용
            return ["MIDI 포트 오류"]
    
    def refresh_ports(self):
        """MIDI 포트 목록 새로고침"""
        # 연결 중이면 먼저 연결 해제
        if self.is_monitoring:
            self.stop_monitoring()
            
        # 입력 포트 업데이트
        input_ports = self.get_midi_input_ports()
        self.input_midi_dropdown['values'] = input_ports
        if input_ports:
            # 현재 선택된 포트가 없거나 목록에 없으면 첫 번째 포트 선택
            if self.input_midi_var.get() not in input_ports:
                self.input_midi_var.set(input_ports[0])
        else: # 포트가 아예 없으면
            self.input_midi_var.set("사용 가능한 포트 없음")
        
        # 출력 포트 업데이트
        output_ports = self.get_midi_output_ports()
        self.output_midi_dropdown['values'] = output_ports
        if output_ports:
            if self.output_midi_var.get() not in output_ports:
                self.output_midi_var.set(output_ports[0])
        else: # 포트가 아예 없으면
            self.output_midi_var.set("사용 가능한 포트 없음")
        
        messagebox.showinfo("새로고침 완료", "MIDI 포트 목록을 새로고침했습니다.")

    def midi_listener(self, port_name):
        """별도의 스레드에서 MIDI 메시지를 수신하는 함수"""
        try:
            self.input_port = mido.open_input(port_name)
            self.log_message(f"'{port_name}' 포트에서 MIDI 메시지 수신 대기 중...")
            for msg in self.input_port:
                if not self.is_monitoring: # 모니터링 중지 요청이 들어오면 루프 종료
                    break
                # GUI 업데이트는 메인 스레드에서 해야 함 (Tkinter 규칙)
                self.after(0, self.log_message, f"MIDI 수신됨: {msg}")
        except Exception as e:
            self.after(0, self.log_message, f"MIDI 수신 오류: {e}")
        finally:
            if self.input_port:
                self.input_port.close()
                self.input_port = None
            self.after(0, self.log_message, f"MIDI 리스너 스레드 종료: '{port_name}'")
            self.is_monitoring = False # 오류 또는 종료 시 상태 업데이트
            self.after(0, self.connect_btn.config, {"text": "연결"}) # 버튼 텍스트도 다시 "연결"로

    def toggle_connection(self):
        """연결/중지 버튼 클릭 시 실행"""
        if self.is_monitoring:
            # 이미 모니터링 중이면 중지 요청
            self.stop_monitoring()
            self.connect_btn.config(text="연결") # 버튼 텍스트 변경
            self.log_message("MIDI 모니터링 중지 요청됨.")
        else:
            # 새로 모니터링 시작
            input_midi_port = self.input_midi_var.get()
            
            # 유효성 검사: 입력 포트
            if input_midi_port in ["사용 가능한 포트 없음", "MIDI 포트 오류"]:
                messagebox.showerror("입력 오류", "유효한 MIDI 입력 포트를 선택해주세요.")
                return

            # 채널 번호 유효성 검사
            try:
                channel_num = int(self.channel_var.get())
                if not (1 <= channel_num <= 16):
                    raise ValueError("1에서 16 사이의 숫자여야 합니다.")
            except ValueError:
                messagebox.showerror("입력 오류", "MIDI 채널 번호는 1에서 16 사이의 숫자여야 합니다.")
                return
            
            self.log_text.delete(1.0, tk.END) # 새 연결 시 로그 초기화

            # 스레드를 시작하여 MIDI 수신
            self.is_monitoring = True
            self.midi_thread = threading.Thread(target=self.midi_listener, args=(input_midi_port,), daemon=True)
            self.midi_thread.start()
            self.connect_btn.config(text="중지") # 버튼 텍스트 변경
            self.log_message(f"MIDI 모니터링 시작: 입력 포트 '{input_midi_port}'")

            # 출력 포트도 연결해야 할 경우 여기에 로직 추가 (현재는 입력만 구현)
            # output_midi_port = self.output_midi_var.get()
            # if output_midi_port not in ["사용 가능한 포트 없음", "MIDI 포트 오류"]:
            #     try:
            #         self.output_port = mido.open_output(output_midi_port)
            #         self.log_message(f"출력 포트 '{output_midi_port}' 연결됨.")
            #     except Exception as e:
            #         self.log_message(f"출력 포트 '{output_midi_port}' 연결 실패: {e}")

    def stop_monitoring(self):
        """MIDI 모니터링을 중지하고 리소스를 해제합니다."""
        self.is_monitoring = False
        if self.input_port:
            self.input_port.close() # 포트를 닫아 MIDI 리스너 루프를 강제로 종료
            self.input_port = None
        if self.midi_thread and self.midi_thread.is_alive():
            # 스레드가 종료될 때까지 잠시 대기 (daemon 스레드라 앱 종료 시 강제 종료됨)
            self.midi_thread.join(timeout=1.0) 
            
    def log_message(self, message):
        """GUI 로그 텍스트 위젯에 메시지를 추가합니다."""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END) # 항상 최신 메시지가 보이도록 스크롤

    def on_closing(self):
        """창이 닫힐 때 호출되어 MIDI 연결 및 스레드를 정리합니다."""
        self.stop_monitoring() # 앱 종료 시 모니터링 중지
        self.destroy() # Tkinter 앱 종료

if __name__ == "__main__":
    app = MidiMixerSelector()
    app.mainloop()