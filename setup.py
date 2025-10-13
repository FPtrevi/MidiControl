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
    'excludes': ['matplotlib', 'numpy', 'scipy', 'pandas'],
    'plist': {
        'CFBundleName': 'MIDI Mixer Control',
        'CFBundleDisplayName': 'MIDI Mixer Control',
        'CFBundleIdentifier': 'com.mcontrol.midimixer',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2025 All Rights Reserved',
        'LSMinimumSystemVersion': '10.13.0',
        'NSHighResolutionCapable': True,
    },
    'iconfile': None,  # 아이콘 파일이 있다면 경로 지정 (예: 'icon.icns')
    'resources': [],
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

