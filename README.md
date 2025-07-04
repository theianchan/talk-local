# Talk - Push-to-Talk Voice Transcription Menu Bar App

A native macOS menu bar application for push-to-talk voice transcription using whisper.cpp. This tool records audio when you press a keyboard shortcut and automatically types the transcribed text at your current cursor position.

## Features

- **Menu Bar App**: Runs in the menu bar, no terminal window needed
- **Push-to-Talk**: Press Command+. to start/stop recording
- **Escape to Cancel**: Press Escape while recording to cancel without transcribing
- **Model Selection**: Choose between different Whisper models from the menu
- **Status Indicators**: Visual feedback for recording and processing states
- **Native Notifications**: macOS notifications for transcription results
- **Auto-Type**: Transcribed text is automatically typed at cursor position
- **Privacy-focused**: All processing happens locally on your device
- **Works system-wide**: Can be used in any application

## Prerequisites

- macOS (tested on Apple Silicon)
- Python 3.11 or later
- Homebrew (for installing dependencies)
- Xcode command line tools

## Quick Setup (Convenience Command)

To run the app by simply typing `t`, add this alias to your shell configuration:

```bash
echo 'alias t="cd ~/code/talk && python3 talk.py"' >> ~/.zshrc
source ~/.zshrc
```

Now you can start the app anytime by typing `t` in your terminal!

## Installation

1. **Clone whisper.cpp repository**:
   ```bash
   git clone https://github.com/ggml-org/whisper.cpp.git
   ```

2. **Build whisper.cpp**:
   ```bash
   brew install cmake
   cd whisper.cpp
   cmake -B build
   cmake --build build --config Release -j
   ```

3. **Download the tiny.en model**:
   ```bash
   cd models
   ./download-ggml-model.sh tiny.en
   cd ..
   ```

4. **Install system dependencies**:
   ```bash
   brew install portaudio
   ```

5. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

The app uses the following default configuration:
- **Hotkey**: Command+. (press to toggle recording)
- **Cancel**: Escape key (while recording)
- **Default Model**: tiny.en (fastest model for quick transcriptions)
- **Sample rate**: 16,000 Hz
- **Channels**: Mono

### Available Models
- **tiny.en**: Fastest, least accurate (default)
- **small.en**: Balanced speed and accuracy
- **medium.en**: Slower, more accurate

To use additional models:
1. Download the desired model:
   ```bash
   cd whisper.cpp/models
   ./download-ggml-model.sh small.en
   ./download-ggml-model.sh medium.en
   ```
2. Edit `WHISPER_MODELS` in `talk.py` to uncomment the model
3. Select the model from the menu bar app's Model menu

## Usage

1. Start the app:
   ```bash
   t
   ```
   
   Or run directly:
   ```bash
   python3 talk.py
   ```

2. The app icon will appear in your menu bar (top-right of screen).

3. To transcribe:
   - Position your cursor where you want the text to appear
   - Press **Command+.** to start recording (menu bar icon turns red)
   - Speak clearly into your microphone
   - Press **Command+.** again to stop recording and transcribe
   - Or press **Escape** to cancel recording without transcribing
   - The transcribed text will be typed at your cursor position

4. To quit: Click the menu bar icon → Quit

### Menu Options

- **Status**: Shows current app state (Ready, Recording, Processing)
- **Start/Stop Recording**: Alternative to hotkey
- **Cancel Recording**: Available while recording (or press Escape)
- **Model**: Select which Whisper model to use
- **Debug**: Troubleshooting tools
- **About**: App information
- **Quit**: Exit the application

## macOS Permissions

The first time you run this tool, macOS will ask for:

1. **Microphone Access**: Required for recording audio
2. **Accessibility Access**: Required for keyboard monitoring and typing text
   - Go to System Settings → Privacy & Security → Accessibility
   - Add Terminal (or your terminal app) to the allowed list
   - Enable the toggle for your terminal

### Troubleshooting Permissions

If hotkeys don't work:
1. Open the Debug menu in the app
2. Click "Test Hotkey Detection"
3. Follow the instructions in the dialog

## Troubleshooting

1. **App doesn't appear in menu bar**: Look in the top-right corner, not the dock
2. **"Another instance is already running"**: The app prevents duplicates. Check your menu bar for existing instance
3. **Hotkey doesn't work**: 
   - Grant accessibility permissions to Terminal in System Settings
   - Use Debug → Test Hotkey Detection
   - Try using the menu button instead
4. **"Model not found"**: Download the model using the whisper.cpp download script
5. **No audio recorded**: Check microphone permissions in System Settings
6. **Text not typing**: Ensure accessibility permissions are granted
7. **Poor transcription quality**: Switch to a better model like small.en or medium.en from the Model menu

### Debug Tools

The app includes several debug features:
- **Toggle Debug Mode**: Enables detailed logging
- **View Logs**: Opens the log file (`~/Library/Logs/PushToTalk.log`)
- **Test Audio**: Verifies audio system is working
- **Test Hotkey Detection**: Checks if keyboard monitoring is working

## Performance Notes

- The tiny.en model is the fastest option for quick transcriptions
- First transcription may be slower as the model loads into memory
- Subsequent transcriptions will be faster
- For better accuracy, consider using base.en or small.en models
- Apple Silicon optimization provides significant speed improvements

## Privacy & Security

- All processing happens locally on your device
- No audio data is sent to external servers
- Temporary audio files are deleted immediately after transcription
- The tool only operates when you press the hotkey combination

## License

This tool uses:
- whisper.cpp (MIT License)
- Various Python libraries (see requirements.txt for details)

Please refer to the respective licenses for each component.