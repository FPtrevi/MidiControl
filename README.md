# MIDI Mixer Control

ProPresenter에서 보내는 MIDI 신호를 받아서 DM3와 Qu-5/6/7 믹서를 제어하는 Python 애플리케이션입니다.

## 기능

- **DM3 믹서 지원**: OSC 통신으로 DM3 믹서 제어
- **Qu-5/6/7 믹서 지원**: TCP/IP MIDI 또는 USB MIDI로 Qu 시리즈 믹서 제어
- **가상 MIDI 포트**: 프로프리젠터와 직접 연결 가능한 가상 MIDI 포트 생성
- **씬 리콜**: ProPresenter 채널 1의 note_on으로 믹서 씬 호출
- **뮤트 제어**: ProPresenter 채널 2의 note_on/note_off로 믹서 입력 채널 뮤트 On/Off
- **네트워크 연결 모니터링**: 믹서 연결 상태 실시간 감시
- **GIL-safe 설계**: macOS + Python + mido 환경에서 안정적인 멀티스레딩

## 구조

```
MControl/
├── model/              # 비즈니스 로직
│   ├── midi_backend.py    # 가상 MIDI 포트 관리
│   ├── dm3_osc_service.py # DM3 OSC 통신 서비스
│   ├── qu5_midi_service.py # Qu-5 MIDI 통신 서비스
│   └── base_service.py    # 기본 서비스 클래스
├── view/               # UI 계층
│   └── midi_view.py       # Tkinter GUI
├── controller/         # 제어 계층
│   └── midi_controller.py # MVC 컨트롤러
├── config/             # 설정
│   └── settings.py        # 애플리케이션 설정
├── utils/              # 유틸리티
│   ├── logger.py          # 로깅
│   └── prefs.py           # 설정 저장/로드
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
   - 믹서 선택: DM3 또는 Qu-5/6/7
   - 믹서 연결 설정:
     - DM3: IP 주소와 포트 설정
     - Qu-5/6/7: IP 주소, 포트, MIDI 채널 설정
   - 가상 MIDI 포트가 자동으로 생성됩니다

3. "믹서 연결" 버튼 클릭

4. ProPresenter에서 가상 MIDI 포트를 선택하여 연결

## MIDI 신호 매핑

### ProPresenter → 애플리케이션 (가상 MIDI 포트)
- **채널 1, note_on (velocity > 0)**: 씬 리콜
  - note=0 → 1번 씬, note=1 → 2번 씬, ...
- **채널 2, note_on/note_off**: 뮤트 제어
  - velocity ≥ 1: 뮤트 On
  - velocity = 0 또는 note_off: 뮤트 Off
  - note=0 → 1번 채널, note=1 → 2번 채널, ...

### 애플리케이션 → 믹서

#### DM3 믹서 (OSC 통신)
- **씬 리콜**: `/yosc:req/ssrecall_ex "scene_a" <번호>`
- **뮤트 제어**: `/yosc:req/set/MIXER:Current/InCh/Fader/On/<채널>/1 <값>`

#### Qu-5/6/7 믹서 (MIDI 통신)
- **씬 리콜**: Program Change 메시지
- **뮤트 제어**: NRPN 시퀀스 (CC99→CC98→CC6→CC38)

## 배포

### macOS 앱으로 빌드

이 애플리케이션을 독립 실행형 macOS .app 파일로 배포할 수 있습니다.

#### 빠른 빌드
```bash
./build_app.sh
```

#### DMG 설치 파일 생성
```bash
./create_dmg.sh
```

자세한 내용은 [DISTRIBUTION.md](DISTRIBUTION.md)를 참조하세요.

## 개발

### 새 믹서 추가
1. `model/` 디렉토리에 새 믹서 서비스 클래스 생성 (예: `new_mixer_service.py`)
2. `BaseMidiService`를 상속받아 `handle_mute()`와 `handle_scene()` 메서드 구현
3. `controller/midi_controller.py`에서 새 믹서 타입 지원 추가
4. `view/midi_view.py`에서 GUI 설정 추가

### 테스트
```bash
python -m pytest tests/
```

## 라이선스

MIT License
