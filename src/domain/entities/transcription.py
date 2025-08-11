from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class Transcription:
    """Domain entity representing a transcribed text from audio."""
    
    id: str
    text: str
    timestamp: datetime
    duration_seconds: float
    model_size: str
    confidence: Optional[float] = None
    audio_rms: Optional[float] = None
    
    @classmethod
    def create(
        cls,
        text: str,
        duration_seconds: float,
        model_size: str,
        confidence: Optional[float] = None,
        audio_rms: Optional[float] = None
    ) -> 'Transcription':
        """Factory method to create a new transcription."""
        return cls(
            id=str(uuid.uuid4()),
            text=text,
            timestamp=datetime.now(),
            duration_seconds=duration_seconds,
            model_size=model_size,
            confidence=confidence,
            audio_rms=audio_rms
        )
    
    def is_valid(self) -> bool:
        """Check if the transcription is valid."""
        return len(self.text.strip()) > 0 and self.duration_seconds > 0.5
    
    def is_likely_hallucination(self) -> bool:
        """Check if the transcription is likely a Whisper hallucination."""
        hallucinations = [
            "thank you", "thanks", "thank you.", "thanks.", 
            "thank you for watching", "thanks for watching",
            "please subscribe", "subscribe", "bye", "bye.",
            "you", "you.", "♪", "[music]", "[applause]",
            ".", "..", "...", ""
        ]
        
        text_lower = self.text.lower().strip()
        
        # Check for exact matches
        if text_lower in hallucinations:
            return True
        
        # Check for very short text with low RMS (likely silence)
        if len(self.text) <= 15 and self.audio_rms and self.audio_rms < 0.01:
            return True
        
        return False
    
    def __str__(self) -> str:
        return f"Transcription(text='{self.text[:50]}...', duration={self.duration_seconds:.1f}s)"