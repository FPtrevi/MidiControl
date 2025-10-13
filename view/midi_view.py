"""
Tkinter-based GUI for MIDI mixer control application.
Thread-safe implementation with proper GUI thread handling.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Callable, Optional, Dict, Any
import threading

from config.settings import (
    WINDOW_TITLE, WINDOW_SIZE, WINDOW_RESIZABLE, 
    DEFAULT_MIDI_CHANNEL, MIDI_CHANNEL_RANGE
)
from config.mixer_config import get_supported_mixers
from utils.logger import get_logger


class MidiMixerView:
    """
    Main GUI view for MIDI mixer control.
    Handles all UI interactions and provides callbacks to controller.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Create main window
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_SIZE[0]}x{WINDOW_SIZE[1]}")
        self.root.resizable(WINDOW_RESIZABLE[0], WINDOW_RESIZABLE[1])
        
        # Callback functions (set by controller)
        self.on_connect_callback: Optional[Callable] = None
        self.on_disconnect_callback: Optional[Callable] = None
        self.on_refresh_ports_callback: Optional[Callable] = None
        self.on_mixer_changed_callback: Optional[Callable] = None
        self.update_callback: Optional[Callable] = None
        
        # GUI variables
        self.mixer_var = tk.StringVar()
        self.input_midi_var = tk.StringVar()
        self.channel_var = tk.StringVar(value=str(DEFAULT_MIDI_CHANNEL))
        self.output_midi_var = tk.StringVar()
        
        # Connection state
        self.is_connected = False
        
        # Create GUI elements
        self._create_widgets()
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_widgets(self) -> None:
        """Create and layout all GUI widgets."""
        
        # Mixer selection
        mixer_label = ttk.Label(self.root, text="믹서 선택:")
        mixer_label.pack(pady=(20, 5))
        
        mixer_dropdown = ttk.Combobox(self.root, textvariable=self.mixer_var, state="readonly")
        mixer_dropdown['values'] = get_supported_mixers()
        mixer_dropdown.current(0)
        mixer_dropdown.bind('<<ComboboxSelected>>', self._on_mixer_selected)
        mixer_dropdown.pack()
        
        # Input MIDI
        input_midi_label = ttk.Label(self.root, text="입력 미디:")
        input_midi_label.pack(pady=(15, 5))
        
        self.input_midi_dropdown = ttk.Combobox(self.root, textvariable=self.input_midi_var, state="readonly")
        self.input_midi_dropdown.pack()
        
        # MIDI Channel
        channel_label = ttk.Label(self.root, text="MIDI 채널 번호 (1~16):")
        channel_label.pack(pady=(15, 5))
        
        channel_entry = ttk.Entry(self.root, textvariable=self.channel_var, width=10)
        channel_entry.pack()
        
        # Output MIDI
        output_midi_label = ttk.Label(self.root, text="출력 미디:")
        output_midi_label.pack(pady=(15, 5))
        
        self.output_midi_dropdown = ttk.Combobox(self.root, textvariable=self.output_midi_var, state="readonly")
        self.output_midi_dropdown.pack()
        
        # Control buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=(20, 10))
        
        self.connect_btn = ttk.Button(button_frame, text="연결", command=self._on_connect_toggle)
        self.connect_btn.pack(side="left")
        
        # Log area
        log_label = ttk.Label(self.root, text="MIDI 로그:")
        log_label.pack(pady=(15, 5))
        
        log_frame = ttk.Frame(self.root)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Scrollbar for log
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")
        
        # Log text widget
        self.log_text = tk.Text(log_frame, height=10, width=30, yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)
        
        # Initial mixer selection
        self._on_mixer_selected(None)
    
    def _on_mixer_selected(self, event) -> None:
        """Handle mixer selection change."""
        mixer = self.mixer_var.get()
        if self.on_mixer_changed_callback:
            self.on_mixer_changed_callback(mixer)
    
    def _on_connect_toggle(self) -> None:
        """Handle connect/disconnect button click."""
        if self.is_connected:
            self._on_disconnect()
        else:
            self._on_connect()
    
    def _on_connect(self) -> None:
        """Handle connection request."""
        if not self._validate_connection_params():
            return
        
        if self.on_connect_callback:
            self.on_connect_callback()
    
    def _on_disconnect(self) -> None:
        """Handle disconnection request."""
        if self.on_disconnect_callback:
            self.on_disconnect_callback()
    
    def _on_refresh_ports(self) -> None:
        """Deprecated: no-op (refresh is automatic)."""
        return
    
    def _validate_connection_params(self) -> bool:
        """Validate connection parameters."""
        # Check input port
        input_port = self.input_midi_var.get()
        if input_port in ["사용 가능한 포트 없음", "MIDI 포트 오류"]:
            messagebox.showerror("입력 오류", "유효한 MIDI 입력 포트를 선택해주세요.")
            return False
        
        # Check output port
        output_port = self.output_midi_var.get()
        if output_port in ["사용 가능한 포트 없음", "MIDI 포트 오류"]:
            messagebox.showerror("입력 오류", "유효한 MIDI 출력 포트를 선택해주세요.")
            return False
        
        # Check channel number
        try:
            channel_num = int(self.channel_var.get())
            min_ch, max_ch = MIDI_CHANNEL_RANGE
            if not (min_ch <= channel_num <= max_ch):
                raise ValueError()
        except ValueError:
            messagebox.showerror("입력 오류", "MIDI 채널 번호는 1에서 16 사이의 숫자여야 합니다.")
            return False
        
        return True
    
    def _on_closing(self) -> None:
        """Handle window closing."""
        if self.is_connected:
            self._on_disconnect()
        self.root.destroy()
    
    # Public interface methods
    def set_connect_callback(self, callback: Callable) -> None:
        """Set connect callback function."""
        self.on_connect_callback = callback
    
    def set_disconnect_callback(self, callback: Callable) -> None:
        """Set disconnect callback function."""
        self.on_disconnect_callback = callback
    
    def set_refresh_ports_callback(self, callback: Callable) -> None:
        """Deprecated: refresh is automatic; keep for compatibility."""
        self.on_refresh_ports_callback = None
    
    def set_mixer_changed_callback(self, callback: Callable) -> None:
        """Set mixer changed callback function."""
        self.on_mixer_changed_callback = callback
    
    def set_update_callback(self, callback: Callable) -> None:
        """Set update callback function."""
        self.update_callback = callback
    
    def update_input_ports(self, ports: List[str]) -> None:
        """Update input port dropdown options."""
        def _apply():
            # sanitize ports list: remove falsy/None and dedupe
            clean_ports = [p for p in ports if p]
            # fallback when empty
            if not clean_ports:
                clean_ports = ["사용 가능한 포트 없음"]

            self.input_midi_dropdown['values'] = clean_ports

            current = self.input_midi_var.get()
            if current not in clean_ports:
                # set to first valid option, or empty if placeholder
                self.input_midi_var.set(clean_ports[0] if clean_ports[0] != "사용 가능한 포트 없음" else "")

        if threading.current_thread() == threading.main_thread():
            _apply()
        else:
            self.root.after(0, _apply)
    
    def update_output_ports(self, ports: List[str]) -> None:
        """Update output port dropdown options."""
        def _apply():
            # sanitize ports list: remove falsy/None and dedupe
            clean_ports = [p for p in ports if p]
            # fallback when empty
            if not clean_ports:
                clean_ports = ["사용 가능한 포트 없음"]

            self.output_midi_dropdown['values'] = clean_ports

            current = self.output_midi_var.get()
            if current not in clean_ports:
                # set to first valid option, or empty if placeholder
                self.output_midi_var.set(clean_ports[0] if clean_ports[0] != "사용 가능한 포트 없음" else "")

        if threading.current_thread() == threading.main_thread():
            _apply()
        else:
            self.root.after(0, _apply)
    
    def set_connection_state(self, connected: bool) -> None:
        """Update connection state and button text."""
        self.is_connected = connected
        self.connect_btn.config(text="중지" if connected else "연결")
    
    def clear_log(self) -> None:
        """Clear the log text area."""
        self.log_text.delete(1.0, tk.END)
    
    def append_log(self, message: str) -> None:
        """Append message to log (thread-safe)."""
        def _append():
            self.log_text.insert(tk.END, f"{message}\n")
            self.log_text.see(tk.END)
        
        # Ensure GUI updates happen on main thread
        if threading.current_thread() == threading.main_thread():
            _append()
        else:
            self.root.after(0, _append)
    
    def show_message(self, title: str, message: str, msg_type: str = "info") -> None:
        """Show message dialog (thread-safe)."""
        def _show():
            if msg_type == "error":
                messagebox.showerror(title, message)
            elif msg_type == "warning":
                messagebox.showwarning(title, message)
            else:
                messagebox.showinfo(title, message)
        
        # Ensure dialogs appear on main thread
        if threading.current_thread() == threading.main_thread():
            _show()
        else:
            self.root.after(0, _show)
    
    def get_connection_params(self) -> Dict[str, Any]:
        """Get current connection parameters."""
        return {
            "mixer": self.mixer_var.get(),
            "input_port": self.input_midi_var.get(),
            "output_port": self.output_midi_var.get(),
            "channel": int(self.channel_var.get())
        }
    
    def run(self) -> None:
        """Start the GUI main loop."""
        self.logger.info("GUI 시작")
        
        # Set up update loop for MIDI message processing
        self._schedule_update()
        
        # Start Tkinter main loop
        self.root.mainloop()
    
    def _schedule_update(self) -> None:
        """Schedule periodic updates for MIDI message processing."""
        # Call controller update if available
        if self.update_callback:
            try:
                self.update_callback()
            except Exception as e:
                self.logger.error(f"업데이트 콜백 오류: {e}")
        
        # Schedule next update
        self.root.after(10, self._schedule_update)  # 10ms interval
    
    def quit(self) -> None:
        """Quit the GUI application."""
        self.root.quit()