from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass(frozen=True)
class AudioData:
    """Value object representing audio data."""
    
    data: np.ndarray
    sample_rate: int
    channels: int
    
    def __post_init__(self):
        """Validate audio data after initialization."""
        if self.sample_rate <= 0:
            raise ValueError(f"Sample rate must be positive, got {self.sample_rate}")
        
        if self.channels <= 0:
            raise ValueError(f"Channels must be positive, got {self.channels}")
        
        if len(self.data.shape) > 2:
            raise ValueError(f"Audio data must be 1D or 2D, got shape {self.data.shape}")
    
    @property
    def duration_seconds(self) -> float:
        """Get the duration of the audio in seconds."""
        return len(self.data) / self.sample_rate
    
    @property
    def num_samples(self) -> int:
        """Get the number of audio samples."""
        return len(self.data)
    
    def calculate_rms(self) -> float:
        """Calculate the RMS (Root Mean Square) energy of the audio."""
        if len(self.data) == 0:
            return 0.0
        return float(np.sqrt(np.mean(self.data ** 2)))
    
    def calculate_peak_amplitude(self) -> float:
        """Calculate the peak amplitude of the audio."""
        if len(self.data) == 0:
            return 0.0
        return float(np.max(np.abs(self.data)))
    
    def is_silent(self, threshold: float = 0.001) -> bool:
        """Check if the audio is silent based on RMS threshold."""
        return self.calculate_rms() < threshold
    
    def is_too_short(self, min_duration: float = 0.5) -> bool:
        """Check if the audio is too short."""
        return self.duration_seconds < min_duration
    
    def is_too_long(self, max_duration: float = 30.0) -> bool:
        """Check if the audio is too long."""
        return self.duration_seconds > max_duration
    
    def normalize(self, target_peak: float = 0.9) -> 'AudioData':
        """Return a normalized version of the audio data."""
        peak = self.calculate_peak_amplitude()
        if peak > 0:
            normalized_data = self.data / peak * target_peak
        else:
            normalized_data = self.data
        
        return AudioData(
            data=normalized_data,
            sample_rate=self.sample_rate,
            channels=self.channels
        )
    
    def to_mono(self) -> 'AudioData':
        """Convert audio to mono if it's stereo."""
        if len(self.data.shape) == 2 and self.data.shape[1] > 1:
            mono_data = np.mean(self.data, axis=1)
            return AudioData(
                data=mono_data,
                sample_rate=self.sample_rate,
                channels=1
            )
        return self
    
    def __str__(self) -> str:
        return f"AudioData(duration={self.duration_seconds:.1f}s, rate={self.sample_rate}Hz, channels={self.channels})"