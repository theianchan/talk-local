# Push to Talk macOS App

A native macOS menu bar application for push-to-talk voice transcription using whisper.cpp.

## Features

- **Menu Bar App**: Runs in the menu bar, no terminal window needed
- **Push-to-Talk**: Press Command+. to start/stop recording
- **Model Selection**: Choose between different Whisper models from the menu
- **Status Indicators**: Visual feedback for recording and processing states
- **Native Notifications**: macOS notifications for transcription results
- **Auto-Type**: Transcribed text is automatically typed at cursor position

## Prerequisites

1. **Build whisper.cpp** (if not already done):
   ```bash
   cd whisper.cpp
   mkdir build && cd build
   cmake ..
   make
   cd ../..
   ```

2. **Download models** (if not already done):
   ```bash
   cd whisper.cpp
   ./models/download-ggml-model.sh tiny.en
   ./models/download-ggml-model.sh base.en
   cd ..
   ```

## Running the App

### Option 1: Terminal Alias (Recommended)
Add this alias to your `~/.zshrc` or `~/.bash_profile`:
```bash
alias t="cd ~/code/talk && python push_to_talk_app.py"
```

Then simply type `t` in any terminal to start the app.

### Option 2: Direct Run
```bash
python push_to_talk_app.py
```

### Option 3: Build App Bundle (if py2app available)
```bash
./build_app.sh
open "dist/Push to Talk.app"
```

## First Run Permissions

On first run, macOS will ask for permissions:

1. **Microphone Access**: Required for recording audio
2. **Accessibility Access**: Required for typing transcribed text
   - Go to System Preferences → Security & Privacy → Privacy → Accessibility
   - Add and enable "Push to Talk.app"

## Usage

1. The app runs in the menu bar (look for "Push to Talk" in the top-right)
2. Press **Command+.** to start recording
3. Press **Command+.** again to stop and transcribe
4. The transcribed text will be typed at your cursor position

## Menu Options

- **Status**: Shows current app state (Ready, Recording, Processing)
- **Model**: Select which Whisper model to use
  - tiny.en (fastest, least accurate)
  - base.en (balanced)
  - small.en (slower, more accurate)
  - medium.en (slowest, most accurate)
- **About**: App information
- **Quit**: Exit the application

## Troubleshooting

- **"Model not found" error**: Make sure you've downloaded the models
- **No transcription**: Check microphone permissions in System Preferences
- **Text not typing**: Check accessibility permissions
- **App doesn't appear**: Look in the menu bar, not the dock

## Development

To run in development mode:
```bash
python push_to_talk_app.py
```

To modify and rebuild:
1. Edit `push_to_talk_app.py`
2. Run `./build_app.sh`
3. Test the new build

## Distribution

For distribution to other users:
1. Code sign the app (requires Apple Developer certificate)
2. Create a DMG installer
3. Notarize the app for Gatekeeper

## Known Limitations

- Requires macOS 10.15 or later
- Models must be downloaded separately
- First run requires manual permission grants