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
# Removed mixer_config dependency - we'll define mixers directly
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
        
        # Mixer connection parameters
        self.dm3_ip_var = tk.StringVar(value="192.168.4.2")
        self.dm3_port_var = tk.StringVar(value="49900")
        self.qu5_ip_var = tk.StringVar(value="192.168.5.10")
        self.qu5_port_var = tk.StringVar(value="51325")
        self.qu5_channel_var = tk.StringVar(value="1")
        self.use_tcp_midi_var = tk.BooleanVar(value=True)
        
        # Connection state
        self.is_connected = False
        
        # Create GUI elements
        self._create_widgets()
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_widgets(self) -> None:
        """Create and layout all GUI widgets."""
        
        # Main container
        main_container = ttk.Frame(self.root, padding="10")
        main_container.pack(fill="both", expand=True)
        
        # Mixer selection
        mixer_frame = ttk.LabelFrame(main_container, text="믹서 선택", padding="5")
        mixer_frame.pack(fill="x", pady=(0, 10))
        
        mixer_dropdown = ttk.Combobox(mixer_frame, textvariable=self.mixer_var, state="readonly")
        mixer_dropdown['values'] = ["DM3", "Qu-5", "Qu-6", "Qu-7"]
        mixer_dropdown.current(0)
        mixer_dropdown.bind('<<ComboboxSelected>>', self._on_mixer_selected)
        mixer_dropdown.pack()
        
        # Mixer connection settings
        self.connection_frame = ttk.LabelFrame(main_container, text="믹서 연결 설정", padding="5")
        self.connection_frame.pack(fill="x", pady=(0, 10))
        
        # DM3 settings (initially hidden)
        self.dm3_frame = ttk.Frame(self.connection_frame)
        
        ttk.Label(self.dm3_frame, text="DM3 IP:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        ttk.Entry(self.dm3_frame, textvariable=self.dm3_ip_var, width=15).grid(row=0, column=1, padx=(0, 10))
        
        ttk.Label(self.dm3_frame, text="포트:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        ttk.Entry(self.dm3_frame, textvariable=self.dm3_port_var, width=10).grid(row=0, column=3)
        
        # Qu-5 settings (initially hidden)
        self.qu5_frame = ttk.Frame(self.connection_frame)
        
        ttk.Label(self.qu5_frame, text="Qu-5 IP:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        ttk.Entry(self.qu5_frame, textvariable=self.qu5_ip_var, width=15).grid(row=0, column=1, padx=(0, 10))
        
        ttk.Label(self.qu5_frame, text="포트:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        ttk.Entry(self.qu5_frame, textvariable=self.qu5_port_var, width=10).grid(row=0, column=3, padx=(0, 10))
        
        ttk.Label(self.qu5_frame, text="MIDI 채널:").grid(row=0, column=4, sticky="w", padx=(0, 5))
        ttk.Entry(self.qu5_frame, textvariable=self.qu5_channel_var, width=5).grid(row=0, column=5, padx=(0, 10))
        
        ttk.Checkbutton(self.qu5_frame, text="TCP/IP MIDI", variable=self.use_tcp_midi_var).grid(row=0, column=6)
        
        # Virtual MIDI info
        virtual_frame = ttk.LabelFrame(main_container, text="가상 MIDI 포트", padding="5")
        virtual_frame.pack(fill="x", pady=(0, 10))
        
        self.virtual_port_label = ttk.Label(virtual_frame, text="가상 MIDI 포트가 생성되면 여기에 표시됩니다.")
        self.virtual_port_label.pack()
        
        # Control buttons
        button_frame = ttk.Frame(main_container)
        button_frame.pack(pady=(0, 10))
        
        self.connect_btn = ttk.Button(button_frame, text="믹서 연결", command=self._on_connect_toggle)
        self.connect_btn.pack(side="left", padx=(0, 5))
        
        ttk.Button(button_frame, text="포트 새로고침", command=self._on_refresh_ports).pack(side="left")
        
        # Log area
        log_frame = ttk.LabelFrame(main_container, text="로그", padding="5")
        log_frame.pack(fill="both", expand=True)
        
        # Scrollbar for log
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")
        
        # Log text widget
        self.log_text = tk.Text(log_frame, height=12, width=80, yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)
        
        # Initial mixer selection
        self._on_mixer_selected(None)
    
    def _on_mixer_selected(self, event) -> None:
        """Handle mixer selection change."""
        mixer = self.mixer_var.get()
        
        # Show/hide appropriate connection settings
        if mixer == "DM3":
            self.dm3_frame.pack(fill="x")
            self.qu5_frame.pack_forget()
        elif mixer in ["Qu-5", "Qu-6", "Qu-7"]:
            self.qu5_frame.pack(fill="x")
            self.dm3_frame.pack_forget()
        
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
        mixer = self.mixer_var.get()
        
        if mixer == "DM3":
            # Validate DM3 connection parameters
            try:
                ip = self.dm3_ip_var.get()
                port = int(self.dm3_port_var.get())
                if not ip or port <= 0 or port > 65535:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("입력 오류", "DM3 IP 주소와 포트를 올바르게 입력해주세요.")
                return False
        
        elif mixer in ["Qu-5", "Qu-6", "Qu-7"]:
            # Validate Qu-5 connection parameters
            try:
                ip = self.qu5_ip_var.get()
                port = int(self.qu5_port_var.get())
                channel = int(self.qu5_channel_var.get())
                if not ip or port <= 0 or port > 65535 or channel < 1 or channel > 16:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("입력 오류", "Qu-5 IP 주소, 포트, MIDI 채널을 올바르게 입력해주세요.")
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
        """Update input port dropdown options (deprecated - virtual ports only)."""
        # Virtual ports are handled automatically, no need to update dropdowns
        pass
    
    def update_output_ports(self, ports: List[str]) -> None:
        """Update output port dropdown options (deprecated - virtual ports only)."""
        # Virtual ports are handled automatically, no need to update dropdowns
        pass
    
    def set_connection_state(self, connected: bool) -> None:
        """Update connection state and button text."""
        self.is_connected = connected
        self.connect_btn.config(text="연결 해제" if connected else "믹서 연결")
    
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
    
    def get_mixer_connection_params(self) -> Dict[str, Any]:
        """Get mixer-specific connection parameters."""
        mixer = self.mixer_var.get()
        
        if mixer == "DM3":
            return {
                "dm3_ip": self.dm3_ip_var.get(),
                "dm3_port": int(self.dm3_port_var.get())
            }
        elif mixer in ["Qu-5", "Qu-6", "Qu-7"]:
            return {
                "qu5_ip": self.qu5_ip_var.get(),
                "qu5_port": int(self.qu5_port_var.get()),
                "qu5_channel": int(self.qu5_channel_var.get()),
                "use_tcp_midi": self.use_tcp_midi_var.get()
            }
        
        return {}
    
    def update_virtual_port_status(self, port_name: str, active: bool) -> None:
        """Update virtual port status display."""
        if active:
            self.virtual_port_label.config(text=f"✅ 가상 MIDI 포트 활성: '{port_name}'")
        else:
            self.virtual_port_label.config(text=f"❌ 가상 MIDI 포트 비활성: '{port_name}'")
    
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