# Refactoring Execution Plan

## Overview

This document provides a step-by-step execution plan for refactoring the speech-to-text application from a monolithic structure to a clean, modular architecture. Each step includes specific tasks, acceptance criteria, and code examples.

## Pre-Refactoring Setup

### Step 0: Environment Preparation
```bash
# Create feature branch
git checkout -b refactor/clean-architecture

# Set up test framework
pip install pytest pytest-cov pytest-mock

# Create initial directory structure
mkdir -p src/{domain,application,infrastructure,presentation,core}
mkdir -p tests/{unit,integration,e2e}
```

## Phase 1: Domain Layer Implementation (Days 1-3)

### Step 1.1: Create Domain Entities

**File: `src/domain/entities/transcription.py`**
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Transcription:
    id: str
    text: str
    timestamp: datetime
    duration_seconds: float
    model_size: str
    confidence: Optional[float] = None
    audio_rms: Optional[float] = None
    
    def is_valid(self) -> bool:
        return len(self.text.strip()) > 0 and self.duration_seconds > 0.5
    
    def is_hallucination(self) -> bool:
        hallucinations = ["thank you", "thanks", "subscribe", "bye"]
        return self.text.lower().strip() in hallucinations
```

**File: `src/domain/entities/recording_session.py`**
```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class RecordingState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    
@dataclass
class RecordingSession:
    id: str
    state: RecordingState
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    sample_rate: int = 16000
    channels: int = 1
    
    def duration(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
```

### Step 1.2: Define Domain Interfaces

**File: `src/domain/interfaces/audio_recorder.py`**
```python
from abc import ABC, abstractmethod
from typing import Optional
import numpy as np

class IAudioRecorder(ABC):
    @abstractmethod
    def start_recording(self) -> None:
        pass
    
    @abstractmethod
    def stop_recording(self) -> np.ndarray:
        pass
    
    @abstractmethod
    def is_recording(self) -> bool:
        pass
    
    @abstractmethod
    def get_available_devices(self) -> list:
        pass
```

**File: `src/domain/interfaces/transcriber.py`**
```python
from abc import ABC, abstractmethod
from typing import Optional
from domain.entities.transcription import Transcription

class ITranscriber(ABC):
    @abstractmethod
    def transcribe(self, audio_data: np.ndarray, language: str = 'en') -> Transcription:
        pass
    
    @abstractmethod
    def load_model(self, model_size: str) -> None:
        pass
```

### Step 1.3: Implement Domain Services

**File: `src/domain/services/voice_command_parser.py`**
```python
from typing import Tuple, List
from dataclasses import dataclass

@dataclass
class VoiceCommand:
    command_type: str
    text: str
    execute: bool = False

class VoiceCommandParser:
    EXECUTE_PATTERNS = [
        'execute mode', 'execute command', 'run command'
    ]
    
    def parse(self, text: str) -> VoiceCommand:
        lower_text = text.lower()
        
        for pattern in self.EXECUTE_PATTERNS:
            if lower_text.startswith(pattern):
                cleaned_text = text[len(pattern):].strip()
                return VoiceCommand(
                    command_type='execute',
                    text=cleaned_text,
                    execute=True
                )
        
        return VoiceCommand(
            command_type='text',
            text=text,
            execute=False
        )
```

## Phase 2: Infrastructure Layer (Days 4-7)

### Step 2.1: Audio Recording Adapter

**File: `src/infrastructure/audio/sounddevice_recorder.py`**
```python
import queue
import numpy as np
import sounddevice as sd
from domain.interfaces.audio_recorder import IAudioRecorder

class SoundDeviceRecorder(IAudioRecorder):
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.audio_queue = queue.Queue()
        self.recording = False
        self.stream = None
        
    def _audio_callback(self, indata, frames, time_info, status):
        if self.recording:
            self.audio_queue.put(indata.copy())
    
    def start_recording(self) -> None:
        self.audio_queue = queue.Queue()
        self.recording = True
        
        if not self.stream:
            self.stream = sd.InputStream(
                callback=self._audio_callback,
                channels=self.channels,
                samplerate=self.sample_rate,
                blocksize=512
            )
            self.stream.start()
    
    def stop_recording(self) -> np.ndarray:
        self.recording = False
        
        # Collect audio data
        audio_chunks = []
        while not self.audio_queue.empty():
            audio_chunks.append(self.audio_queue.get())
        
        if audio_chunks:
            return np.concatenate(audio_chunks, axis=0)
        return np.array([])
    
    def is_recording(self) -> bool:
        return self.recording
    
    def get_available_devices(self) -> list:
        devices = sd.query_devices()
        return [(idx, dev['name']) for idx, dev in enumerate(devices) 
                if dev['max_input_channels'] > 0]
```

### Step 2.2: Whisper Transcription Adapter

**File: `src/infrastructure/transcription/whisper_adapter.py`**
```python
import whisper
import numpy as np
import tempfile
import soundfile as sf
from pathlib import Path
from datetime import datetime
from domain.interfaces.transcriber import ITranscriber
from domain.entities.transcription import Transcription

class WhisperAdapter(ITranscriber):
    def __init__(self):
        self.model = None
        self.model_size = None
        
    def load_model(self, model_size: str) -> None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = whisper.load_model(model_size, device=device)
        self.model_size = model_size
        
    def transcribe(self, audio_data: np.ndarray, language: str = 'en') -> Transcription:
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        # Save audio to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            sf.write(tmp.name, audio_data, 16000)
            temp_path = Path(tmp.name)
        
        try:
            # Perform transcription
            result = self.model.transcribe(
                str(temp_path),
                language=language,
                fp16=torch.cuda.is_available(),
                beam_size=5,
                temperature=0.0
            )
            
            return Transcription(
                id=str(uuid.uuid4()),
                text=result['text'].strip(),
                timestamp=datetime.now(),
                duration_seconds=len(audio_data) / 16000,
                model_size=self.model_size,
                confidence=result.get('avg_logprob')
            )
        finally:
            temp_path.unlink()
```

### Step 2.3: Window Management Adapter

**File: `src/infrastructure/windows/window_manager.py`**
```python
import win32gui
import win32con
import keyboard
import time
from typing import Optional, List, Tuple

class WindowManager:
    def __init__(self):
        self.target_window_handle: Optional[int] = None
        
    def get_window_list(self) -> List[Tuple[int, str]]:
        windows = []
        
        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title.strip():
                    windows.append((hwnd, title))
            return True
        
        win32gui.EnumWindows(enum_callback, None)
        return sorted(windows, key=lambda x: x[1].lower())
    
    def set_target_window(self, handle: Optional[int]) -> None:
        self.target_window_handle = handle
    
    def send_text(self, text: str, execute: bool = False) -> bool:
        try:
            if self.target_window_handle:
                # Focus target window
                win32gui.SetForegroundWindow(self.target_window_handle)
                time.sleep(0.1)
            
            # Type text
            keyboard.write(' ' + text)
            
            if execute:
                time.sleep(0.1)
                keyboard.press_and_release('enter')
            
            return True
        except Exception:
            return False
```

## Phase 3: Application Layer (Days 8-10)

### Step 3.1: Use Cases Implementation

**File: `src/application/use_cases/record_and_transcribe.py`**
```python
from dataclasses import dataclass
from domain.interfaces.audio_recorder import IAudioRecorder
from domain.interfaces.transcriber import ITranscriber
from domain.services.voice_command_parser import VoiceCommandParser

@dataclass
class RecordAndTranscribeRequest:
    min_duration: float = 0.5
    max_duration: float = 30.0
    silence_threshold: float = 0.001

@dataclass
class RecordAndTranscribeResponse:
    text: str
    execute: bool
    duration: float
    success: bool

class RecordAndTranscribeUseCase:
    def __init__(
        self,
        audio_recorder: IAudioRecorder,
        transcriber: ITranscriber,
        command_parser: VoiceCommandParser
    ):
        self.audio_recorder = audio_recorder
        self.transcriber = transcriber
        self.command_parser = command_parser
    
    def execute(self, request: RecordAndTranscribeRequest) -> RecordAndTranscribeResponse:
        # Start recording
        self.audio_recorder.start_recording()
        
        # Wait for recording to complete
        # (This would be triggered by hotkey release in real implementation)
        audio_data = self.audio_recorder.stop_recording()
        
        # Validate audio
        duration = len(audio_data) / 16000
        if duration < request.min_duration:
            return RecordAndTranscribeResponse(
                text="", execute=False, duration=duration, success=False
            )
        
        # Check for silence
        rms = np.sqrt(np.mean(audio_data**2))
        if rms < request.silence_threshold:
            return RecordAndTranscribeResponse(
                text="", execute=False, duration=duration, success=False
            )
        
        # Transcribe
        transcription = self.transcriber.transcribe(audio_data)
        
        # Parse commands
        command = self.command_parser.parse(transcription.text)
        
        return RecordAndTranscribeResponse(
            text=command.text,
            execute=command.execute,
            duration=duration,
            success=True
        )
```

### Step 3.2: Application Services

**File: `src/application/services/audio_service.py`**
```python
from typing import Optional
from core.events import EventBus, RecordingStartedEvent, RecordingStoppedEvent

class AudioService:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.is_recording = False
        
    def start_recording(self) -> None:
        if not self.is_recording:
            self.is_recording = True
            self.event_bus.publish(RecordingStartedEvent())
    
    def stop_recording(self) -> None:
        if self.is_recording:
            self.is_recording = False
            self.event_bus.publish(RecordingStoppedEvent())
```

## Phase 4: Presentation Layer (Days 11-13)

### Step 4.1: View Models

**File: `src/presentation/gui/view_models/main_view_model.py`**
```python
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Optional

class MainViewModel(QObject):
    # Signals
    status_changed = pyqtSignal(str)
    recording_state_changed = pyqtSignal(bool)
    transcription_received = pyqtSignal(str)
    log_message = pyqtSignal(str)
    
    def __init__(self, audio_service, transcription_service):
        super().__init__()
        self.audio_service = audio_service
        self.transcription_service = transcription_service
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        # Subscribe to domain events
        self.audio_service.on_recording_started = self.on_recording_started
        self.audio_service.on_recording_stopped = self.on_recording_stopped
        self.transcription_service.on_transcription_complete = self.on_transcription_complete
    
    def on_recording_started(self):
        self.recording_state_changed.emit(True)
        self.status_changed.emit("Recording...")
        self.log_message.emit("Recording started")
    
    def on_recording_stopped(self):
        self.recording_state_changed.emit(False)
        self.status_changed.emit("Processing...")
        self.log_message.emit("Recording stopped")
    
    def on_transcription_complete(self, text: str):
        self.transcription_received.emit(text)
        self.status_changed.emit("Ready")
```

### Step 4.2: Refactored GUI Components

**File: `src/presentation/gui/widgets/status_bar.py`**
```python
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import pyqtSlot

class StatusBar(QWidget):
    def __init__(self, view_model):
        super().__init__()
        self.view_model = view_model
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        layout = QHBoxLayout()
        
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        self.recording_indicator = QLabel("⚫")
        self.recording_indicator.setStyleSheet("font-size: 20px; color: gray;")
        layout.addWidget(self.recording_indicator)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _connect_signals(self):
        self.view_model.status_changed.connect(self.update_status)
        self.view_model.recording_state_changed.connect(self.update_recording_indicator)
    
    @pyqtSlot(str)
    def update_status(self, status: str):
        self.status_label.setText(status)
    
    @pyqtSlot(bool)
    def update_recording_indicator(self, is_recording: bool):
        if is_recording:
            self.recording_indicator.setText("🔴")
            self.recording_indicator.setStyleSheet("font-size: 20px; color: red;")
        else:
            self.recording_indicator.setText("⚫")
            self.recording_indicator.setStyleSheet("font-size: 20px; color: gray;")
```

## Phase 5: Dependency Injection & Configuration (Days 14-15)

### Step 5.1: DI Container

**File: `src/core/dependency_injection.py`**
```python
from typing import Dict, Type, Any, Callable
import inspect

class Container:
    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
    
    def register_singleton(self, interface: Type, implementation: Any) -> None:
        self._services[interface] = implementation
    
    def register_factory(self, interface: Type, factory: Callable) -> None:
        self._factories[interface] = factory
    
    def resolve(self, interface: Type) -> Any:
        # Check if singleton exists
        if interface in self._services:
            return self._services[interface]
        
        # Check if factory exists
        if interface in self._factories:
            instance = self._factories[interface]()
            self._services[interface] = instance
            return instance
        
        raise ValueError(f"No registration found for {interface}")
    
    def auto_wire(self, cls: Type) -> Any:
        # Get constructor parameters
        sig = inspect.signature(cls.__init__)
        params = {}
        
        for name, param in sig.parameters.items():
            if name == 'self':
                continue
            if param.annotation != param.empty:
                params[name] = self.resolve(param.annotation)
        
        return cls(**params)
```

### Step 5.2: Application Bootstrap

**File: `src/core/bootstrap.py`**
```python
from core.dependency_injection import Container
from domain.interfaces.audio_recorder import IAudioRecorder
from domain.interfaces.transcriber import ITranscriber
from infrastructure.audio.sounddevice_recorder import SoundDeviceRecorder
from infrastructure.transcription.whisper_adapter import WhisperAdapter
from application.use_cases.record_and_transcribe import RecordAndTranscribeUseCase

def create_container(config: dict) -> Container:
    container = Container()
    
    # Register infrastructure
    container.register_factory(
        IAudioRecorder,
        lambda: SoundDeviceRecorder(
            sample_rate=config['audio']['sample_rate'],
            channels=config['audio']['channels']
        )
    )
    
    container.register_factory(
        ITranscriber,
        lambda: WhisperAdapter()
    )
    
    # Register use cases
    container.register_factory(
        RecordAndTranscribeUseCase,
        lambda: container.auto_wire(RecordAndTranscribeUseCase)
    )
    
    return container
```

## Phase 6: Testing Strategy (Days 16-18)

### Step 6.1: Unit Tests

**File: `tests/unit/domain/test_voice_command_parser.py`**
```python
import pytest
from domain.services.voice_command_parser import VoiceCommandParser

class TestVoiceCommandParser:
    def setup_method(self):
        self.parser = VoiceCommandParser()
    
    def test_parse_execute_command(self):
        command = self.parser.parse("execute mode python main.py")
        assert command.text == "python main.py"
        assert command.execute == True
        assert command.command_type == "execute"
    
    def test_parse_regular_text(self):
        command = self.parser.parse("This is regular text")
        assert command.text == "This is regular text"
        assert command.execute == False
        assert command.command_type == "text"
```

### Step 6.2: Integration Tests

**File: `tests/integration/test_recording_flow.py`**
```python
import pytest
from unittest.mock import Mock, patch
import numpy as np
from application.use_cases.record_and_transcribe import RecordAndTranscribeUseCase

class TestRecordingFlow:
    @patch('infrastructure.audio.sounddevice_recorder.sd')
    def test_full_recording_flow(self, mock_sd):
        # Setup
        mock_recorder = Mock()
        mock_transcriber = Mock()
        mock_parser = Mock()
        
        use_case = RecordAndTranscribeUseCase(
            mock_recorder, mock_transcriber, mock_parser
        )
        
        # Configure mocks
        audio_data = np.random.rand(16000)  # 1 second of audio
        mock_recorder.stop_recording.return_value = audio_data
        mock_transcriber.transcribe.return_value = Mock(text="test command")
        mock_parser.parse.return_value = Mock(text="test command", execute=False)
        
        # Execute
        response = use_case.execute(Mock())
        
        # Assert
        assert response.success == True
        assert response.text == "test command"
        assert response.duration == 1.0
```

## Phase 7: Migration & Deployment (Days 19-21)

### Step 7.1: Parallel Implementation

**File: `main.py`**
```python
import argparse
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='base')
    parser.add_argument('--use-legacy', action='store_true',
                       help='Use legacy monolithic implementation')
    args = parser.parse_args()
    
    if args.use_legacy:
        # Import and run legacy code
        from speech_to_text_gui import main as legacy_main
        legacy_main()
    else:
        # Run new modular implementation
        from src.presentation.gui.main_window import ModularMainWindow
        from src.core.bootstrap import create_container
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication(sys.argv)
        
        # Load configuration
        config = load_config()
        
        # Create DI container
        container = create_container(config)
        
        # Create and show window
        window = ModularMainWindow(container)
        window.show()
        
        sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

