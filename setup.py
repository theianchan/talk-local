"""
py2app setup script for Push to Talk macOS app

Usage:
    python setup.py py2app
"""

from setuptools import setup
import os
import shutil

APP = ['talk.py']
DATA_FILES = []

# Include whisper.cpp executable and models
WHISPER_FILES = [
    ('whisper.cpp/build/bin', ['whisper.cpp/build/bin/whisper-cli']),
    ('whisper.cpp/models', [
        'whisper.cpp/models/ggml-tiny.en.bin',
        'whisper.cpp/models/ggml-base.en.bin',
        # Add more models as needed
    ])
]

# Filter out non-existent files
for dest, files in WHISPER_FILES:
    existing_files = [f for f in files if os.path.exists(f)]
    if existing_files:
        DATA_FILES.append((dest, existing_files))

OPTIONS = {
    'argv_emulation': False,
    'iconfile': None,  # Will add icon later
    'plist': {
        'CFBundleName': 'Talk',
        'CFBundleDisplayName': 'Talk',
        'CFBundleIdentifier': 'com.talk.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSUIElement': True,  # Hide from dock (menu bar app)
        'NSMicrophoneUsageDescription': 'Push to Talk needs access to your microphone to record audio for transcription.',
        'NSAppleEventsUsageDescription': 'Push to Talk needs accessibility permissions to type transcribed text.',
        'LSMinimumSystemVersion': '10.15',
    },
    'packages': [
        'pyaudio',
        'pynput',
        'numpy',
        'rumps',
        'pyobjc',
    ],
    'includes': [
        'pyobjc',
        'pyobjc.objc',
        'pyobjc._objc',
        'Quartz',
        'ApplicationServices',
        'Cocoa',
    ],
    'excludes': [
        'matplotlib',
        'scipy',
        'pandas',
        'PIL',
        'tkinter',
    ],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)