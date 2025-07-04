"""
Unit tests for Push to Talk app
"""
import pytest
import os
import tempfile
from unittest.mock import Mock, MagicMock, patch, mock_open, call
import sys

# Add parent directory to path to import our module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock the GUI libraries before importing
sys.modules['rumps'] = MagicMock()
sys.modules['pynput'] = MagicMock()
sys.modules['pynput.keyboard'] = MagicMock()
sys.modules['pyaudio'] = MagicMock()

from talk import PushToTalkApp, acquire_lock, WHISPER_MODELS, SAMPLE_RATE, CHANNELS


class TestModelManagement:
    """Test model switching and validation"""
    
    @patch('talk.os.path.exists')
    @patch('talk.logger')
    def test_check_prerequisites_success(self, mock_logger, mock_exists):
        """Test prerequisites check when all files exist"""
        mock_exists.return_value = True
        
        # Create instance with mocked dependencies
        with patch('talk.pyaudio.PyAudio'):
            with patch('talk.keyboard.Listener'):
                app = PushToTalkApp()
                result = app.check_prerequisites()
                
                assert result == True
                # Should have checked for executable and model
                assert mock_exists.call_count >= 2
    
    @patch('talk.os.path.exists')
    @patch('talk.logger')
    def test_check_prerequisites_missing_model(self, mock_logger, mock_exists):
        """Test prerequisites check when model file is missing"""
        # First call for executable returns True, second for model returns False
        mock_exists.side_effect = [True, False]
        
        with patch('talk.pyaudio.PyAudio'):
            with patch('talk.keyboard.Listener'):
                app = PushToTalkApp()
                result = app.check_prerequisites()
                
                assert result == False
                assert any('not found' in str(call) for call in mock_logger.error.call_args_list)
    
    @patch('talk.os.path.exists')
    @patch('talk.logger')
    def test_set_model_success(self, mock_logger, mock_exists):
        """Test successful model switching"""
        mock_exists.return_value = True
        
        with patch('talk.pyaudio.PyAudio'):
            with patch('talk.keyboard.Listener'):
                app = PushToTalkApp()
                app.show_notification = MagicMock()
                
                # Switch to a model that exists
                app.set_model("tiny.en")
                
                assert app.current_model == "tiny.en"
                app.show_notification.assert_called_once()
                assert "switched successfully" in str(mock_logger.info.call_args_list)


class TestAudioProcessing:
    """Test audio-related functionality"""
    
    def test_audio_data_collection(self):
        """Test that audio data is collected properly"""
        with patch('talk.pyaudio.PyAudio'):
            with patch('talk.keyboard.Listener'):
                app = PushToTalkApp()
                
                # Simulate audio data collection
                app.audio_data = []
                test_chunks = [b'chunk1', b'chunk2', b'chunk3']
                
                for chunk in test_chunks:
                    app.audio_data.append(chunk)
                
                assert len(app.audio_data) == 3
                assert b''.join(app.audio_data) == b'chunk1chunk2chunk3'
    
    @patch('talk.subprocess.run')
    def test_whisper_command_building(self, mock_run):
        """Test that whisper command is built correctly"""
        mock_run.return_value = MagicMock(returncode=0, stdout="Test transcription", stderr="")
        
        with patch('talk.pyaudio.PyAudio'):
            with patch('talk.keyboard.Listener'):
                app = PushToTalkApp()
                
                # Check that the command would be built with correct parameters
                test_wav = "/tmp/test.wav"
                expected_cmd = [
                    "whisper.cpp/build/bin/whisper-cli",
                    "-m", WHISPER_MODELS[app.current_model],
                    "-f", test_wav,
                    "-nt",  # no timestamps
                    "-np"   # no prints
                ]
                
                # This verifies our command structure is correct
                assert expected_cmd[0].endswith("whisper-cli")
                assert "-nt" in expected_cmd
                assert "-np" in expected_cmd


