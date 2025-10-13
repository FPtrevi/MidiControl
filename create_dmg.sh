#!/bin/bash
# DMG 이미지 생성 스크립트

set -e

echo "======================================"
echo "MIDI Mixer Control - DMG 생성"
echo "======================================"
echo ""

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 앱 확인
if [ ! -d "dist/MIDI Mixer Control.app" ]; then
    echo -e "${RED}✗ 앱을 먼저 빌드해주세요: ./build_app.sh${NC}"
    exit 1
fi

# 버전 정보
VERSION="1.0.0"
DMG_NAME="MIDI-Mixer-Control-${VERSION}.dmg"

echo -e "${YELLOW}[1/4] 임시 DMG 폴더 생성...${NC}"
TEMP_DIR="temp_dmg"
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

# 앱 복사
cp -r "dist/MIDI Mixer Control.app" "$TEMP_DIR/"
echo -e "${GREEN}✓ 앱 복사 완료${NC}"

echo -e "${YELLOW}[2/4] Applications 심볼릭 링크 생성...${NC}"
ln -s /Applications "$TEMP_DIR/Applications"
echo -e "${GREEN}✓ 링크 생성 완료${NC}"

echo -e "${YELLOW}[3/4] DMG 이미지 생성...${NC}"
# 이전 DMG 제거
if [ -f "$DMG_NAME" ]; then
    rm "$DMG_NAME"
fi

# create-dmg가 설치되어 있는지 확인
if command -v create-dmg &> /dev/null; then
    # create-dmg 사용 (더 예쁜 DMG)
    create-dmg \
        --volname "MIDI Mixer Control" \
        --volicon "icon.icns" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 100 \
        --icon "MIDI Mixer Control.app" 175 120 \
        --hide-extension "MIDI Mixer Control.app" \
        --app-drop-link 425 120 \
        "$DMG_NAME" \
        "$TEMP_DIR" || {
            # create-dmg 실패 시 hdiutil 사용
            echo -e "${YELLOW}create-dmg 실패, hdiutil 사용...${NC}"
            hdiutil create -volname "MIDI Mixer Control" \
                -srcfolder "$TEMP_DIR" \
                -ov -format UDZO \
                "$DMG_NAME"
        }
else
    # create-dmg가 없으면 기본 hdiutil 사용
    echo -e "${YELLOW}create-dmg가 없습니다. 기본 DMG 생성 중...${NC}"
    echo "더 예쁜 DMG를 원하시면: brew install create-dmg"
    
    hdiutil create -volname "MIDI Mixer Control" \
        -srcfolder "$TEMP_DIR" \
        -ov -format UDZO \
        "$DMG_NAME"
fi

echo -e "${GREEN}✓ DMG 생성 완료${NC}"

echo -e "${YELLOW}[4/4] 정리...${NC}"
rm -rf "$TEMP_DIR"
echo -e "${GREEN}✓ 정리 완료${NC}"

# DMG 크기 확인
dmg_size=$(du -sh "$DMG_NAME" | awk '{print $1}')

echo ""
echo "======================================"
echo -e "${GREEN}DMG 생성 완료!${NC}"
echo "======================================"
echo ""
echo "파일: $DMG_NAME"
echo "크기: $dmg_size"
echo "위치: $(pwd)/$DMG_NAME"
echo ""
echo "이 DMG 파일을 다른 사람들과 공유할 수 있습니다."
echo "사용자는 DMG를 열고 앱을 Applications 폴더로 드래그하면 됩니다."
echo ""

# DMG 열기 옵션
read -p "지금 DMG를 열어보시겠습니까? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    open "$DMG_NAME"
fi

