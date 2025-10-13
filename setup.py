"""
Setup script for creating macOS .app bundle with py2app
"""
from setuptools import setup

APP = ['app.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['mido', 'rtmidi', 'tkinter'],
    'includes': [
        'controller',
        'model',
        'view',
        'config',
        'utils',
    ],
    'excludes': [
        'matplotlib', 'numpy', 'scipy', 'pandas',
        'PIL', 'PIL.Image', 'PIL.ImageTk',  # 이미지 라이브러리 제외
        'test', 'tests', 'unittest',  # 테스트 모듈 제외
        'distutils', 'setuptools',  # 빌드 도구 제외
        'email', 'http', 'urllib',  # 네트워크 관련 제외 (필요시 추가)
    ],
    'plist': {
        'CFBundleName': 'MIDI Mixer Control',
        'CFBundleDisplayName': 'MIDI Mixer Control',
        'CFBundleIdentifier': 'com.mcontrol.midimixer',
        'CFBundleVersion': '1.0.1',
        'CFBundleShortVersionString': '1.0.1',
        'NSHumanReadableCopyright': 'Copyright © 2025 All Rights Reserved',
        'LSMinimumSystemVersion': '10.13.0',
        'NSHighResolutionCapable': True,
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'NSSupportsAutomaticTermination': True,
        'NSSupportsSuddenTermination': True,
    },
    'iconfile': None,  # 아이콘 파일이 있다면 경로 지정 (예: 'icon.icns')
    'resources': [],
    'optimize': 2,  # Python 최적화 레벨
    'strip': True,  # 디버그 심볼 제거
}

setup(
    name='MIDI Mixer Control',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    install_requires=[
        'mido>=1.2.10',
        'python-rtmidi>=1.4.9',
    ],
)

