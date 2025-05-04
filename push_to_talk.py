#!/usr/bin/env python3
"""
Push-to-Talk Transcription Tool using whisper.cpp

This tool records audio when a hotkey is pressed, transcribes it when pressed again,
and types the transcribed text at the current cursor position.

Default hotkey: Command+.
"""

import sys
import os
import threading
import time
import wave
import tempfile
import subprocess
import numpy as np
import pyaudio
from pynput import keyboard
from pynput.keyboard import Controller, Key

# Configuration
HOTKEY_COMBO = {Key.cmd, keyboard.KeyCode.from_char('.')}
WHISPER_MODEL_PATH = "whisper.cpp/models/ggml-tiny.en.bin"
WHISPER_EXECUTABLE = "whisper.cpp/build/bin/whisper-cli"
SAMPLE_RATE = 16000
CHUNK_SIZE = 512
CHANNELS = 1

class PushToTalk:
    def __init__(self):
        self.is_recording = False
        self.recording_thread = None
        self.audio_data = []
        self.current_keys = set()
        self.keyboard_controller = Controller()
        self.audio = pyaudio.PyAudio()
        
        # Check if whisper.cpp executable exists
        if not os.path.exists(WHISPER_EXECUTABLE):
            print(f"Error: Whisper executable not found at {WHISPER_EXECUTABLE}")
            print("Please build whisper.cpp first.")
            sys.exit(1)
            
        # Check if model exists
        if not os.path.exists(WHISPER_MODEL_PATH):
            print(f"Error: Model not found at {WHISPER_MODEL_PATH}")
            print("Please download the model first.")
            sys.exit(1)

    def record_audio(self):
        """Record audio while the hotkey is held down."""
        self.is_recording = True
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE
        )
        
        self.audio_data = []
        
        try:
            while self.is_recording:
                chunk = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                self.audio_data.append(chunk)
        except Exception as e:
            print(f"Recording error: {e}")
        finally:
            stream.stop_stream()
            stream.close()

    def start_recording(self):
        """Start recording audio in a separate thread."""
        if not self.is_recording:
            self.recording_thread = threading.Thread(target=self.record_audio)
            self.recording_thread.start()
            print("Recording started...")

    def stop_recording(self):
        """Stop recording and process the audio."""
        if self.is_recording:
            self.is_recording = False
            self.recording_thread.join()
            print("Recording stopped. Processing...")
            
            # Save audio to temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                with wave.open(temp_wav.name, 'wb') as wf:
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
                    wf.setframerate(SAMPLE_RATE)
                    wf.writeframes(b''.join(self.audio_data))
                
                # Process with whisper.cpp
                try:
                    result = subprocess.run([
                        WHISPER_EXECUTABLE,
                        "-m", WHISPER_MODEL_PATH,
                        "-f", temp_wav.name,
                        "-nt",  # no timestamps
                        "-np"   # no prints (except results)
                    ], capture_output=True, text=True)
                    
                    # Extract transcribed text (skip the first lines with system info)
                    lines = result.stdout.strip().split('\n')
                    text = ""
                    for line in lines:
                        if line and not (line.startswith('whisper_') or line.startswith('system_info') 
                                       or line.startswith('main:') or line.startswith('[') 
                                       or ':' in line[:10]):
                            text += line.strip() + " "
                    
                    text = text.strip()
                    
                    if text:
                        print(f"Transcribed: {text}")
                        # Type the transcribed text
                        self.keyboard_controller.type(text)
                    else:
                        print("No transcription available.")
                    
                except Exception as e:
                    print(f"Transcription error: {e}")
                finally:
                    # Clean up the temporary file
                    os.unlink(temp_wav.name)

    def on_press(self, key):
        """Handle key press events."""
        try:
            self.current_keys.add(key)
            if self.current_keys == HOTKEY_COMBO:
                # Toggle recording on hotkey press
                if not self.is_recording:
                    self.start_recording()
                else:
                    self.stop_recording()
        except AttributeError:
            # Handle special keys that don't have a char representation
            pass

    def on_release(self, key):
        """Handle key release events."""
        try:
            self.current_keys.discard(key)
        except AttributeError:
            pass

    def run(self):
        """Start the push-to-talk service."""
        print(f"Push-to-Talk service started.")
        print(f"Press Command+. to start recording.")
        print(f"Press Command+. again to stop and transcribe.")
        print(f"Press Ctrl+C to exit.")
        
        with keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        ) as listener:
            try:
                listener.join()
            except KeyboardInterrupt:
                print("\nExiting...")
                if self.is_recording:
                    self.stop_recording()
                self.audio.terminate()

if __name__ == "__main__":
    ptt = PushToTalk()
    ptt.run()