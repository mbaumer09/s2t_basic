import tempfile
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
import numpy as np
import soundfile as sf
import torch
import whisper

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.domain.interfaces.transcriber import ITranscriber
from src.domain.entities.transcription import Transcription
from src.domain.value_objects.audio_data import AudioData


class WhisperAdapter(ITranscriber):
    """Whisper implementation of the transcriber interface."""
    
    def __init__(self):
        """Initialize the Whisper adapter."""
        self.model: Optional[whisper.Whisper] = None
        self.model_size: Optional[str] = None
        self.device: Optional[str] = None
        self.model_info: Dict[str, Any] = {}
    
    def transcribe(
        self,
        audio_data: AudioData,
        language: str = 'en',
        **kwargs
    ) -> Transcription:
        """Transcribe audio data to text using Whisper.
        
        Args:
            audio_data: The audio data to transcribe
            language: Language code for transcription
            **kwargs: Additional Whisper transcription parameters
            
        Returns:
            Transcription entity containing the transcribed text and metadata
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        # Prepare audio data
        audio_array = audio_data.data
        if len(audio_array.shape) > 1:
            audio_array = audio_array.flatten()
        
        # Normalize audio if needed
        max_val = np.max(np.abs(audio_array))
        if max_val > 0 and max_val < 0.1:
            audio_array = audio_array / max_val * 0.9
        
        # Save to temporary file (Whisper requires file input)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            temp_path = Path(tmp_file.name)
            sf.write(str(temp_path), audio_array, audio_data.sample_rate)
        
        try:
            # Set default transcription parameters
            transcribe_params = {
                'language': language,
                'fp16': self.device == 'cuda',
                'beam_size': kwargs.get('beam_size', 5),
                'best_of': kwargs.get('best_of', 5),
                'temperature': kwargs.get('temperature', 0.0),
            }
            
            # Override with any provided kwargs
            transcribe_params.update(kwargs)
            
            # Perform transcription
            result = self.model.transcribe(
                str(temp_path.absolute()),
                **transcribe_params
            )
            
            # Extract text and metadata
            text = result['text'].strip()
            
            # Calculate confidence from average log probability
            confidence = None
            if 'segments' in result and result['segments']:
                avg_logprob = np.mean([
                    segment.get('avg_logprob', 0)
                    for segment in result['segments']
                ])
                # Convert log probability to confidence (0-1 scale)
                confidence = float(np.exp(avg_logprob))
            
            # Create transcription entity
            return Transcription.create(
                text=text,
                duration_seconds=audio_data.duration_seconds,
                model_size=self.model_size,
                confidence=confidence,
                audio_rms=audio_data.calculate_rms()
            )
            
        finally:
            # Clean up temporary file
            if temp_path.exists():
                temp_path.unlink()
    
    def load_model(self, model_size: str, device: Optional[str] = None) -> None:
        """Load the Whisper model.
        
        Args:
            model_size: Size of the model to load (tiny, base, small, medium, large)
            device: Device to load the model on (cpu, cuda, or None for auto-detect)
        """
        # Validate model size
        valid_sizes = ['tiny', 'base', 'small', 'medium', 'large']
        if model_size not in valid_sizes:
            raise ValueError(f"Invalid model size: {model_size}. Must be one of {valid_sizes}")
        
        # Auto-detect device if not specified
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # Load the model
        print(f"Loading Whisper '{model_size}' model on {device}...")
        self.model = whisper.load_model(model_size, device=device)
        self.model_size = model_size
        self.device = device
        
        # Store model information
        n_params = sum(p.numel() for p in self.model.parameters())
        self.model_info = {
            'size': model_size,
            'device': device,
            'parameters': n_params,
            'parameters_millions': n_params / 1e6,
            'gpu_available': torch.cuda.is_available(),
        }
        
        if device == 'cuda':
            self.model_info['gpu_name'] = torch.cuda.get_device_name(0)
            self.model_info['gpu_memory_allocated'] = torch.cuda.memory_allocated(0)
        
        print(f"Model loaded: {n_params/1e6:.0f}M parameters on {device.upper()}")
    
    def unload_model(self) -> None:
        """Unload the current model to free memory."""
        if self.model is not None:
            del self.model
            self.model = None
            self.model_size = None
            self.device = None
            self.model_info = {}
            
            # Force garbage collection and clear CUDA cache if applicable
            import gc
            gc.collect()
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    
    def is_model_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        return self.model is not None
    
    def get_model_info(self) -> dict:
        """Get information about the currently loaded model."""
        if not self.is_model_loaded():
            return {'loaded': False}
        
        return {
            'loaded': True,
            **self.model_info
        }
    
    def warmup(self) -> None:
        """Perform a warmup transcription to initialize the model."""
        if not self.is_model_loaded():
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        print("Warming up model...")
        
        # Create dummy audio (1 second of silence)
        dummy_audio = AudioData(
            data=np.zeros(16000, dtype=np.float32),
            sample_rate=16000,
            channels=1
        )
        
        # Perform warmup transcription
        try:
            _ = self.transcribe(dummy_audio, language='en')
            print("Model warmup complete")
        except Exception as e:
            print(f"Warmup failed (non-critical): {e}")