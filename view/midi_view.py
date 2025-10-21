"""
Tkinter-based GUI for MIDI mixer control application.
Thread-safe implementation with proper GUI thread handling.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Callable, Optional, Dict, Any, Union
import threading

from config.settings import (
    WINDOW_TITLE, WINDOW_SIZE, WINDOW_RESIZABLE, 
    DEFAULT_MIDI_CHANNEL, MIDI_CHANNEL_RANGE,
    DEFAULT_DM3_IP, DEFAULT_DM3_PORT, DEFAULT_QU5_IP, DEFAULT_QU5_PORT
)
# Removed mixer_config dependency - we'll define mixers directly
from utils.logger import get_logger
from utils.prefs import load_prefs, save_prefs


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
        self.on_connect_callback: Optional[Callable[[], None]] = None
        self.on_disconnect_callback: Optional[Callable[[], None]] = None
        self.on_refresh_ports_callback: Optional[Callable[[], None]] = None
        self.on_mixer_changed_callback: Optional[Callable[[str], None]] = None
        self.update_callback: Optional[Callable[[], None]] = None
        
        # GUI variables
        self.mixer_var = tk.StringVar()
        self.input_midi_var = tk.StringVar()
        self.channel_var = tk.StringVar(value=str(DEFAULT_MIDI_CHANNEL))
        self.output_midi_var = tk.StringVar()
        
        # MIDI channel for mixer control
        self.midi_channel_var = tk.StringVar(value="1")
        
        # Mixer connection parameters - load from preferences
        prefs = load_prefs()
        self.dm3_ip_var = tk.StringVar(value=prefs.get("dm3_ip", DEFAULT_DM3_IP))
        self.dm3_port_var = tk.StringVar(value=str(prefs.get("dm3_port", DEFAULT_DM3_PORT)))
        self.qu5_ip_var = tk.StringVar(value=prefs.get("qu5_ip", DEFAULT_QU5_IP))
        self.qu5_port_var = tk.StringVar(value=str(prefs.get("qu5_port", DEFAULT_QU5_PORT)))
        self.qu5_channel_var = tk.StringVar(value=str(prefs.get("qu5_channel", 1)))
        self.use_tcp_midi_var = tk.BooleanVar(value=prefs.get("use_tcp_midi", True))
        
        # Connection state
        self.is_connected = False
        self._initialized = False
        
        # Control references for enabling/disabling
        self.mixer_dropdown = None
        self.connection_frame = None
        self.midi_channel_frame = None
        
        # Create GUI elements
        self._create_widgets()
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        self._initialized = True
    
    def _create_widgets(self) -> None:
        """Create and layout all GUI widgets."""
        
        # Main container
        main_container = ttk.Frame(self.root, padding="10")
        main_container.pack(fill="both", expand=True)
        
        # Mixer selection
        mixer_frame = ttk.LabelFrame(main_container, text="믹서 선택", padding="5")
        mixer_frame.pack(fill="x", pady=(0, 10))
        
        self.mixer_dropdown = ttk.Combobox(mixer_frame, textvariable=self.mixer_var, state="readonly")
        self.mixer_dropdown['values'] = ["DM3", "Qu-5/6/7"]
        self.mixer_dropdown.current(0)
        self.mixer_dropdown.bind('<<ComboboxSelected>>', self._on_mixer_selected)
        self.mixer_dropdown.pack()
        
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
        
        # MIDI Channel settings
        self.midi_channel_frame = ttk.LabelFrame(main_container, text="MIDI 채널 설정", padding="5")
        self.midi_channel_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(self.midi_channel_frame, text="믹서 MIDI 채널:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.midi_channel_spinbox = ttk.Spinbox(self.midi_channel_frame, from_=1, to=16, textvariable=self.midi_channel_var, width=5)
        self.midi_channel_spinbox.grid(row=0, column=1, padx=(0, 10))
        
        ttk.Label(self.midi_channel_frame, text="(1-16, 믹서로 전송되는 MIDI 메시지의 채널)", 
                 font=("TkDefaultFont", 8)).grid(row=0, column=2, sticky="w")
        
        # Control buttons
        button_frame = ttk.Frame(main_container)
        button_frame.pack(pady=(0, 10))
        
        self.connect_btn = ttk.Button(button_frame, text="믹서 연결", command=self._on_connect_toggle)
        self.connect_btn.pack()
        
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
            # DM3는 OSC를 사용하므로 MIDI 채널 설정 비활성화
            self._set_midi_channel_frame_state("disabled")
        elif mixer == "Qu-5/6/7":
            self.qu5_frame.pack(fill="x")
            self.dm3_frame.pack_forget()
            # Qu-5/6/7는 MIDI를 사용하므로 MIDI 채널 설정 활성화
            self._set_midi_channel_frame_state("normal")
        
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
        
        # Save current IP settings to preferences
        self._save_connection_prefs()
        
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
                ip = self.dm3_ip_var.get().strip()
                port = int(self.dm3_port_var.get().strip())
                if not ip or port <= 0 or port > 65535:
                    raise ValueError()
            except (ValueError, AttributeError):
                messagebox.showerror("입력 오류", "DM3 IP 주소와 포트를 올바르게 입력해주세요.")
                return False
        
        elif mixer == "Qu-5/6/7":
            # Validate Qu-5/6/7 connection parameters
            try:
                ip = self.qu5_ip_var.get().strip()
                port = int(self.qu5_port_var.get().strip())
                channel = int(self.qu5_channel_var.get().strip())
                if not ip or port <= 0 or port > 65535 or channel < 1 or channel > 16:
                    raise ValueError()
            except (ValueError, AttributeError):
                messagebox.showerror("입력 오류", "Qu-5/6/7 IP 주소, 포트, MIDI 채널을 올바르게 입력해주세요.")
                return False
        
        return True
    
    def _save_connection_prefs(self) -> None:
        """Save current connection settings to preferences."""
        prefs = load_prefs()
        prefs["dm3_ip"] = self.dm3_ip_var.get()
        prefs["dm3_port"] = int(self.dm3_port_var.get())
        prefs["qu5_ip"] = self.qu5_ip_var.get()
        prefs["qu5_port"] = int(self.qu5_port_var.get())
        prefs["qu5_channel"] = int(self.qu5_channel_var.get())
        prefs["use_tcp_midi"] = self.use_tcp_midi_var.get()
        save_prefs(prefs)
    
    def _set_connection_frame_state(self, state: str) -> None:
        """Enable/disable all widgets in connection frame."""
        if state == "disabled":
            # Disable all entry widgets and checkbuttons in connection frames
            for widget in self.connection_frame.winfo_children():
                self._set_widget_state_recursive(widget, state)
        else:
            # Enable all widgets in connection frames
            for widget in self.connection_frame.winfo_children():
                self._set_widget_state_recursive(widget, state)
    
    def _set_midi_channel_frame_state(self, state: str) -> None:
        """Enable/disable all widgets in MIDI channel frame."""
        if state == "disabled":
            # Disable spinbox
            self.midi_channel_spinbox.config(state=state)
        else:
            # Enable spinbox
            self.midi_channel_spinbox.config(state=state)
    
    def _set_widget_state_recursive(self, widget, state: str) -> None:
        """Recursively set widget state for nested widgets."""
        try:
            if hasattr(widget, 'config'):
                # Check if widget has state config
                try:
                    widget.config(state=state)
                except tk.TclError:
                    # Widget doesn't support state config, skip
                    pass
            
            # Recursively apply to children
            for child in widget.winfo_children():
                self._set_widget_state_recursive(child, state)
        except tk.TclError:
            # Widget might be destroyed, ignore
            pass
    
    def _on_closing(self) -> None:
        """Handle window closing."""
        if not self._initialized:
            return
            
        if self.is_connected:
            self._on_disconnect()
        self.root.destroy()
    
    # Public interface methods
    def set_connect_callback(self, callback: Callable[[], None]) -> None:
        """Set connect callback function."""
        self.on_connect_callback = callback
    
    def set_disconnect_callback(self, callback: Callable[[], None]) -> None:
        """Set disconnect callback function."""
        self.on_disconnect_callback = callback
    
    def set_refresh_ports_callback(self, callback: Callable[[], None]) -> None:
        """Deprecated: refresh is automatic; keep for compatibility."""
        self.on_refresh_ports_callback = None
    
    def set_mixer_changed_callback(self, callback: Callable[[str], None]) -> None:
        """Set mixer changed callback function."""
        self.on_mixer_changed_callback = callback
    
    def set_update_callback(self, callback: Callable[[], None]) -> None:
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
        
        # Enable/disable controls based on connection state
        if connected:
            # 연결 시 모든 컨트롤 비활성화
            self.mixer_dropdown.config(state="disabled")
            self._set_connection_frame_state("disabled")
            self._set_midi_channel_frame_state("disabled")
        else:
            # 연결 해제 시 믹서 타입에 따라 적절한 상태로 복원
            self.mixer_dropdown.config(state="normal")
            self._set_connection_frame_state("normal")
            # MIDI 채널 설정은 믹서 타입에 따라 활성화/비활성화
            mixer = self.mixer_var.get()
            if mixer == "DM3":
                self._set_midi_channel_frame_state("disabled")
            else:  # Qu-5/6/7
                self._set_midi_channel_frame_state("normal")
    
    def clear_log(self) -> None:
        """Clear the log text area."""
        self.log_text.delete(1.0, tk.END)
    
    def append_log(self, message: str) -> None:
        """Append message to log (thread-safe)."""
        if not self._initialized:
            return
            
        def _append():
            try:
                self.log_text.insert(tk.END, f"{message}\n")
                self.log_text.see(tk.END)
            except tk.TclError:
                # Widget might be destroyed
                pass
        
        # Ensure GUI updates happen on main thread
        if threading.current_thread() == threading.main_thread():
            _append()
        else:
            self.root.after(0, _append)
    
    def show_message(self, title: str, message: str, msg_type: str = "info") -> None:
        """Show message dialog (thread-safe)."""
        if not self._initialized:
            return
            
        def _show():
            try:
                if msg_type == "error":
                    messagebox.showerror(title, message)
                elif msg_type == "warning":
                    messagebox.showwarning(title, message)
                else:
                    messagebox.showinfo(title, message)
            except tk.TclError:
                # Widget might be destroyed
                pass
        
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
            "channel": int(self.channel_var.get()),
            "midi_channel": int(self.midi_channel_var.get())
        }
    
    def get_mixer_connection_params(self) -> Dict[str, Any]:
        """Get mixer-specific connection parameters."""
        mixer = self.mixer_var.get()
        
        if mixer == "DM3":
            return {
                "dm3_ip": self.dm3_ip_var.get(),
                "dm3_port": int(self.dm3_port_var.get())
            }
        elif mixer == "Qu-5/6/7":
            return {
                "qu5_ip": self.qu5_ip_var.get(),
                "qu5_port": int(self.qu5_port_var.get()),
                "qu5_channel": int(self.qu5_channel_var.get()),
                "use_tcp_midi": self.use_tcp_midi_var.get()
            }
        
        return {}
    
    def update_virtual_port_status(self, port_name: str, active: bool) -> None:
        """Update virtual port status display (deprecated - GUI element removed)."""
        # Virtual port display removed from GUI, but keep method for compatibility
        pass
    
    def run(self) -> None:
        """Start the GUI main loop."""
        self.logger.info("GUI 시작")
        
        # Set up update loop for MIDI message processing
        self._schedule_update()
        
        # Start Tkinter main loop
        self.root.mainloop()
    
    def _schedule_update(self) -> None:
        """Schedule periodic updates for MIDI message processing."""
        if not self._initialized:
            return
            
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
        if self._initialized:
            self._initialized = False
            self.root.quit()