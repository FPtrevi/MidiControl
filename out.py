import mido
import time

# Qu5 MIDI 출력 포트 이름 (환경에 맞게 수정하세요)
QU5_MIDI_OUT_PORT = 'MIDI Control 1'

def send_scene_1(midi_out):
    # 씬 1은 Bank 0, Program 0 (Qu5는 씬 번호-1로 카운팅)
    bank = 0
    program = 0

    # Bank Change (Control Change 0)
    bank_change_msg = mido.Message('control_change', channel=0, control=0, value=bank)
    midi_out.send(bank_change_msg)
    time.sleep(0.05)  # 약간의 지연 추가

    # Program Change
    program_change_msg = mido.Message('program_change', channel=0, program=program)
    midi_out.send(program_change_msg)

    print("씬 1 호출 메시지를 전송했습니다.")

def main():
    try:
        with mido.open_output(QU5_MIDI_OUT_PORT) as midi_out:
            send_scene_1(midi_out)
    except IOError:
        print(f"포트 '{QU5_MIDI_OUT_PORT}'를 열 수 없습니다. 포트 이름을 확인해 주세요.")

if __name__ == '__main__':
    main()