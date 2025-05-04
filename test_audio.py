#!/usr/bin/env python3
"""
Simple test script to verify audio recording works
"""

import pyaudio
import wave
import tempfile
import time

def record_audio_test(duration=3):
    """Record audio for a fixed duration and save to file."""
    CHUNK_SIZE = 512
    SAMPLE_RATE = 16000
    CHANNELS = 1
    
    audio = pyaudio.PyAudio()
    
    print(f"Recording for {duration} seconds...")
    
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE
    )
    
    frames = []
    
    for i in range(0, int(SAMPLE_RATE / CHUNK_SIZE * duration)):
        data = stream.read(CHUNK_SIZE)
        frames.append(data)
    
    stream.stop_stream()
    stream.close()
    audio.terminate()
    
    print("Recording complete.")
    
    # Save the audio to a file
    output_file = "test_recording.wav"
    with wave.open(output_file, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b''.join(frames))
    
    print(f"Audio saved to {output_file}")
    return output_file

if __name__ == "__main__":
    print("Testing audio recording...")
    output_file = record_audio_test(3)
    print(f"Test completed. Check the file: {output_file}")