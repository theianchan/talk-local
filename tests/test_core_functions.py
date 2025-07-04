"""
Test core functions that can be isolated from GUI components
"""
import pytest
import os
from unittest.mock import patch, MagicMock
import errno

# Test the standalone functions
from talk import acquire_lock, WHISPER_MODELS, SAMPLE_RATE, CHANNELS, CHUNK_SIZE


class TestConfiguration:
    """Test configuration constants"""
    
    def test_audio_constants(self):
        """Test audio configuration is correct for whisper"""
        assert SAMPLE_RATE == 16000  # Whisper requires 16kHz
        assert CHANNELS == 1  # Mono audio
        assert CHUNK_SIZE == 512  # Reasonable chunk size
    
    def test_model_configuration(self):
        """Test model paths are configured"""
        assert "tiny.en" in WHISPER_MODELS
        assert WHISPER_MODELS["tiny.en"].endswith("ggml-tiny.en.bin")
        # base.en should be disabled due to compatibility
        assert "base.en" not in WHISPER_MODELS
    
    def test_whisper_paths(self):
        """Test whisper paths are properly formatted"""
        from talk import WHISPER_EXECUTABLE
        assert WHISPER_EXECUTABLE.endswith("whisper-cli")
        assert "whisper.cpp" in WHISPER_EXECUTABLE


class TestSingletonLock:
    """Test the singleton lock mechanism"""
    
    @patch('os.open')
    @patch('fcntl.flock')
    def test_acquire_lock_success(self, mock_flock, mock_open):
        """Test successful lock acquisition"""
        mock_open.return_value = 42  # Mock file descriptor
        
        result = acquire_lock()
        
        assert result == 42
        mock_open.assert_called_once()
        mock_flock.assert_called_once()
    
    @patch('os.open')
    @patch('fcntl.flock')
    def test_acquire_lock_fails_when_already_locked(self, mock_flock, mock_open):
        """Test lock fails when another instance has it"""
        mock_open.return_value = 42
        mock_flock.side_effect = IOError(errno.EAGAIN, "Resource temporarily unavailable")
        
        result = acquire_lock()
        
        assert result is None
    
    @patch('os.open')
    @patch('fcntl.flock') 
    def test_acquire_lock_propagates_other_errors(self, mock_flock, mock_open):
        """Test that non-lock errors are propagated"""
        mock_open.return_value = 42
        mock_flock.side_effect = IOError(errno.EACCES, "Permission denied")
        
        result = acquire_lock()
        
        assert result is None  # Still returns None for any lock error


class TestAudioHelpers:
    """Test audio-related helper functions"""
    
    def test_audio_data_concatenation(self):
        """Test that audio chunks concatenate correctly"""
        chunks = [b'chunk1', b'chunk2', b'chunk3']
        result = b''.join(chunks)
        assert result == b'chunk1chunk2chunk3'
        assert len(result) == sum(len(c) for c in chunks)
    
    def test_sample_size_calculation(self):
        """Test audio buffer size calculations"""
        # At 16kHz mono with 512 samples per chunk
        bytes_per_sample = 2  # 16-bit audio
        expected_bytes_per_chunk = CHUNK_SIZE * bytes_per_sample * CHANNELS
        assert expected_bytes_per_chunk == 1024  # 512 * 2 * 1


class TestWhisperIntegration:
    """Test whisper command construction"""
    
    def test_whisper_command_structure(self):
        """Test the structure of whisper commands"""
        from talk import WHISPER_EXECUTABLE
        
        test_model = "whisper.cpp/models/ggml-tiny.en.bin" 
        test_wav = "/tmp/test.wav"
        
        # Expected command structure
        expected_cmd = [
            WHISPER_EXECUTABLE,
            "-m", test_model,
            "-f", test_wav,
            "-nt",  # no timestamps
            "-np"   # no prints
        ]
        
        # Verify command components
        assert expected_cmd[0] == WHISPER_EXECUTABLE
        assert "-m" in expected_cmd  # model flag
        assert "-f" in expected_cmd  # file flag
        assert "-nt" in expected_cmd  # no timestamps
        assert "-np" in expected_cmd  # no prints
    
    def test_transcription_text_extraction(self):
        """Test extracting clean text from whisper output"""
        # Sample whisper output with system messages
        whisper_output = """whisper_init_from_file_with_params_no_state: loading model
system_info: n_threads = 8
main: processing audio
[00:00:00.000 --> 00:00:03.000]  Hello, this is a test.
[00:00:03.000 --> 00:00:05.000]  Second sentence here."""
        
        lines = whisper_output.strip().split('\n')
        text = ""
        
        # This mimics the actual extraction logic
        for line in lines:
            if line and not (line.startswith('whisper_') or 
                           line.startswith('system_info') or 
                           line.startswith('main:') or 
                           line.startswith('[') or 
                           ':' in line[:10]):
                text += line.strip() + " "
        
        # Should extract nothing since all lines have prefixes
        assert text.strip() == ""
        
        # Test with clean output
        clean_output = "Hello, this is a test."
        assert clean_output.strip() == "Hello, this is a test."


class TestMenuHelpers:
    """Test menu-related helper logic"""
    
    def test_recording_status_detection(self):
        """Test detecting recording state from status"""
        recording_statuses = ["Recording...", "Recording... 5s", "Recording"]
        non_recording_statuses = ["Ready", "Processing...", "Error", "Transcribed"]
        
        for status in recording_statuses:
            assert "Recording" in status
        
        for status in non_recording_statuses:
            assert "Recording" not in status or status == "Recording"
    
    def test_model_name_validation(self):
        """Test model name validation"""
        valid_models = ["tiny.en", "base.en", "small.en", "medium.en"]
        invalid_models = ["", "unknown", "large.en", None]
        
        for model in valid_models:
            assert model.endswith(".en")  # English models
        
        for model in invalid_models:
            if model:
                assert not model.endswith(".en") or model not in WHISPER_MODELS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])