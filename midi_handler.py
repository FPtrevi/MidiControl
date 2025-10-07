import mido
import threading
import time

# 백엔드를 portmidi로 변경
mido.set_backend('mido.backends.portmidi')

class MidiHandler:
    def __init__(self):
        self._input_port = None
        self._output_port = None
        self._is_listening = False
        self._listener_thread = None
        self._listener_callback = None
    
    # midi_handler.py의 get_input_ports() 함수 수정
    def get_input_ports(self):
        """사용 가능한 모든 MIDI 입력 포트 목록을 반환합니다."""
        try:
            # 포트 목록을 직접 확인하고 로깅
            ports = mido.get_input_names()
            print(f"감지된 MIDI 입력 포트: {ports}")
            return ports if ports else ["사용 가능한 포트 없음"]
        except Exception as e:
            print(f"입력 포트 가져오기 오류: {e}")
            # 오류 상세 정보 출력
            import traceback
            traceback.print_exc()
            return ["MIDI 포트 오류"]

    # midi_handler.py의 get_output_ports() 함수 수정
    def get_output_ports(self):
        """사용 가능한 모든 MIDI 출력 포트 목록을 반환합니다."""
        try:
            # 포트 목록을 직접 확인하고 로깅
            ports = mido.get_output_names()
            print(f"감지된 MIDI 출력 포트: {ports}")
            return ports if ports else ["사용 가능한 포트 없음"]
        except Exception as e:
            print(f"출력 포트 가져오기 오류: {e}")
            # 오류 상세 정보 출력
            import traceback
            traceback.print_exc()
            return ["MIDI 포트 오류"]

    def open_input_port(self, port_name, callback):
        """지정된 이름의 MIDI 입력 포트를 열고, 메시지 수신 콜백을 설정합니다."""
        self.close_input_port()  # 기존 포트가 열려있으면 닫기
        try:
            if port_name in ["사용 가능한 포트 없음", "MIDI 포트 오류"]:
                return False
                
            self._input_port = mido.open_input(port_name)
            self._listener_callback = callback
            self._is_listening = True
            self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._listener_thread.start()
            return True
        except Exception as e:
            print(f"입력 포트 '{port_name}' 열기 실패: {e}")
            return False

    def close_input_port(self):
        """열려있는 MIDI 입력 포트를 닫고, 리스닝 스레드를 중지합니다."""
        if self._is_listening:
            self._is_listening = False
            if self._listener_thread and self._listener_thread.is_alive():
                self._listener_thread.join(timeout=1.0)
        if self._input_port:
            self._input_port.close()
            self._input_port = None
    
    def open_output_port(self, port_name):
        """지정된 이름의 MIDI 출력 포트를 엽니다."""
        self.close_output_port()  # 기존 포트가 열려있으면 닫기
        try:
            if port_name in ["사용 가능한 포트 없음", "MIDI 포트 오류"]:
                return False
                
            self._output_port = mido.open_output(port_name)
            return True
        except Exception as e:
            print(f"출력 포트 '{port_name}' 열기 실패: {e}")
            return False

    def close_output_port(self):
        """열려있는 MIDI 출력 포트를 닫습니다."""
        if self._output_port:
            self._output_port.close()
            self._output_port = None
            
    def _listen_loop(self):
        """MIDI 메시지를 비동기적으로 수신하고 콜백 함수를 호출하는 루프."""
        if not self._input_port:
            return

        try:
            while self._is_listening:
                # portmidi는 블로킹 방식이 달라서 이렇게 처리
                msg = self._input_port.poll()
                if msg and self._listener_callback:
                    self._listener_callback(msg)
                time.sleep(0.001)  # CPU 부하 감소
        except Exception as e:
            print(f"MIDI 수신 중 오류 발생: {e}")
        finally:
            print("MIDI 리스닝 스레드 종료.")
            self._is_listening = False

    def send_midi_message(self, msg):
        """MIDI 메시지를 열려있는 출력 포트로 전송합니다."""
        if self._output_port:
            try:
                self._output_port.send(msg)
                return True
            except Exception as e:
                print(f"MIDI 메시지 전송 실패: {e}")
                return False
        return False
        
    def send_scene_change(self, scene_number, channel=0):
        """씬 변경 MIDI 메시지 전송"""
        if not self._output_port:
            return False
        
        # 씬 번호를 Bank와 Program 값으로 변환
        if 1 <= scene_number <= 128:
            bank = 0
            program = scene_number - 1
        elif 129 <= scene_number <= 256:
            bank = 1
            program = scene_number - 129
        elif 257 <= scene_number <= 300:
            bank = 2
            program = scene_number - 257
        else:
            return False
        
        # Bank Change 메시지 전송
        bank_change_msg = mido.Message('control_change', channel=channel, control=0, value=bank)
        self.send_midi_message(bank_change_msg)
        time.sleep(0.05)  # 안정적인 전송을 위한 약간의 지연
        
        # Program Change 메시지 전송
        program_change_msg = mido.Message('program_change', channel=channel, program=program)
        self.send_midi_message(program_change_msg)
        
        return True
        
    def close_all_ports(self):
        """열려있는 모든 MIDI 포트를 닫고 스레드를 중지합니다."""
        self.close_input_port()
        self.close_output_port()