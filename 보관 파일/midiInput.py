# midiInput.py
import mido

def list_input_ports():
    print("사용 가능한 MIDI 입력 포트 목록:")
    for port in mido.get_input_names():
        print(f' - {port}')

def main():
    list_input_ports()
    midi_port_name = input("ProPresenter MIDI 출력 포트 이름을 입력하세요: ")

    try:
        with mido.open_input(midi_port_name) as inport:
            print(f"'{midi_port_name}' 포트에서 MIDI 메시지 수신 대기 중...")
            for msg in inport:
                print(f"MIDI 수신됨: {msg}")
    except IOError:
        print(f"포트 '{midi_port_name}'를 열 수 없습니다. 이름을 다시 확인해주세요.")

if __name__ == "__main__":
    main()