import json
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List


@dataclass
class AudioConfig:
    """Audio configuration settings."""
    sample_rate: int = 16000
    channels: int = 1
    blocksize: int = 512
    max_recording_duration: int = 30
    min_recording_duration: float = 0.5
    silence_threshold: float = 0.001
    normalize_audio: bool = True
    trim_silence: bool = True
    device_id: Optional[int] = None


@dataclass
class TranscriptionConfig:
    """Transcription configuration settings."""
    model_size: str = 'base'
    language: str = 'en'
    device: Optional[str] = None  # None for auto-detect
    beam_size: int = 5
    best_of: int = 5
    temperature: float = 0.0
    fp16: Optional[bool] = None  # None for auto-detect based on device


@dataclass
class HotkeyConfig:
    """Hotkey configuration settings."""
    record_key: str = 'right ctrl'
    debounce_time: float = 0.5


@dataclass
class UIConfig:
    """UI configuration settings."""
    enable_audio_feedback: bool = True
    start_beep_frequency: int = 800
    stop_beep_frequency: int = 600
    error_beep_frequency: int = 400
    success_beep_frequency: int = 1000
    beep_duration_ms: int = 100
    auto_add_space: bool = True
    auto_execute: bool = False
    minimize_to_tray: bool = True


@dataclass
class Config:
    """Application configuration."""
    audio: AudioConfig = field(default_factory=AudioConfig)
    transcription: TranscriptionConfig = field(default_factory=TranscriptionConfig)
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create config from dictionary.
        
        Args:
            data: Configuration dictionary
            
        Returns:
            Config instance
        """
        config = cls()
        
        if 'audio' in data:
            config.audio = AudioConfig(**data['audio'])
        
        if 'transcription' in data:
            config.transcription = TranscriptionConfig(**data['transcription'])
        
        if 'hotkey' in data:
            config.hotkey = HotkeyConfig(**data['hotkey'])
        
        if 'ui' in data:
            config.ui = UIConfig(**data['ui'])
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary.
        
        Returns:
            Configuration dictionary
        """
        return {
            'audio': {
                'sample_rate': self.audio.sample_rate,
                'channels': self.audio.channels,
                'blocksize': self.audio.blocksize,
                'max_recording_duration': self.audio.max_recording_duration,
                'min_recording_duration': self.audio.min_recording_duration,
                'silence_threshold': self.audio.silence_threshold,
                'normalize_audio': self.audio.normalize_audio,
                'trim_silence': self.audio.trim_silence,
                'device_id': self.audio.device_id
            },
            'transcription': {
                'model_size': self.transcription.model_size,
                'language': self.transcription.language,
                'device': self.transcription.device,
                'beam_size': self.transcription.beam_size,
                'best_of': self.transcription.best_of,
                'temperature': self.transcription.temperature,
                'fp16': self.transcription.fp16
            },
            'hotkey': {
                'record_key': self.hotkey.record_key,
                'debounce_time': self.hotkey.debounce_time
            },
            'ui': {
                'enable_audio_feedback': self.ui.enable_audio_feedback,
                'start_beep_frequency': self.ui.start_beep_frequency,
                'stop_beep_frequency': self.ui.stop_beep_frequency,
                'error_beep_frequency': self.ui.error_beep_frequency,
                'success_beep_frequency': self.ui.success_beep_frequency,
                'beep_duration_ms': self.ui.beep_duration_ms,
                'auto_add_space': self.ui.auto_add_space,
                'auto_execute': self.ui.auto_execute,
                'minimize_to_tray': self.ui.minimize_to_tray
            }
        }


class ConfigLoader:
    """Service for loading and saving configuration."""
    
    @staticmethod
    def load_from_file(file_path: Path) -> Config:
        """Load configuration from file.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            Config instance
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is unsupported
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            if file_path.suffix == '.json':
                data = json.load(f)
            elif file_path.suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported config format: {file_path.suffix}")
        
        return Config.from_dict(data)
    
    @staticmethod
    def save_to_file(config: Config, file_path: Path) -> None:
        """Save configuration to file.
        
        Args:
            config: Config instance to save
            file_path: Path to save configuration to
            
        Raises:
            ValueError: If file format is unsupported
        """
        data = config.to_dict()
        
        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            if file_path.suffix == '.json':
                json.dump(data, f, indent=2)
            elif file_path.suffix in ['.yaml', '.yml']:
                yaml.safe_dump(data, f, default_flow_style=False)
            else:
                raise ValueError(f"Unsupported config format: {file_path.suffix}")
    
    @staticmethod
    def load_or_create_default(file_path: Path) -> Config:
        """Load config from file or create default if not exists.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            Config instance
        """
        if file_path.exists():
            try:
                return ConfigLoader.load_from_file(file_path)
            except Exception as e:
                print(f"Error loading config: {e}. Using defaults.")
        
        # Create and save default config
        config = Config()
        try:
            ConfigLoader.save_to_file(config, file_path)
            print(f"Created default configuration at: {file_path}")
        except Exception as e:
            print(f"Could not save default config: {e}")
        
        return config