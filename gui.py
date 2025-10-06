import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

class MidiMixerSelector(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MIDI 믹서 설정")
        self.geometry("320x280")  # 드롭다운 2개 추가로 살짝 높이 확장
        self.resizable(False, False)
        
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
        input_midi_dropdown = ttk.Combobox(self, textvariable=self.input_midi_var, state="readonly")
        input_midi_dropdown['values'] = ("IAC",)
        input_midi_dropdown.current(0)
        input_midi_dropdown.pack()

        # MIDI 채널 라벨 및 텍스트 박스
        channel_label = ttk.Label(self, text="MIDI 채널 번호 (1~16):")
        channel_label.pack(pady=(15, 5))

        self.channel_var = tk.StringVar()
        channel_entry = ttk.Entry(self, textvariable=self.channel_var, width=10)
        channel_entry.pack()

        # 출력 미디 라벨 및 드롭다운
        output_midi_label = ttk.Label(self, text="출력 미디:")
        output_midi_label.pack(pady=(15, 5))

        self.output_midi_var = tk.StringVar()
        output_midi_dropdown = ttk.Combobox(self, textvariable=self.output_midi_var, state="readonly")
        output_midi_dropdown['values'] = ("MIDI Control",)
        output_midi_dropdown.current(0)
        output_midi_dropdown.pack()

        # 확인 버튼
        confirm_btn = ttk.Button(self, text="확인", command=self.confirm)
        confirm_btn.pack(pady=15)

    def confirm(self):
        mixer = self.mixer_var.get()
        input_midi = self.input_midi_var.get()
        channel = self.channel_var.get()
        output_midi = self.output_midi_var.get()

        if not channel.isdigit() or not (1 <= int(channel) <= 16):
            messagebox.showerror("입력 오류", "MIDI 채널 번호는 1에서 16 사이의 숫자여야 합니다.")
            return
        
        messagebox.showinfo(
            "설정 완료", 
            f"믹서: {mixer}\n입력 미디: {input_midi}\nMIDI 채널: {channel}\n출력 미디: {output_midi}"
        )

if __name__ == "__main__":
    app = MidiMixerSelector()
    app.mainloop()