### Step 7.2: Feature Toggle Configuration

**File: `config/features.yaml`**
```yaml
features:
  use_new_architecture: false
  enable_voice_commands: true
  enable_window_targeting: true
  enable_auto_execute: true
  
migration:
  parallel_run: true
  deprecation_warnings: true
  legacy_compatibility: true
```

## Rollout Schedule

### Week 1: Foundation
- Days 1-3: Implement domain layer
- Days 4-5: Code review and testing

### Week 2: Infrastructure
- Days 6-8: Build infrastructure adapters
- Days 9-10: Integration testing

### Week 3: Application Layer
- Days 11-12: Implement use cases
- Days 13-14: Service layer development

### Week 4: Presentation
- Days 15-16: Refactor GUI components
- Days 17-18: CLI and API interfaces

### Week 5: Testing & Deployment
- Days 19-20: Comprehensive testing
- Day 21: Production deployment

## Rollback Plan

1. Keep legacy code intact during migration
2. Use feature flags for gradual rollout
3. Maintain backward compatibility
4. Have automated rollback scripts ready
5. Monitor metrics and user feedback

## Success Criteria

- [ ] All unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Performance benchmarks met (<100ms UI response)
- [ ] No regression bugs reported
- [ ] Code review approved by team
- [ ] Documentation updated
- [ ] User acceptance testing passed

## Post-Refactoring Tasks

1. Remove legacy code after stability period
2. Performance optimization
3. Add monitoring and telemetry
4. Create developer documentation
5. Conduct team knowledge transfer session