#!/usr/bin/env python3
"""
Push-to-Talk Transcription Menu Bar App using whisper.cpp

This is a macOS menu bar application that records audio when a hotkey is pressed,
transcribes it when pressed again, and types the transcribed text at the current cursor position.

Default hotkey: Command+.
"""

import sys
import os
import threading
import time
import wave
import tempfile
import subprocess
import json
import pyaudio
import rumps
from pynput import keyboard
from pynput.keyboard import Controller, Key
from datetime import datetime
import logging
import traceback
import fcntl
import errno

# Configuration
HOTKEY_COMBO = {Key.cmd, keyboard.KeyCode.from_char('.')}
# Alternative simpler hotkey for testing
ALT_HOTKEY_COMBO = {keyboard.KeyCode.from_char('`')}  # Just backtick key
WHISPER_MODELS = {
    "tiny.en": "whisper.cpp/models/ggml-tiny.en.bin",
    "base.en": "whisper.cpp/models/ggml-base.en.bin",
    "small.en": "whisper.cpp/models/ggml-small.en.bin",
    "medium.en": "whisper.cpp/models/ggml-medium.en.bin",
}
DEFAULT_MODEL = "tiny.en"
WHISPER_EXECUTABLE = "whisper.cpp/build/bin/whisper-cli"
SAMPLE_RATE = 16000
CHUNK_SIZE = 512
CHANNELS = 1

# App configuration
APP_NAME = "Talk"
APP_ICON = None  # Will use default microphone icon

