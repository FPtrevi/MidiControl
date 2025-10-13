# macOS 앱 배포 가이드

이 문서는 MIDI Mixer Control을 macOS .app 번들로 패키징하고 배포하는 방법을 설명합니다.

## 방법 1: py2app (권장)

### 1단계: 개발 의존성 설치

```bash
pip install py2app
```

### 2단계: 앱 번들 빌드

```bash
# 개발 모드로 먼저 테스트 (선택사항)
python setup.py py2app -A

# 프로덕션 빌드
python setup.py py2app
```

빌드가 완료되면 `dist/` 폴더에 `MIDI Mixer Control.app` 파일이 생성됩니다.

### 3단계: 앱 테스트

```bash
# 빌드된 앱 실행
open "dist/MIDI Mixer Control.app"
```

### 4단계: 배포

**옵션 A: 직접 배포**
- `dist/MIDI Mixer Control.app` 파일을 zip으로 압축하여 공유
- 사용자는 압축을 풀고 Applications 폴더로 드래그

**옵션 B: DMG 이미지 생성** (더 전문적)
```bash
# create-dmg 설치 (Homebrew 사용)
brew install create-dmg

# DMG 생성
create-dmg \
  --volname "MIDI Mixer Control" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --app-drop-link 425 120 \
  "MIDI-Mixer-Control-1.0.0.dmg" \
  "dist/MIDI Mixer Control.app"
```

## 방법 2: PyInstaller (대안)

### 1단계: PyInstaller 설치

```bash
pip install pyinstaller
```

### 2단계: spec 파일 생성

```bash
pyinstaller --name="MIDI Mixer Control" \
            --windowed \
            --onefile \
            --add-data="config:config" \
            --hidden-import=mido \
            --hidden-import=rtmidi \
            app.py
```

### 3단계: 앱 빌드

```bash
pyinstaller "MIDI Mixer Control.spec"
```

빌드된 앱은 `dist/MIDI Mixer Control.app`에 생성됩니다.

## 아이콘 추가 (선택사항)

macOS 앱에 커스텀 아이콘을 추가하려면:

### 1. 아이콘 이미지 준비
- 1024x1024 PNG 이미지 준비

### 2. ICNS 파일 생성

```bash
# iconutil 사용 (macOS 내장)
mkdir MyIcon.iconset
sips -z 16 16     icon.png --out MyIcon.iconset/icon_16x16.png
sips -z 32 32     icon.png --out MyIcon.iconset/icon_16x16@2x.png
sips -z 32 32     icon.png --out MyIcon.iconset/icon_32x32.png
sips -z 64 64     icon.png --out MyIcon.iconset/icon_32x32@2x.png
sips -z 128 128   icon.png --out MyIcon.iconset/icon_128x128.png
sips -z 256 256   icon.png --out MyIcon.iconset/icon_128x128@2x.png
sips -z 256 256   icon.png --out MyIcon.iconset/icon_256x256.png
sips -z 512 512   icon.png --out MyIcon.iconset/icon_256x256@2x.png
sips -z 512 512   icon.png --out MyIcon.iconset/icon_512x512.png
sips -z 1024 1024 icon.png --out MyIcon.iconset/icon_512x512@2x.png

iconutil -c icns MyIcon.iconset
mv MyIcon.icns icon.icns
```

### 3. setup.py에서 아이콘 설정
`setup.py` 파일의 `iconfile` 부분을 수정:

```python
'iconfile': 'icon.icns',
```

## 코드 서명 및 공증 (선택사항, App Store 외부 배포)

macOS Gatekeeper를 통과하려면 앱에 서명해야 합니다.

### 1. 개발자 인증서 필요
- Apple Developer Program 가입 필요 ($99/년)

### 2. 앱 서명

```bash
# 개발자 ID 확인
security find-identity -v -p codesigning

# 앱 서명
codesign --deep --force --verify --verbose --sign "Developer ID Application: YOUR NAME" \
  "dist/MIDI Mixer Control.app"

# 서명 확인
codesign --verify --deep --strict --verbose=2 "dist/MIDI Mixer Control.app"
spctl -a -t exec -vv "dist/MIDI Mixer Control.app"
```

### 3. 앱 공증 (Notarization)

```bash
# DMG 생성 후
xcrun notarytool submit MIDI-Mixer-Control-1.0.0.dmg \
  --apple-id "your@email.com" \
  --team-id "TEAM_ID" \
  --password "app-specific-password" \
  --wait

# 공증 티켓 스테이플
xcrun stapler staple MIDI-Mixer-Control-1.0.0.dmg
```

## 트러블슈팅

### 문제: "앱이 손상되어 열 수 없습니다"

**해결책:**
```bash
# Gatekeeper 속성 제거 (개발/테스트 용도)
xattr -cr "dist/MIDI Mixer Control.app"
```

### 문제: MIDI 포트를 찾을 수 없음

**해결책:**
- `setup.py`의 `packages`에 `rtmidi`가 포함되어 있는지 확인
- python-rtmidi가 제대로 빌드되었는지 확인

### 문제: 앱 실행 시 크래시

**해결책:**
```bash
# 콘솔에서 직접 실행하여 에러 확인
./dist/MIDI\ Mixer\ Control.app/Contents/MacOS/MIDI\ Mixer\ Control
```

## 빌드 정리

```bash
# 빌드 파일 정리
python setup.py py2app --clean
rm -rf build/ dist/
```

## 참고사항

- **py2app**: macOS 전용, tkinter 앱에 최적화
- **PyInstaller**: 크로스 플랫폼 지원, 더 큰 번들 크기
- **코드 서명 없이 배포**: 사용자가 "시스템 설정 > 개인정보 보호 및 보안"에서 수동으로 허용해야 함
- **DMG 배포**: 가장 전문적이고 사용자 친화적인 방법

## 배포 체크리스트

- [ ] py2app 설치
- [ ] setup.py 설정 확인
- [ ] 앱 빌드 테스트
- [ ] 빌드된 앱 실행 테스트
- [ ] 아이콘 추가 (선택)
- [ ] DMG 생성 (선택)
- [ ] 코드 서명 (선택, 권장)
- [ ] 앱 공증 (선택, 권장)
- [ ] 다른 macOS 기기에서 테스트
- [ ] 배포

