"""Bootstrap module for initializing the application with dependency injection."""

from pathlib import Path
from typing import Optional

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.container import Container, Scope
from src.core.config import Config, ConfigLoader

# Domain interfaces
from src.domain.interfaces.audio_recorder import IAudioRecorder
from src.domain.interfaces.transcriber import ITranscriber
from src.domain.interfaces.text_output import ITextOutput
from src.domain.interfaces.hotkey_handler import IHotkeyHandler

# Domain services
from src.domain.services.voice_command_parser import VoiceCommandParser
from src.domain.services.transcription_validator import TranscriptionValidator
from src.domain.services.audio_processor import AudioProcessor

# Infrastructure implementations
from src.infrastructure.audio.sounddevice_recorder import SoundDeviceRecorder
from src.infrastructure.audio.audio_feedback import AudioFeedback
from src.infrastructure.transcription.whisper_adapter import WhisperAdapter
from src.infrastructure.transcription.model_manager import ModelManager
from src.infrastructure.windows.window_manager import WindowManager
from src.infrastructure.windows.keyboard_simulator import KeyboardSimulator

# Application use cases
from src.application.use_cases.record_and_transcribe import RecordAndTranscribeUseCase
from src.application.use_cases.send_text import SendTextUseCase
from src.application.use_cases.manage_recording import ManageRecordingUseCase


class ApplicationBootstrap:
    """Bootstrap class for initializing the application."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the bootstrap with configuration.
        
        Args:
            config: Application configuration, uses defaults if None
        """
        self.config = config or Config()
        self.container = Container()
        self._register_dependencies()
    
    def _register_dependencies(self) -> None:
        """Register all application dependencies in the container."""
        
        # Register configuration
        self.container.register_instance(Config, self.config)
        
        # Register domain services
        self.container.register_singleton(VoiceCommandParser, VoiceCommandParser)
        self.container.register_singleton(AudioProcessor, AudioProcessor)
        
        # Register transcription validator with config
        self.container.register_factory(
            TranscriptionValidator,
            lambda: TranscriptionValidator(
                min_duration=self.config.audio.min_recording_duration,
                max_duration=self.config.audio.max_recording_duration,
                silence_threshold=self.config.audio.silence_threshold
            ),
            scope=Scope.SINGLETON
        )
        
        # Register infrastructure - Audio
        self.container.register_factory(
            IAudioRecorder,
            lambda: SoundDeviceRecorder(
                sample_rate=self.config.audio.sample_rate,
                channels=self.config.audio.channels,
                blocksize=self.config.audio.blocksize
            ),
            scope=Scope.SINGLETON
        )
        
        # Register infrastructure - Transcription
        self.container.register_singleton(ITranscriber, WhisperAdapter)
        self.container.register_singleton(ModelManager, ModelManager)
        
        # Register infrastructure - Windows
        self.container.register_singleton(ITextOutput, WindowManager)
        self.container.register_singleton(IHotkeyHandler, KeyboardSimulator)
        
        # Register infrastructure - Audio feedback
        self.container.register_factory(
            AudioFeedback,
            lambda: AudioFeedback(enabled=self.config.ui.enable_audio_feedback),
            scope=Scope.SINGLETON
        )
        
        # Register application use cases
        self.container.register_transient(
            RecordAndTranscribeUseCase,
            RecordAndTranscribeUseCase
        )
        self.container.register_transient(SendTextUseCase, SendTextUseCase)
        self.container.register_transient(ManageRecordingUseCase, ManageRecordingUseCase)
    
    def get_container(self) -> Container:
        """Get the configured DI container.
        
        Returns:
            The dependency injection container
        """
        return self.container
    
    def initialize_model(self) -> None:
        """Initialize the transcription model."""
        transcriber = self.container.resolve(ITranscriber)
        model_manager = self.container.resolve(ModelManager)
        
        # Get device recommendation
        device = self.config.transcription.device
        if device is None:
            recommendation = model_manager.get_device_recommendation()
            device = recommendation['device']
            print(f"Using recommended device: {device}")
        
        # Load model
        model_size = self.config.transcription.model_size
        print(f"Loading {model_size} model on {device}...")
        
        transcriber.load_model(model_size, device)
        
        # Warmup
        print("Warming up model...")
        transcriber.warmup()
        
        print("Model initialization complete")
    
    def setup_audio_device(self, device_id: Optional[int] = None) -> None:
        """Set up the audio recording device.
        
        Args:
            device_id: Specific device ID to use, or None for default
        """
        audio_recorder = self.container.resolve(IAudioRecorder)
        
        if device_id is None:
            device_id = self.config.audio.device_id
        
        if device_id is not None:
            audio_recorder.set_device(device_id)
            print(f"Audio device set to ID: {device_id}")
        else:
            # Use first available device
            devices = audio_recorder.get_available_devices()
            if devices:
                device_id, device_name = devices[0]
                audio_recorder.set_device(device_id)
                print(f"Using audio device: {device_name} (ID: {device_id})")
    
    def setup_hotkeys(self) -> None:
        """Set up hotkey handlers."""
        hotkey_handler = self.container.resolve(IHotkeyHandler)
        
        # Set debounce time
        if hasattr(hotkey_handler, 'set_debounce_time'):
            hotkey_handler.set_debounce_time(self.config.hotkey.debounce_time)
        
        print(f"Hotkey configuration: {self.config.hotkey.record_key}")
    
    @staticmethod
    def create_from_config_file(config_path: Path) -> 'ApplicationBootstrap':
        """Create bootstrap from configuration file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configured ApplicationBootstrap instance
        """
        config = ConfigLoader.load_or_create_default(config_path)
        return ApplicationBootstrap(config)


def create_default_container() -> Container:
    """Create a container with default configuration.
    
    Returns:
        Configured DI container
    """
    bootstrap = ApplicationBootstrap()
    return bootstrap.get_container()


def create_container_from_config(config: Config) -> Container:
    """Create a container with specific configuration.
    
    Args:
        config: Application configuration
        
    Returns:
        Configured DI container
    """
    bootstrap = ApplicationBootstrap(config)
    return bootstrap.get_container()