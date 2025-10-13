# 빠른 시작 가이드 - macOS 앱 배포

## 5분 안에 macOS 앱 만들기

### 1단계: 준비

```bash
# py2app 설치
pip3 install py2app

# 프로젝트 의존성 설치
pip3 install -r requirements.txt
```

### 2단계: 빌드

```bash
# 자동 빌드 스크립트 실행
./build_app.sh
```

이것만으로 끝입니다! `dist/` 폴더에 `MIDI Mixer Control.app`이 생성됩니다.

### 3단계: 테스트

```bash
# 앱 실행
open "dist/MIDI Mixer Control.app"
```

### 4단계: 배포 (선택사항)

**방법 A: ZIP으로 배포**
```bash
cd dist
zip -r "MIDI-Mixer-Control.zip" "MIDI Mixer Control.app"
```

**방법 B: DMG으로 배포 (권장)**
```bash
./create_dmg.sh
```

## 트러블슈팅

### "앱이 손상되었습니다" 에러

```bash
xattr -cr "dist/MIDI Mixer Control.app"
```

### 앱이 실행되지 않음

콘솔에서 직접 실행하여 에러 확인:
```bash
./dist/MIDI\ Mixer\ Control.app/Contents/MacOS/MIDI\ Mixer\ Control
```

### MIDI 포트가 표시되지 않음

앱을 종료하고 다시 빌드:
```bash
python3 setup.py py2app --clean
./build_app.sh
```

## 더 자세한 정보

- 전체 가이드: [DISTRIBUTION.md](DISTRIBUTION.md)
- 코드 서명 및 공증 방법
- 커스텀 아이콘 추가
- App Store 배포

## 주요 파일

- `setup.py` - py2app 설정
- `build_app.sh` - 자동 빌드 스크립트
- `create_dmg.sh` - DMG 생성 스크립트

## 다음 단계

1. ✅ 앱 빌드 완료
2. ✅ 앱 테스트 완료
3. [ ] 아이콘 추가 (선택)
4. [ ] 코드 서명 (권장)
5. [ ] DMG 생성
6. [ ] 배포!

즐거운 배포 되세요! 🚀

