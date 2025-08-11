import queue
import threading
from typing import List, Tuple, Optional
import numpy as np
import sounddevice as sd

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.domain.interfaces.audio_recorder import IAudioRecorder
from src.domain.value_objects.audio_data import AudioData


class SoundDeviceRecorder(IAudioRecorder):
    """Sound device implementation of the audio recorder interface."""
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        blocksize: int = 512
    ):
        """Initialize the sound device recorder.
        
        Args:
            sample_rate: Sample rate in Hz
            channels: Number of audio channels
            blocksize: Audio block size for streaming
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.blocksize = blocksize
        
        self.audio_queue: queue.Queue = queue.Queue()
        self.recording = False
        self.stream: Optional[sd.InputStream] = None
        self.current_device_id: Optional[int] = None
        self.current_device_name: Optional[str] = None
        
        # Thread safety
        self._lock = threading.Lock()
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback function for audio stream.
        
        This is called from a separate thread by sounddevice.
        """
        if status:
            print(f"Audio stream status: {status}")
        
        if self.recording:
            # Copy the data to avoid it being overwritten
            self.audio_queue.put(indata.copy())
    
    def start_recording(self, device_id: Optional[int] = None) -> None:
        """Start recording audio from the specified device."""
        with self._lock:
            if self.recording:
                raise RuntimeError("Already recording")
            
            # Clear the queue
            self.audio_queue = queue.Queue()
            
            # Use provided device or current device
            device_to_use = device_id if device_id is not None else self.current_device_id
            
            # Stop existing stream if any
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            
            # Create and start new stream
            self.stream = sd.InputStream(
                callback=self._audio_callback,
                device=device_to_use,
                channels=self.channels,
                samplerate=self.sample_rate,
                blocksize=self.blocksize
            )
            
            self.stream.start()
            self.recording = True
    
    def stop_recording(self) -> AudioData:
        """Stop recording and return the captured audio data."""
        with self._lock:
            if not self.recording:
                raise RuntimeError("Not recording")
            
            self.recording = False
            
            # Stop the stream
            if self.stream:
                self.stream.stop()
            
            # Collect all audio chunks from the queue
            audio_chunks = []
            while not self.audio_queue.empty():
                try:
                    chunk = self.audio_queue.get_nowait()
                    audio_chunks.append(chunk)
                except queue.Empty:
                    break
            
            # Concatenate audio chunks
            if audio_chunks:
                audio_array = np.concatenate(audio_chunks, axis=0)
                # Flatten to 1D if mono
                if self.channels == 1:
                    audio_array = audio_array.flatten()
            else:
                # Return empty audio if no data recorded
                audio_array = np.array([])
            
            return AudioData(
                data=audio_array,
                sample_rate=self.sample_rate,
                channels=self.channels
            )
    
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self.recording
    
    def get_available_devices(self) -> List[Tuple[int, str]]:
        """Get list of available audio input devices."""
        devices = sd.query_devices()
        input_devices = []
        seen_names = set()
        
        for idx, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                name = device['name']
                # Filter out duplicates and system devices
                if (name not in seen_names and 
                    'mapper' not in name.lower() and 
                    'primary' not in name.lower()):
                    input_devices.append((idx, name))
                    seen_names.add(name)
        
        return input_devices
    
    def set_device(self, device_id: int) -> None:
        """Set the audio input device to use."""
        # Validate device exists
        devices = sd.query_devices()
        if device_id >= len(devices):
            raise ValueError(f"Invalid device ID: {device_id}")
        
        device = devices[device_id]
        if device['max_input_channels'] <= 0:
            raise ValueError(f"Device {device_id} is not an input device")
        
        self.current_device_id = device_id
        self.current_device_name = device['name']
    
    def get_current_device(self) -> Optional[Tuple[int, str]]:
        """Get the currently selected device."""
        if self.current_device_id is not None:
            return (self.current_device_id, self.current_device_name)
        return None
    
    def __del__(self):
        """Cleanup resources."""
        if self.stream:
            self.stream.stop()
            self.stream.close()