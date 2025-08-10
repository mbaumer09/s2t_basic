from abc import ABC, abstractmethod
from typing import Optional
from domain.value_objects.audio_data import AudioData
from domain.entities.transcription import Transcription


class ITranscriber(ABC):
    """Interface for audio transcription functionality."""
    
    @abstractmethod
    def transcribe(
        self,
        audio_data: AudioData,
        language: str = 'en',
        **kwargs
    ) -> Transcription:
        """Transcribe audio data to text.
        
        Args:
            audio_data: The audio data to transcribe
            language: Language code for transcription
            **kwargs: Additional transcription parameters
            
        Returns:
            Transcription entity containing the transcribed text and metadata
        """
        pass
    
    @abstractmethod
    def load_model(self, model_size: str, device: Optional[str] = None) -> None:
        """Load the transcription model.
        
        Args:
            model_size: Size of the model to load (tiny, base, small, medium, large)
            device: Device to load the model on (cpu, cuda, or None for auto-detect)
        """
        pass
    
    @abstractmethod
    def unload_model(self) -> None:
        """Unload the current model to free memory."""
        pass
    
    @abstractmethod
    def is_model_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        pass
    
    @abstractmethod
    def get_model_info(self) -> dict:
        """Get information about the currently loaded model.
        
        Returns:
            Dictionary containing model information (size, device, parameters, etc.)
        """
        pass
    
    @abstractmethod
    def warmup(self) -> None:
        """Perform a warmup transcription to initialize the model."""
        pass