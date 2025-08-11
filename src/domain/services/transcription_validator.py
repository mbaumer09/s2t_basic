from typing import Optional
from src.domain.entities.transcription import Transcription
from src.domain.value_objects.audio_data import AudioData


class TranscriptionValidator:
    """Domain service for validating transcriptions."""
    
    def __init__(
        self,
        min_duration: float = 0.5,
        max_duration: float = 30.0,
        silence_threshold: float = 0.001,
        min_text_length: int = 1,
        min_rms_for_short_text: float = 0.01
    ):
        """Initialize the transcription validator.
        
        Args:
            min_duration: Minimum audio duration in seconds
            max_duration: Maximum audio duration in seconds
            silence_threshold: RMS threshold below which audio is considered silent
            min_text_length: Minimum text length to be valid
            min_rms_for_short_text: Minimum RMS for short text to avoid hallucinations
        """
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.silence_threshold = silence_threshold
        self.min_text_length = min_text_length
        self.min_rms_for_short_text = min_rms_for_short_text
    
    def validate_audio(self, audio_data: AudioData) -> tuple[bool, Optional[str]]:
        """Validate audio data before transcription.
        
        Args:
            audio_data: The audio data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check duration
        if audio_data.is_too_short(self.min_duration):
            return False, f"Audio too short ({audio_data.duration_seconds:.1f}s < {self.min_duration}s)"
        
        if audio_data.is_too_long(self.max_duration):
            return False, f"Audio too long ({audio_data.duration_seconds:.1f}s > {self.max_duration}s)"
        
        # Check for silence
        if audio_data.is_silent(self.silence_threshold):
            rms = audio_data.calculate_rms()
            return False, f"Audio is too quiet (RMS: {rms:.4f})"
        
        # Check peak amplitude
        peak = audio_data.calculate_peak_amplitude()
        if peak < 0.01:
            return False, f"Audio volume too low (peak: {peak:.4f})"
        
        return True, None
    
    def validate_transcription(
        self,
        transcription: Transcription,
        audio_data: Optional[AudioData] = None
    ) -> tuple[bool, Optional[str]]:
        """Validate a transcription result.
        
        Args:
            transcription: The transcription to validate
            audio_data: Optional audio data for additional validation
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for empty text
        if not transcription.text or not transcription.text.strip():
            return False, "Empty transcription"
        
        # Check minimum text length
        if len(transcription.text.strip()) < self.min_text_length:
            return False, f"Text too short ({len(transcription.text)} characters)"
        
        # Check for likely hallucinations
        if transcription.is_likely_hallucination():
            return False, f"Likely hallucination: '{transcription.text}'"
        
        # Additional validation with audio data
        if audio_data:
            # Short text with low RMS is likely a hallucination
            if len(transcription.text) <= 15:
                rms = audio_data.calculate_rms()
                if rms < self.min_rms_for_short_text:
                    return False, f"Short text with low audio energy (possible hallucination)"
        
        return True, None
    
    def is_valid_for_output(self, transcription: Transcription) -> bool:
        """Quick check if transcription is valid for output.
        
        Args:
            transcription: The transcription to check
            
        Returns:
            True if valid for output, False otherwise
        """
        is_valid, _ = self.validate_transcription(transcription)
        return is_valid