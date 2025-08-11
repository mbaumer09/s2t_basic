import winsound
from typing import Optional


class AudioFeedback:
    """Service for providing audio feedback to the user."""
    
    def __init__(self, enabled: bool = True):
        """Initialize the audio feedback service.
        
        Args:
            enabled: Whether audio feedback is enabled
        """
        self.enabled = enabled
        
        # Default beep frequencies
        self.start_frequency = 800
        self.stop_frequency = 600
        self.error_frequency = 400
        self.success_frequency = 1000
        
        # Default beep duration
        self.default_duration = 100
    
    def play_beep(self, frequency: int, duration_ms: int = None) -> bool:
        """Play a beep sound.
        
        Args:
            frequency: Frequency of the beep in Hz
            duration_ms: Duration of the beep in milliseconds
            
        Returns:
            True if beep was played, False if disabled or error
        """
        if not self.enabled:
            return False
        
        duration = duration_ms if duration_ms is not None else self.default_duration
        
        try:
            winsound.Beep(frequency, duration)
            return True
        except Exception as e:
            print(f"Failed to play beep: {e}")
            return False
    
    def play_recording_start(self) -> bool:
        """Play the recording start sound."""
        return self.play_beep(self.start_frequency)
    
    def play_recording_stop(self) -> bool:
        """Play the recording stop sound."""
        return self.play_beep(self.stop_frequency)
    
    def play_error(self) -> bool:
        """Play an error sound."""
        return self.play_beep(self.error_frequency, 200)
    
    def play_success(self) -> bool:
        """Play a success sound."""
        return self.play_beep(self.success_frequency)
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable audio feedback.
        
        Args:
            enabled: Whether to enable audio feedback
        """
        self.enabled = enabled
    
    def is_enabled(self) -> bool:
        """Check if audio feedback is enabled.
        
        Returns:
            True if enabled, False otherwise
        """
        return self.enabled
    
    def set_frequencies(
        self,
        start: Optional[int] = None,
        stop: Optional[int] = None,
        error: Optional[int] = None,
        success: Optional[int] = None
    ) -> None:
        """Set custom beep frequencies.
        
        Args:
            start: Frequency for recording start
            stop: Frequency for recording stop
            error: Frequency for errors
            success: Frequency for success
        """
        if start is not None:
            self.start_frequency = start
        if stop is not None:
            self.stop_frequency = stop
        if error is not None:
            self.error_frequency = error
        if success is not None:
            self.success_frequency = success