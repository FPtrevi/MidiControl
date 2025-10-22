"""
Setup script for creating macOS .app bundle with py2app
"""
from setuptools import setup, find_packages

APP = ['app.py']
DATA_FILES = []

# Optimized py2app options for better performance and smaller bundle size
OPTIONS = {
    'argv_emulation': False,
    'packages': ['mido', 'rtmidi', 'tkinter', 'pythonosc', 'packaging'],
    'includes': [
        'controller',
        'model',
        'view',
        'config',
        'utils',
    ],
    'excludes': [
        # Scientific computing libraries
        'matplotlib', 'numpy', 'scipy', 'pandas', 'sympy',
        # Image processing libraries
        'PIL', 'PIL.Image', 'PIL.ImageTk', 'Pillow',
        # Web frameworks
        'flask', 'django', 'tornado', 'fastapi',
        # Database libraries
        'sqlite3', 'pymongo', 'psycopg2', 'mysql',
        # Testing frameworks
        'test', 'tests', 'unittest', 'pytest', 'nose',
        # Development tools
        'black', 'mypy', 'flake8', 'pylint',
        # Other unnecessary modules
        'http', 'html', 'setuptools', 'extern', 'vendor', 'helpers', 'distutils', 'wheel', 'pip', 'ensurepip', 'importlib_metadata', 'site', 'pkg_resources',
        'concurrent', 'asyncio',
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
        'LSUIElement': False,  # Show in dock
        'NSRequiresAquaSystemAppearance': False,
    },
    'iconfile': None,  # 아이콘 파일이 있다면 경로 지정 (예: 'icon.icns')
    'resources': [],
    'optimize': 2,  # Python 최적화 레벨
    'strip': True,  # 디버그 심볼 제거
    'compressed': True,  # 압축된 번들 생성
    'dist_dir': 'dist',  # 배포 디렉토리
}

setup(
    name='MIDI Mixer Control',
    version='1.0.1',
    description='MIDI mixer control application for DM3 and Qu-5/6/7 mixers',
    author='MControl',
    author_email='',
    url='',
    app=APP,
    data_files=DATA_FILES,
    packages=find_packages(),
    options={'py2app': OPTIONS},
    setup_requires=['py2app>=0.13'],
    install_requires=[
        'mido>=1.2.10,<2.0.0',
        'python-rtmidi>=1.4.9,<2.0.0',
        'python-osc>=1.8.1,<2.0.0',
    ],
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Sound/Audio :: MIDI',
    ],
)