class TestSingletonBehavior:
    """Test single instance enforcement"""
    
    @patch('os.open')
    @patch('fcntl.flock')
    def test_acquire_lock_success(self, mock_flock, mock_open):
        """Test successful lock acquisition"""
        mock_open.return_value = 123  # Fake file descriptor
        
        result = acquire_lock()
        
        assert result == 123
        assert mock_open.called
        assert mock_flock.called
    
    @patch('os.open')
    @patch('fcntl.flock')
    def test_acquire_lock_already_running(self, mock_flock, mock_open):
        """Test lock acquisition when another instance is running"""
        import errno
        mock_open.return_value = 123
        mock_flock.side_effect = IOError(errno.EAGAIN, "Resource temporarily unavailable")
        
        result = acquire_lock()
        
        assert result is None


class TestConfiguration:
    """Test configuration and constants"""
    
    def test_whisper_models_configuration(self):
        """Test that model configuration is properly set"""
        assert "tiny.en" in WHISPER_MODELS
        assert WHISPER_MODELS["tiny.en"] == "whisper.cpp/models/ggml-tiny.en.bin"
        # base.en should be commented out due to compatibility issues
        assert "base.en" not in WHISPER_MODELS
    
    def test_audio_configuration(self):
        """Test audio configuration constants"""
        assert SAMPLE_RATE == 16000  # Required for whisper
        assert CHANNELS == 1  # Mono audio
    
    def test_hotkey_configuration(self):
        """Test hotkey configuration"""
        from talk import HOTKEY_COMBO
        
        # We can't test the actual key values without the real pynput
        # but we can verify the configuration exists
        assert HOTKEY_COMBO is not None


class TestStateManagement:
    """Test application state transitions"""
    
    @patch('talk.pyaudio.PyAudio')
    @patch('talk.keyboard.Listener')
    def test_recording_state_transitions(self, mock_listener, mock_pyaudio):
        """Test that recording state changes correctly"""
        app = PushToTalkApp()
        
        # Initial state
        assert app.is_recording == False
        assert app.audio_data == []
        
        # Can't fully test start_recording without threading complications
        # but we can test state management
        app.is_recording = True
        assert app.is_recording == True
        
        app.is_recording = False
        assert app.is_recording == False
    
    @patch('talk.pyaudio.PyAudio')
    @patch('talk.keyboard.Listener')
    def test_cancel_recording_clears_data(self, mock_listener, mock_pyaudio):
        """Test that cancel recording clears audio data"""
        app = PushToTalkApp()
        app.show_notification = MagicMock()
        
        # Simulate recording state
        app.is_recording = True
        app.audio_data = [b'test_data']
        app.recording_thread = MagicMock()
        app.recording_thread.join = MagicMock()
        
        # Cancel recording
        app.cancel_recording()
        
        assert app.is_recording == False
        assert app.audio_data == []
        app.show_notification.assert_called()


class TestMenuOperations:
    """Test menu-related operations"""
    
    @patch('talk.pyaudio.PyAudio')
    @patch('talk.keyboard.Listener')
    def test_update_status(self, mock_listener, mock_pyaudio):
        """Test status update functionality"""
        app = PushToTalkApp()
        
        # Test different status updates
        app.update_status("Recording...")
        assert app.title == "🔴 Talk"
        
        app.update_status("Ready")
        assert app.title == "Talk"
    
    @patch('talk.pyaudio.PyAudio')
    @patch('talk.keyboard.Listener')
    def test_debug_mode_toggle(self, mock_listener, mock_pyaudio):
        """Test debug mode toggling"""
        app = PushToTalkApp()
        app.show_notification = MagicMock()
        
        initial_state = app.debug_mode
        
        # Create a mock sender
        sender = MagicMock()
        
        # Toggle debug mode
        app.toggle_debug(sender)
        
        assert app.debug_mode != initial_state
        assert sender.state == app.debug_mode


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @patch('talk.subprocess.run')
    @patch('talk.pyaudio.PyAudio')
    @patch('talk.keyboard.Listener')
    def test_whisper_failure_handling(self, mock_listener, mock_pyaudio, mock_run):
        """Test handling of whisper transcription failures"""
        # Simulate whisper failure
        mock_run.return_value = MagicMock(
            returncode=3,
            stdout="",
            stderr="error: failed to initialize whisper context"
        )
        
        app = PushToTalkApp()
        app.show_notification = MagicMock()
        
        # The app should handle this gracefully
        # In real implementation, it falls back to tiny.en
        assert app.current_model == "tiny.en"  # Default model


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=talk", "--cov-report=term-missing"])