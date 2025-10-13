#!/bin/bash
# macOS 앱 빌드 스크립트

set -e  # 에러 발생 시 중단

echo "======================================"
echo "MIDI Mixer Control - macOS 앱 빌드"
echo "======================================"
echo ""

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Python 버전 확인
echo -e "${YELLOW}[1/7] Python 버전 확인...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python 버전: $python_version"

# 2. py2app 설치 확인
echo -e "${YELLOW}[2/7] py2app 설치 확인...${NC}"
if ! python3 -c "import py2app" 2>/dev/null; then
    echo "py2app이 설치되지 않았습니다. 설치 중..."
    pip3 install py2app
fi
echo -e "${GREEN}✓ py2app 설치됨${NC}"

# 3. 의존성 설치 확인
echo -e "${YELLOW}[3/7] 의존성 설치 확인...${NC}"
pip3 install -r requirements.txt
echo -e "${GREEN}✓ 의존성 설치 완료${NC}"

# 4. 이전 빌드 정리
echo -e "${YELLOW}[4/7] 이전 빌드 정리...${NC}"
if [ -d "build" ]; then
    rm -rf build/
fi
if [ -d "dist" ]; then
    rm -rf dist/
fi
echo -e "${GREEN}✓ 정리 완료${NC}"

# 5. 앱 빌드
echo -e "${YELLOW}[5/7] 앱 빌드 중...${NC}"
python3 setup.py py2app

if [ ! -d "dist/MIDI Mixer Control.app" ]; then
    echo -e "${RED}✗ 빌드 실패!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 빌드 완료${NC}"

# 6. 앱 크기 확인
echo -e "${YELLOW}[6/7] 빌드된 앱 정보...${NC}"
app_size=$(du -sh "dist/MIDI Mixer Control.app" | awk '{print $1}')
echo "앱 크기: $app_size"
echo "위치: $(pwd)/dist/MIDI Mixer Control.app"

# 7. 테스트 실행 옵션
echo -e "${YELLOW}[7/7] 빌드 완료!${NC}"
echo ""
echo "======================================"
echo -e "${GREEN}성공적으로 빌드되었습니다!${NC}"
echo "======================================"
echo ""
echo "다음 단계:"
echo "1. 앱 테스트: open 'dist/MIDI Mixer Control.app'"
echo "2. Applications 폴더로 복사: cp -r 'dist/MIDI Mixer Control.app' /Applications/"
echo "3. DMG 생성 (선택): ./create_dmg.sh"
echo ""

# 테스트 실행 여부 묻기
read -p "지금 앱을 실행해보시겠습니까? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    open "dist/MIDI Mixer Control.app"
fi

