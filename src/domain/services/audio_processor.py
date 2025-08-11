import numpy as np
from typing import Optional
from src.domain.value_objects.audio_data import AudioData


class AudioProcessor:
    """Domain service for audio processing operations."""
    
    def normalize_audio(
        self,
        audio_data: AudioData,
        target_peak: float = 0.9
    ) -> AudioData:
        """Normalize audio to a target peak amplitude.
        
        Args:
            audio_data: The audio data to normalize
            target_peak: Target peak amplitude (0.0 to 1.0)
            
        Returns:
            Normalized AudioData
        """
        if target_peak <= 0 or target_peak > 1.0:
            raise ValueError(f"Target peak must be between 0 and 1, got {target_peak}")
        
        return audio_data.normalize(target_peak)
    
    def convert_to_mono(self, audio_data: AudioData) -> AudioData:
        """Convert stereo audio to mono.
        
        Args:
            audio_data: The audio data to convert
            
        Returns:
            Mono AudioData
        """
        return audio_data.to_mono()
    
    def apply_noise_gate(
        self,
        audio_data: AudioData,
        threshold: float = 0.001,
        attack_time: float = 0.01,
        release_time: float = 0.1
    ) -> AudioData:
        """Apply a noise gate to remove low-level noise.
        
        Args:
            audio_data: The audio data to process
            threshold: Gate threshold (RMS level)
            attack_time: Time to open the gate (seconds)
            release_time: Time to close the gate (seconds)
            
        Returns:
            Processed AudioData
        """
        data = audio_data.data.copy()
        sample_rate = audio_data.sample_rate
        
        # Calculate window sizes
        window_size = int(0.01 * sample_rate)  # 10ms windows
        attack_samples = int(attack_time * sample_rate)
        release_samples = int(release_time * sample_rate)
        
        # Process in windows
        for i in range(0, len(data) - window_size, window_size):
            window = data[i:i + window_size]
            window_rms = np.sqrt(np.mean(window ** 2))
            
            if window_rms < threshold:
                # Apply gate (fade out)
                fade_length = min(release_samples, window_size)
                fade = np.linspace(1.0, 0.0, fade_length)
                data[i:i + fade_length] *= fade
                data[i + fade_length:i + window_size] = 0
        
        return AudioData(
            data=data,
            sample_rate=audio_data.sample_rate,
            channels=audio_data.channels
        )
    
    def trim_silence(
        self,
        audio_data: AudioData,
        threshold: float = 0.001,
        min_silence_duration: float = 0.1
    ) -> AudioData:
        """Trim silence from the beginning and end of audio.
        
        Args:
            audio_data: The audio data to trim
            threshold: RMS threshold for silence detection
            min_silence_duration: Minimum duration of silence to trim (seconds)
            
        Returns:
            Trimmed AudioData
        """
        data = audio_data.data
        sample_rate = audio_data.sample_rate
        window_size = int(min_silence_duration * sample_rate)
        
        # Find start of non-silence
        start_idx = 0
        for i in range(0, len(data) - window_size, window_size // 2):
            window = data[i:i + window_size]
            if np.sqrt(np.mean(window ** 2)) > threshold:
                start_idx = i
                break
        
        # Find end of non-silence
        end_idx = len(data)
        for i in range(len(data) - window_size, 0, -window_size // 2):
            window = data[i:i + window_size]
            if np.sqrt(np.mean(window ** 2)) > threshold:
                end_idx = i + window_size
                break
        
        # Ensure we don't trim everything
        if start_idx >= end_idx:
            return audio_data
        
        trimmed_data = data[start_idx:end_idx]
        
        return AudioData(
            data=trimmed_data,
            sample_rate=audio_data.sample_rate,
            channels=audio_data.channels
        )
    
    def calculate_audio_features(self, audio_data: AudioData) -> dict:
        """Calculate various audio features for analysis.
        
        Args:
            audio_data: The audio data to analyze
            
        Returns:
            Dictionary of audio features
        """
        data = audio_data.data
        
        features = {
            'duration_seconds': audio_data.duration_seconds,
            'sample_rate': audio_data.sample_rate,
            'channels': audio_data.channels,
            'num_samples': audio_data.num_samples,
            'rms': audio_data.calculate_rms(),
            'peak_amplitude': audio_data.calculate_peak_amplitude(),
            'is_silent': audio_data.is_silent(),
        }
        
        # Additional features
        if len(data) > 0:
            features['mean'] = float(np.mean(data))
            features['std'] = float(np.std(data))
            features['min'] = float(np.min(data))
            features['max'] = float(np.max(data))
            
            # Zero crossing rate
            zero_crossings = np.sum(np.diff(np.sign(data)) != 0)
            features['zero_crossing_rate'] = zero_crossings / len(data)
            
            # Dynamic range
            features['dynamic_range_db'] = 20 * np.log10(
                features['peak_amplitude'] / (features['rms'] + 1e-10)
            )
        
        return features