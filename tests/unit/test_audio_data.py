"""Unit tests for AudioData value object."""

import pytest
import numpy as np
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.domain.value_objects.audio_data import AudioData


class TestAudioData:
    """Test suite for AudioData value object."""
    
    def test_create_audio_data(self):
        """Test creating an AudioData object."""
        data = np.random.rand(16000)
        audio = AudioData(data=data, sample_rate=16000, channels=1)
        
        assert audio.sample_rate == 16000
        assert audio.channels == 1
        assert audio.num_samples == 16000
        assert audio.duration_seconds == 1.0
    
    def test_invalid_sample_rate(self):
        """Test that invalid sample rate raises error."""
        data = np.random.rand(16000)
        
        with pytest.raises(ValueError, match="Sample rate must be positive"):
            AudioData(data=data, sample_rate=0, channels=1)
        
        with pytest.raises(ValueError, match="Sample rate must be positive"):
            AudioData(data=data, sample_rate=-1, channels=1)
    
    def test_invalid_channels(self):
        """Test that invalid channels raises error."""
        data = np.random.rand(16000)
        
        with pytest.raises(ValueError, match="Channels must be positive"):
            AudioData(data=data, sample_rate=16000, channels=0)
    
    def test_calculate_rms(self):
        """Test RMS calculation."""
        # Create known signal
        data = np.ones(1000) * 0.5
        audio = AudioData(data=data, sample_rate=16000, channels=1)
        
        rms = audio.calculate_rms()
        assert abs(rms - 0.5) < 0.001
    
    def test_calculate_rms_empty(self):
        """Test RMS calculation with empty data."""
        data = np.array([])
        audio = AudioData(data=data, sample_rate=16000, channels=1)
        
        assert audio.calculate_rms() == 0.0
    
    def test_calculate_peak_amplitude(self):
        """Test peak amplitude calculation."""
        data = np.array([-0.5, 0.3, 0.8, -0.9, 0.1])
        audio = AudioData(data=data, sample_rate=16000, channels=1)
        
        peak = audio.calculate_peak_amplitude()
        assert abs(peak - 0.9) < 0.001
    
    def test_is_silent(self):
        """Test silence detection."""
        # Very quiet audio
        quiet_data = np.random.rand(1000) * 0.0001
        quiet_audio = AudioData(data=quiet_data, sample_rate=16000, channels=1)
        assert quiet_audio.is_silent(threshold=0.001) == True
        
        # Normal audio
        normal_data = np.random.rand(1000) * 0.1
        normal_audio = AudioData(data=normal_data, sample_rate=16000, channels=1)
        assert normal_audio.is_silent(threshold=0.001) == False
    
    def test_is_too_short(self):
        """Test duration validation."""
        # 0.1 second audio
        short_data = np.random.rand(1600)
        short_audio = AudioData(data=short_data, sample_rate=16000, channels=1)
        
        assert short_audio.is_too_short(min_duration=0.5) == True
        assert short_audio.is_too_short(min_duration=0.05) == False
    
    def test_is_too_long(self):
        """Test max duration validation."""
        # 2 second audio
        long_data = np.random.rand(32000)
        long_audio = AudioData(data=long_data, sample_rate=16000, channels=1)
        
        assert long_audio.is_too_long(max_duration=1.0) == True
        assert long_audio.is_too_long(max_duration=3.0) == False
    
    def test_normalize(self):
        """Test audio normalization."""
        data = np.array([0.1, -0.2, 0.3, -0.4, 0.5])
        audio = AudioData(data=data, sample_rate=16000, channels=1)
        
        normalized = audio.normalize(target_peak=0.9)
        
        # Check peak is correct
        assert abs(normalized.calculate_peak_amplitude() - 0.9) < 0.001
        
        # Check it's a new object (immutability)
        assert normalized is not audio
        assert not np.array_equal(normalized.data, audio.data)
    
    def test_normalize_silent_audio(self):
        """Test normalizing silent audio."""
        data = np.zeros(1000)
        audio = AudioData(data=data, sample_rate=16000, channels=1)
        
        normalized = audio.normalize(target_peak=0.9)
        
        # Should remain silent
        assert np.all(normalized.data == 0)
    
    def test_to_mono_from_stereo(self):
        """Test converting stereo to mono."""
        # Create stereo data (1000 samples, 2 channels)
        stereo_data = np.random.rand(1000, 2)
        stereo_audio = AudioData(data=stereo_data, sample_rate=16000, channels=2)
        
        mono_audio = stereo_audio.to_mono()
        
        assert mono_audio.channels == 1
        assert len(mono_audio.data.shape) == 1
        assert mono_audio.data.shape[0] == 1000
    
    def test_to_mono_already_mono(self):
        """Test converting mono to mono (should return same)."""
        mono_data = np.random.rand(1000)
        mono_audio = AudioData(data=mono_data, sample_rate=16000, channels=1)
        
        result = mono_audio.to_mono()
        
        assert result.channels == 1
        assert np.array_equal(result.data, mono_audio.data)
    
    def test_immutability(self):
        """Test that AudioData is immutable."""
        data = np.array([0.1, 0.2, 0.3])
        audio = AudioData(data=data, sample_rate=16000, channels=1)
        
        # Should not be able to modify after creation
        with pytest.raises(AttributeError):
            audio.sample_rate = 8000
        
        with pytest.raises(AttributeError):
            audio.channels = 2
    
    def test_string_representation(self):
        """Test string representation."""
        data = np.random.rand(16000)
        audio = AudioData(data=data, sample_rate=16000, channels=1)
        
        str_repr = str(audio)
        assert "1.0s" in str_repr
        assert "16000Hz" in str_repr
        assert "channels=1" in str_repr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])