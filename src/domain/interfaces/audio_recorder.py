from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
from domain.value_objects.audio_data import AudioData


class IAudioRecorder(ABC):
    """Interface for audio recording functionality."""
    
    @abstractmethod
    def start_recording(self, device_id: Optional[int] = None) -> None:
        """Start recording audio from the specified device."""
        pass
    
    @abstractmethod
    def stop_recording(self) -> AudioData:
        """Stop recording and return the captured audio data."""
        pass
    
    @abstractmethod
    def is_recording(self) -> bool:
        """Check if currently recording."""
        pass
    
    @abstractmethod
    def get_available_devices(self) -> List[Tuple[int, str]]:
        """Get list of available audio input devices.
        
        Returns:
            List of tuples containing (device_id, device_name)
        """
        pass
    
    @abstractmethod
    def set_device(self, device_id: int) -> None:
        """Set the audio input device to use."""
        pass
    
    @abstractmethod
    def get_current_device(self) -> Optional[Tuple[int, str]]:
        """Get the currently selected device.
        
        Returns:
            Tuple of (device_id, device_name) or None if not set
        """
        pass