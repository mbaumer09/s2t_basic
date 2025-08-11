from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class RecordingState(Enum):
    """Enumeration of possible recording states."""
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class RecordingSession:
    """Domain entity representing a recording session."""
    
    id: str
    state: RecordingState
    sample_rate: int = 16000
    channels: int = 1
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    device_id: Optional[int] = None
    device_name: Optional[str] = None
    
    @classmethod
    def create(
        cls,
        sample_rate: int = 16000,
        channels: int = 1,
        device_id: Optional[int] = None,
        device_name: Optional[str] = None
    ) -> 'RecordingSession':
        """Factory method to create a new recording session."""
        return cls(
            id=str(uuid.uuid4()),
            state=RecordingState.IDLE,
            sample_rate=sample_rate,
            channels=channels,
            device_id=device_id,
            device_name=device_name
        )
    
    def start(self) -> None:
        """Start the recording session."""
        if self.state != RecordingState.IDLE:
            raise ValueError(f"Cannot start recording from state {self.state}")
        
        self.state = RecordingState.RECORDING
        self.start_time = datetime.now()
        self.end_time = None
        self.error_message = None
    
    def stop(self) -> None:
        """Stop the recording session."""
        if self.state != RecordingState.RECORDING:
            raise ValueError(f"Cannot stop recording from state {self.state}")
        
        self.state = RecordingState.PROCESSING
        self.end_time = datetime.now()
    
    def complete(self) -> None:
        """Mark the recording session as completed."""
        if self.state != RecordingState.PROCESSING:
            raise ValueError(f"Cannot complete recording from state {self.state}")
        
        self.state = RecordingState.COMPLETED
    
    def fail(self, error_message: str) -> None:
        """Mark the recording session as failed."""
        self.state = RecordingState.ERROR
        self.error_message = error_message
        if self.state == RecordingState.RECORDING:
            self.end_time = datetime.now()
    
    def duration(self) -> float:
        """Get the duration of the recording in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time and self.state == RecordingState.RECORDING:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0
    
    def is_recording(self) -> bool:
        """Check if the session is currently recording."""
        return self.state == RecordingState.RECORDING
    
    def is_complete(self) -> bool:
        """Check if the session is complete."""
        return self.state == RecordingState.COMPLETED
    
    def __str__(self) -> str:
        return f"RecordingSession(id={self.id[:8]}, state={self.state.value}, duration={self.duration():.1f}s)"