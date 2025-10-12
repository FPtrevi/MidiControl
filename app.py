#!/usr/bin/env python3
"""
Main entry point for MIDI Mixer Control application.
MVC-based architecture with GIL-safe threading for macOS + mido environment.
"""
import sys
import os
import signal
import threading
import time

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from controller.midi_controller import MidiController
from utils.logger import get_logger
from config.settings import LOG_LEVEL


class MidiMixerApp:
    """
    Main application class with proper signal handling and cleanup.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.controller: MidiController = None
        self.shutdown_event = threading.Event()
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("MIDI Mixer Control 애플리케이션 초기화")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"신호 수신: {signum}, 종료 중...")
        self.shutdown_event.set()
        self.shutdown()
    
    def run(self):
        """Run the application."""
        try:
            # Initialize controller
            self.controller = MidiController()
            
            # Start controller in separate thread to avoid blocking
            controller_thread = threading.Thread(
                target=self._run_controller,
                daemon=True,
                name="MidiController"
            )
            controller_thread.start()
            
            # Main update loop
            self._main_loop()
            
        except Exception as e:
            self.logger.error(f"애플리케이션 실행 오류: {e}")
            return 1
        
        return 0
    
    def _run_controller(self):
        """Run controller in separate thread."""
        try:
            # Controller는 GUI를 실행하지 않고 초기화만
            self.controller.initialize()
        except Exception as e:
            self.logger.error(f"컨트롤러 초기화 오류: {e}")
            self.shutdown_event.set()
    
    def _main_loop(self):
        """Main application loop with update cycle."""
        self.logger.info("메인 루프 시작")
        
        try:
            # GUI 메인 루프 시작 (블로킹)
            if self.controller and self.controller.view:
                self.controller.view.run()
                
        except KeyboardInterrupt:
            self.logger.info("사용자에 의해 중단됨")
        except Exception as e:
            self.logger.error(f"메인 루프 오류: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Shutdown the application gracefully."""
        try:
            self.logger.info("애플리케이션 종료 중...")
            
            if self.controller:
                self.controller.shutdown()
            
            self.shutdown_event.set()
            self.logger.info("애플리케이션 종료 완료")
            
        except Exception as e:
            self.logger.error(f"종료 중 오류: {e}")


def main():
    """Main entry point."""
    print("MIDI Mixer Control v1.0")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("오류: Python 3.7 이상이 필요합니다.")
        return 1
    
    # Check required packages
    try:
        import mido
        import tkinter
    except ImportError as e:
        print(f"오류: 필요한 패키지가 설치되지 않았습니다: {e}")
        print("다음 명령으로 설치하세요: pip install mido")
        return 1
    
    # Create and run application
    app = MidiMixerApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
