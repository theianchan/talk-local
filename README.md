# Talk Local - Push-to-Talk Voice Transcription

A local push-to-talk transcription tool for macOS using whisper.cpp, which complies with Anthropic's approved software. This tool records audio when you press a keyboard shortcut and automatically types the transcribed text at your current cursor position.

## Features

- **Hotkey-triggered recording**: Press Command+. to start/stop recording
- **Toggle recording**: No need to hold keys - press once to start, press again to stop
- **Automatic text insertion**: Transcribed text is automatically typed at your current cursor position
- **Fast local transcription**: Uses whisper.cpp with optimized Apple Silicon support
- **Privacy-focused**: All processing happens locally on your device
- **Works system-wide**: Can be used in any application

## Prerequisites

- macOS (tested on Apple Silicon)
- Python 3.11 or later
- Homebrew (for installing dependencies)
- Xcode command line tools

## Quick Setup (Convenience Command)

To run the app by simply typing `talk`, add this alias to your shell configuration:

```bash
echo 'alias talk="cd /Users/ianchan/code/talk && python3 push_to_talk.py"' >> ~/.zshrc
source ~/.zshrc
```

Now you can start the app anytime by typing `talk` in your terminal!

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

The script uses the following default configuration:
- **Hotkey**: Command+. (press to toggle recording)
- **Model**: tiny.en (fastest model for quick transcriptions)
- **Sample rate**: 16,000 Hz
- **Channels**: Mono

To change the hotkey, edit the `HOTKEY_COMBO` variable in `push_to_talk.py`:
```python
HOTKEY_COMBO = {Key.cmd, keyboard.KeyCode.from_char('.')}
```

To use a different model (e.g., base.en for better accuracy):
1. Download the desired model: `cd models && ./download-ggml-model.sh base.en`
2. Update `WHISPER_MODEL_PATH` in the script to point to the new model

## Usage

1. Start the push-to-talk service:
   ```bash
   talk
   ```
   
   Or run directly:
   ```bash
   ./push_to_talk.py
   ```

2. The service will start and wait for the hotkey combination.

3. To transcribe:
   - Position your cursor where you want the text to appear
   - Press Command+. to start recording
   - Speak clearly into your microphone
   - Press Command+. again to stop recording
   - The transcribed text will be typed at your cursor position

4. Press Ctrl+C to stop the service.

## macOS Permissions

The first time you run this tool, macOS may ask for:
- Microphone access (for recording audio)
- Accessibility permissions (for simulating keyboard input)

Make sure to grant these permissions for the tool to work properly.

## Troubleshooting

1. **"Whisper executable not found"**: Make sure you built whisper.cpp successfully
2. **"Model not found"**: Download the model using the provided script
3. **No audio recorded**: Check microphone permissions in System Preferences
4. **Text not typing**: Grant accessibility permissions to Terminal/your IDE
5. **Poor transcription quality**: Try using a better model like small.en or medium.en

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