# Set up logging
LOG_FILE = os.path.expanduser("~/Library/Logs/PushToTalk.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger(__name__)

class PushToTalkApp(rumps.App):
    def __init__(self):
        super(PushToTalkApp, self).__init__(APP_NAME, icon=APP_ICON, quit_button=None)
        logger.info("Initializing Push to Talk app")
        
        # Audio recording state
        self.is_recording = False
        self.recording_thread = None
        self.audio_data = []
        self.current_keys = set()
        self.keyboard_controller = Controller()
        self.audio = None
        self.keyboard_listener = None
        self.current_model = DEFAULT_MODEL
        self.debug_mode = False
        
        # Initialize PyAudio
        try:
            self.audio = pyaudio.PyAudio()
            logger.info(f"PyAudio initialized successfully. Found {self.audio.get_device_count()} audio devices")
        except Exception as e:
            logger.error(f"Failed to initialize PyAudio: {e}")
            rumps.alert("Audio Error", "Failed to initialize audio system. Please check your audio devices.")
            sys.exit(1)
        
        # Menu items
        self.menu = [
            rumps.MenuItem(f"Status: Ready", callback=None),
            rumps.separator,
            rumps.MenuItem("Start Recording (⌘.)", callback=self.toggle_recording),
            rumps.MenuItem("Cancel Recording (Esc)", callback=lambda _: self.cancel_recording()),
            rumps.separator,
            rumps.MenuItem("Model", callback=None),
            rumps.separator,
            rumps.MenuItem("Debug", callback=None),
            rumps.separator,
            rumps.MenuItem("About", callback=self.about),
            rumps.MenuItem("Quit", callback=self.quit_app)
        ]
        
        # Initially disable cancel option
        self.menu["Cancel Recording (Esc)"].enabled = False
        
        # Create debug submenu
        debug_menu = [
            rumps.MenuItem("Toggle Debug Mode", callback=self.toggle_debug),
            rumps.MenuItem("View Logs", callback=self.view_logs),
            rumps.MenuItem("Clear Logs", callback=self.clear_logs),
            rumps.MenuItem("Test Audio", callback=self.test_audio),
            rumps.MenuItem("Test Hotkey Detection", callback=self.test_hotkey),
            rumps.separator,
            rumps.MenuItem("Kill All Instances", callback=self.kill_all_instances)
        ]
        self.menu["Debug"].update(debug_menu)
        
        # Create model submenu
        model_menu = []
        for model_name in WHISPER_MODELS.keys():
            item = rumps.MenuItem(
                model_name, 
                callback=lambda sender, model=model_name: self.set_model(model)
            )
            if model_name == self.current_model:
                item.state = True
            model_menu.append(item)
        self.menu["Model"].update(model_menu)
        
        # Update status
        self.update_status("Ready")
        
        # Check prerequisites
        if not self.check_prerequisites():
            rumps.alert("Missing Prerequisites", 
                       "Please ensure whisper.cpp is built and models are downloaded.")
            sys.exit(1)
        
        # Start keyboard listener
        self.start_keyboard_listener()
        
        # Test notifications
        self.notifications_available = self.test_notifications()
    
    def check_prerequisites(self):
        """Check if whisper.cpp executable and models exist."""
        logger.info("Checking prerequisites...")
        if not os.path.exists(WHISPER_EXECUTABLE):
            logger.error(f"Whisper executable not found at: {WHISPER_EXECUTABLE}")
            return False
        else:
            logger.info(f"Found whisper executable at: {WHISPER_EXECUTABLE}")
            
        model_path = WHISPER_MODELS[self.current_model]
        if not os.path.exists(model_path):
            logger.error(f"Model not found at: {model_path}")
            return False
        else:
            logger.info(f"Found model at: {model_path}")
            
        return True
    
    def test_notifications(self):
        """Test if notifications are available."""
        try:
            # Try to create the Info.plist if it doesn't exist
            plist_path = os.path.join(os.path.dirname(sys.executable), "Info.plist")
            if not os.path.exists(plist_path):
                logger.info(f"Creating Info.plist at {plist_path}")
                subprocess.run([
                    "/usr/libexec/PlistBuddy",
                    "-c", "Add :CFBundleIdentifier string com.pushtotak.app",
                    plist_path
                ], capture_output=True)
            return True
        except Exception as e:
            logger.warning(f"Notifications may not work: {e}")
            return False
    
    def show_notification(self, title, subtitle, message):
        """Show notification if available, otherwise log."""
        if self.notifications_available:
            try:
                rumps.notification(title, subtitle, message)
                return
            except Exception as e:
                logger.debug(f"Notification failed: {e}")
                self.notifications_available = False
        
        # Fallback to logging
        logger.info(f"NOTIFICATION: {title} - {message}")
    
    def update_status(self, status):
        """Update the status menu item."""
        self.menu["Status: Ready"].title = f"Status: {status}"
        
        # Update icon based on status
        if "Recording" in status:
            self.title = "🔴 " + APP_NAME
        else:
            self.title = APP_NAME
    
    def set_model(self, model_name):
        """Set the active model."""
        # Update menu checkmarks
        for item in self.menu["Model"]:
            item.state = (item.title == model_name)
        
        self.current_model = model_name
        self.update_status(f"Model: {model_name}")
        
        # Check if model exists
        if not os.path.exists(WHISPER_MODELS[model_name]):
            rumps.alert("Model Not Found", 
                       f"Model {model_name} not found. Please download it first.")
    
    def toggle_recording(self, sender):
        """Toggle recording from menu."""
        logger.info(f"Toggle recording called. Current state: is_recording={self.is_recording}")
        try:
            if not self.is_recording:
                self.start_recording()
            else:
                self.stop_recording()
        except Exception as e:
            logger.error(f"Error in toggle_recording: {e}\n{traceback.format_exc()}")
            rumps.alert("Error", f"Recording error: {str(e)}")
    
    def toggle_debug(self, sender):
        """Toggle debug mode."""
        self.debug_mode = not self.debug_mode
        sender.state = self.debug_mode
        logger.info(f"Debug mode: {self.debug_mode}")
        if self.debug_mode:
            self.show_notification("Debug Mode", "", "Debug mode enabled. Check logs for details.")
    
    def view_logs(self, _):
        """Open log file."""
        subprocess.run(["open", LOG_FILE])
    
    def clear_logs(self, _):
        """Clear log file."""
        try:
            with open(LOG_FILE, 'w') as f:
                f.write("")
            logger.info("Logs cleared")
            self.show_notification("Logs Cleared", "", "Log file has been cleared")
        except Exception as e:
            logger.error(f"Failed to clear logs: {e}")
    
    def test_audio(self, _):
        """Test audio recording."""
        logger.info("Testing audio...")
        try:
            # List audio devices
            device_count = self.audio.get_device_count()
            logger.info(f"Found {device_count} audio devices:")
            
            for i in range(device_count):
                info = self.audio.get_device_info_by_index(i)
                logger.info(f"  Device {i}: {info['name']} - Inputs: {info['maxInputChannels']}")
            
            # Try to open a stream
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE
            )
            
            logger.info("Audio stream test successful")
            stream.close()
            
            rumps.alert("Audio Test", "Audio system is working correctly!")
            
        except Exception as e:
            logger.error(f"Audio test failed: {e}\n{traceback.format_exc()}")
            rumps.alert("Audio Test Failed", f"Error: {str(e)}")
    
    def test_hotkey(self, _):
        """Test hotkey detection."""
        logger.info("Testing hotkey detection...")
        
        # Test if we have accessibility permissions
        try:
            # Simple test: try to create a keyboard listener
            test_keys = []
            
            def test_press(key):
                test_keys.append(str(key))
                return False  # Stop listener
            
            # Try to create a test listener
            test_listener = keyboard.Listener(on_press=test_press)
            test_listener.start()
            test_listener.stop()
            
            # If we get here, basic keyboard monitoring works
            msg = (
                "Keyboard monitoring is working!\n\n"
                "To test the hotkey:\n"
                "1. Enable Debug Mode\n"
                "2. Press Command+.\n" 
                "3. Check View Logs for results\n\n"
                "Note: If hotkey doesn't work, check:\n"
                "- System Settings → Privacy & Security → Accessibility\n"
                "- Add Terminal to the allowed apps list"
            )
            
            rumps.alert("Hotkey Test", msg)
            logger.info("Keyboard listener test successful")
            
        except Exception as e:
            logger.error(f"Keyboard test failed: {e}\n{traceback.format_exc()}")
            msg = (
                "❌ Keyboard monitoring failed!\n\n"
                "Please grant accessibility permissions:\n"
                "1. System Settings → Privacy & Security → Accessibility\n"
                "2. Click the + button\n"
                "3. Add Terminal (or your terminal app)\n"
                "4. Restart this app"
            )
            rumps.alert("Permission Required", msg)
    
    def kill_all_instances(self, _):
        """Kill all running instances of the app."""
        try:
            # Get current process ID
            current_pid = os.getpid()
            
            # Find all push_to_talk_app.py processes
            result = subprocess.run(
                ["pgrep", "-f", "push_to_talk_app.py"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                killed = []
                
                for pid in pids:
                    if pid and int(pid) != current_pid:
                        try:
                            os.kill(int(pid), 9)
                            killed.append(pid)
                        except:
                            pass
                
                if killed:
                    msg = f"Killed {len(killed)} other instance(s)"
                    logger.info(f"Killed PIDs: {killed}")
                else:
                    msg = "No other instances found"
            else:
                msg = "No other instances found"
            
            rumps.alert("Kill All Instances", msg)
            
        except Exception as e:
            logger.error(f"Failed to kill instances: {e}")
            rumps.alert("Error", f"Failed to kill instances: {str(e)}")
    
    def about(self, _):
        """Show about dialog."""
        rumps.alert(
            "Push to Talk Transcription",
            "A macOS menu bar app for voice transcription.\n\n"
            f"Hotkey: ⌘. (Command+Period)\n"
            f"Alternative: ` (Backtick)\n"
            f"Current Model: {self.current_model}\n\n"
            "Powered by whisper.cpp"
        )
    
    def quit_app(self, _):
        """Quit the application."""
        if self.is_recording:
            self.stop_recording()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        self.audio.terminate()
        rumps.quit_application()
    
    def record_audio(self):
        """Record audio while the hotkey is held down."""
        logger.info("Starting audio recording thread")
        self.is_recording = True
        stream = None
        
        try:
            logger.debug(f"Opening audio stream: format=paInt16, channels={CHANNELS}, rate={SAMPLE_RATE}")
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE
            )
            logger.info("Audio stream opened successfully")
            
            self.audio_data = []
            
            start_time = datetime.now()
            while self.is_recording:
                chunk = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                self.audio_data.append(chunk)
                
                # Update recording duration (skip UI update from background thread)
                duration = (datetime.now() - start_time).seconds
                # Don't update UI from background thread - it causes crashes
                # Just log the duration
                if self.debug_mode and duration % 5 == 0:
                    logger.debug(f"Recording duration: {duration}s")
                
                if self.debug_mode and len(self.audio_data) % 10 == 0:
                    logger.debug(f"Recorded {len(self.audio_data)} chunks, {duration}s elapsed")
                
        except Exception as e:
            logger.error(f"Recording error: {e}\n{traceback.format_exc()}")
            self.show_notification("Recording Error", "", str(e))
        finally:
            if stream:
                logger.info("Closing audio stream")
                stream.stop_stream()
                stream.close()
            logger.info(f"Recording thread ended. Collected {len(self.audio_data)} audio chunks")
    
    def start_recording(self):
        """Start recording audio in a separate thread."""
        logger.info("start_recording called")
        if not self.is_recording:
            logger.info("Starting new recording thread")
            # Update UI before starting thread
            self.update_status("Recording...")
            self.menu["Start Recording (⌘.)"].title = "Stop Recording (⌘.)"
            self.menu["Cancel Recording (Esc)"].enabled = True
            
            self.recording_thread = threading.Thread(target=self.record_audio)
            self.recording_thread.start()
            self.show_notification("Recording Started", "", "Press ⌘. to stop or Esc to cancel")
        else:
            logger.warning("start_recording called but already recording!")
    
    def cancel_recording(self):
        """Cancel recording without transcription."""
        logger.info("cancel_recording called")
        if self.is_recording:
            logger.info("Cancelling recording...")
            self.is_recording = False
            self.recording_thread.join()
            logger.info(f"Recording cancelled. Discarded {len(self.audio_data)} audio chunks")
            
            # Reset UI
            self.update_status("Cancelled")
            # The menu item key doesn't change when we change the title
            self.menu["Start Recording (⌘.)"].title = "Start Recording (⌘.)"
            self.menu["Cancel Recording (Esc)"].enabled = False
            
            self.show_notification("Recording Cancelled", "", "No text was transcribed")
            
            # Clear audio data
            self.audio_data = []
            
            # Reset status to Ready after a moment
            self.update_status("Ready")
        else:
            logger.warning("cancel_recording called but not recording!")
    
    def stop_recording(self):
        """Stop recording and process the audio."""
        logger.info("stop_recording called")
        if self.is_recording:
            logger.info("Stopping recording...")
            self.is_recording = False
            self.recording_thread.join()
            logger.info(f"Recording thread joined. Audio data size: {len(self.audio_data)} chunks")
            
            self.update_status("Processing...")
            
            # Save audio to temporary WAV file
            temp_wav_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                    temp_wav_path = temp_wav.name
                    logger.info(f"Creating WAV file at: {temp_wav_path}")
                    
                    with wave.open(temp_wav.name, 'wb') as wf:
                        wf.setnchannels(CHANNELS)
                        wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
                        wf.setframerate(SAMPLE_RATE)
                        audio_bytes = b''.join(self.audio_data)
                        wf.writeframes(audio_bytes)
                        logger.info(f"Wrote {len(audio_bytes)} bytes to WAV file")
                
                # Process with whisper.cpp
                model_path = WHISPER_MODELS[self.current_model]
                cmd = [
                    WHISPER_EXECUTABLE,
                    "-m", model_path,
                    "-f", temp_wav_path,
                    "-nt",  # no timestamps
                    "-np"   # no prints (except results)
                ]
                
                logger.info(f"Running whisper command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                logger.debug(f"Whisper return code: {result.returncode}")
                logger.debug(f"Whisper stdout: {result.stdout}")
                if result.stderr:
                    logger.debug(f"Whisper stderr: {result.stderr}")
                
                # Extract transcribed text
                lines = result.stdout.strip().split('\n')
                text = ""
                for line in lines:
                    if line and not (line.startswith('whisper_') or line.startswith('system_info') 
                                   or line.startswith('main:') or line.startswith('[') 
                                   or ':' in line[:10]):
                        text += line.strip() + " "
                
                text = text.strip()
                logger.info(f"Transcription result: '{text}'")
                
                if text:
                    # Type the transcribed text
                    self.keyboard_controller.type(text)
                    self.update_status("Transcribed")
                    self.show_notification("Transcription Complete", "", text[:100] + "..." if len(text) > 100 else text)
                else:
                    self.update_status("No transcription")
                    self.show_notification("No Transcription", "", "No speech detected")
                    
            except Exception as e:
                logger.error(f"Error in stop_recording: {e}\n{traceback.format_exc()}")
                self.update_status("Error")
                self.show_notification("Transcription Error", "", str(e))
            finally:
                # Clean up the temporary file
                if temp_wav_path and os.path.exists(temp_wav_path):
                    logger.info(f"Cleaning up temp file: {temp_wav_path}")
                    os.unlink(temp_wav_path)
                
                # Reset status after a delay
                # Don't use threading.Timer as it creates a background thread
                # Just reset immediately for now
                self.update_status("Ready")
                self.menu["Start Recording (⌘.)"].title = "Start Recording (⌘.)"
                self.menu["Cancel Recording (Esc)"].enabled = False
        else:
            logger.warning("stop_recording called but not recording!")
    
    def on_press(self, key):
        """Handle key press events."""
        try:
            # Check for Escape key first (single key, not a combination)
            if key == Key.esc and self.is_recording:
                logger.info("Escape key pressed while recording - cancelling")
                self.cancel_recording()
                return
            
            self.current_keys.add(key)
            if self.debug_mode:
                logger.debug(f"Key pressed: {key}, current keys: {self.current_keys}")
            
            # Check for hotkey
            if self.current_keys == HOTKEY_COMBO:
                logger.info("Hotkey combo detected!")
                # Toggle recording on hotkey press
                if not self.is_recording:
                    self.start_recording()
                else:
                    self.stop_recording()
            elif self.current_keys == ALT_HOTKEY_COMBO:
                logger.info("Alternative hotkey (`) detected!")
                # Toggle recording on alternative hotkey
                if not self.is_recording:
                    self.start_recording()
                else:
                    self.stop_recording()
            elif self.debug_mode and len(self.current_keys) >= 1:
                # Log all key presses in debug mode
                logger.debug(f"Keys pressed: {self.current_keys}, Expected: {HOTKEY_COMBO} or {ALT_HOTKEY_COMBO}")
        except AttributeError:
            pass
        except Exception as e:
            logger.error(f"Error in on_press: {e}\n{traceback.format_exc()}")
    
    def on_release(self, key):
        """Handle key release events."""
        try:
            self.current_keys.discard(key)
        except AttributeError:
            pass
    
    def start_keyboard_listener(self):
        """Start the keyboard listener in a separate thread."""
        logger.info("Starting keyboard listener for hotkey: Command+.")
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.keyboard_listener.start()
        logger.info("Keyboard listener started")

def acquire_lock():
    """Ensure only one instance of the app is running."""
    lock_file = os.path.expanduser("~/.push_to_talk.lock")
    try:
        # Try to acquire an exclusive lock
        lock_fd = os.open(lock_file, os.O_CREAT | os.O_WRONLY)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_fd
    except IOError as e:
        if e.errno == errno.EAGAIN or e.errno == errno.EACCES:
            # Another instance is running
            return None
        else:
            raise

if __name__ == "__main__":
    logger.info("="*50)
    logger.info("Push to Talk app starting...")
    logger.info(f"Log file: {LOG_FILE}")
    logger.info(f"Python version: {sys.version}")
    logger.info("="*50)
    
    # Check for existing instance
    lock_fd = acquire_lock()
    if lock_fd is None:
        logger.warning("Another instance is already running!")
        print("Talk is already running. Check your menu bar.")
        # Show a notification if possible
        try:
            subprocess.run([
                "osascript", "-e",
                'display notification "Talk is already running in the menu bar" with title "Talk"'
            ])
        except:
            pass
        sys.exit(0)
    
    try:
        app = PushToTalkApp()
        app.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}\n{traceback.format_exc()}")
        raise
    finally:
        # Release the lock when exiting
        if lock_fd:
            os.close(lock_fd)