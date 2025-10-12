# MIDI Mixer Control

ProPresenter에서 보내는 MIDI 신호를 받아서 Allen & Heath 믹서를 제어하는 Python 애플리케이션입니다.

## 기능

- **뮤트 제어**: ProPresenter 채널 0의 note_on/note_off로 믹서 입력 채널 뮤트 On/Off
- **씬 호출**: ProPresenter 채널 1의 note_on으로 믹서 씬 호출
- **믹서별 프로토콜 지원**: Qu 5/6/7 NRPN 프로토콜 지원 (확장 가능)
- **GIL-safe 설계**: macOS + Python + mido 환경에서 안정적인 멀티스레딩

## 구조

```
MControl/
├── model/              # 비즈니스 로직
│   ├── midi_backend.py    # MIDI 포트 관리
│   ├── mute_service.py    # 뮤트 제어 서비스
│   └── scene_service.py   # 씬 호출 서비스
├── view/               # UI 계층
│   └── midi_view.py       # Tkinter GUI
├── controller/         # 제어 계층
│   └── midi_controller.py # MVC 컨트롤러
├── config/             # 설정
│   ├── settings.py        # 애플리케이션 설정
│   └── mixer_config.py    # 믹서별 프로토콜 설정
├── utils/              # 유틸리티
│   └── logger.py          # 로깅
└── app.py              # 메인 엔트리포인트
```

## 설치

1. Python 3.7+ 설치
2. 의존성 설치:
   ```bash
   pip install -r requirements.txt
   ```

## 사용법

1. 애플리케이션 실행:
   ```bash
   python app.py
   ```

2. GUI에서 설정:
   - 믹서 선택: Qu 5/6/7
   - 입력 미디: ProPresenter 출력 포트 선택
   - 출력 미디: 믹서 입력 포트 선택
   - MIDI 채널: 송신할 채널 번호 (1-16)

3. "연결" 버튼 클릭

## MIDI 신호 매핑

### ProPresenter → 애플리케이션
- **채널 0, note_on/note_off**: 뮤트 제어
  - velocity ≥ 1: 뮤트 On
  - velocity = 0 또는 note_off: 뮤트 Off
- **채널 1, note_on (velocity > 0)**: 씬 호출
  - note=0 → 씬 1
  - note=1 → 씬 2
  - ...

### 애플리케이션 → 믹서
- **Qu 5/6/7 뮤트**: NRPN 시퀀스 (CC99→CC98→CC6→CC38)
- **Qu 5/6/7 씬**: Bank Select + Program Change (CC0→CC32→PC)

## 개발

### 새 믹서 추가
1. `config/mixer_config.py`에 믹서 설정 추가
2. 필요시 `model/mute_service.py` 또는 `model/scene_service.py`에 새 프로토콜 지원 추가

### 테스트
```bash
python -m pytest tests/
```

## 라이선스

MIT License
