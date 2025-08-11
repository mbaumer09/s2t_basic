from dataclasses import dataclass
from typing import Optional

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.domain.interfaces.audio_recorder import IAudioRecorder
from src.domain.interfaces.transcriber import ITranscriber
from src.domain.services.voice_command_parser import VoiceCommandParser
from src.domain.services.transcription_validator import TranscriptionValidator
from src.domain.services.audio_processor import AudioProcessor
from src.domain.entities.transcription import Transcription
from src.domain.entities.voice_command import VoiceCommand
from src.domain.entities.recording_session import RecordingSession


@dataclass
class RecordAndTranscribeRequest:
    """Request DTO for recording and transcribing audio."""
    session_id: str
    language: str = 'en'
    normalize_audio: bool = True
    trim_silence: bool = True
    apply_noise_gate: bool = False


@dataclass
class RecordAndTranscribeResponse:
    """Response DTO for recording and transcribing audio."""
    success: bool
    transcription: Optional[Transcription] = None
    voice_command: Optional[VoiceCommand] = None
    error_message: Optional[str] = None
    session: Optional[RecordingSession] = None


class RecordAndTranscribeUseCase:
    """Use case for recording audio and transcribing it to text."""
    
    def __init__(
        self,
        audio_recorder: IAudioRecorder,
        transcriber: ITranscriber,
        command_parser: VoiceCommandParser,
        validator: TranscriptionValidator,
        audio_processor: AudioProcessor
    ):
        """Initialize the use case with required dependencies.
        
        Args:
            audio_recorder: Audio recording service
            transcriber: Transcription service
            command_parser: Voice command parsing service
            validator: Transcription validation service
            audio_processor: Audio processing service
        """
        self.audio_recorder = audio_recorder
        self.transcriber = transcriber
        self.command_parser = command_parser
        self.validator = validator
        self.audio_processor = audio_processor
    
    def execute(self, request: RecordAndTranscribeRequest) -> RecordAndTranscribeResponse:
        """Execute the recording and transcription process.
        
        Args:
            request: Request containing recording parameters
            
        Returns:
            Response containing transcription result or error
        """
        # Create recording session
        session = RecordingSession.create()
        
        try:
            # Start recording
            session.start()
            
            # Note: In real implementation, this would be triggered by hotkey release
            # For now, we assume recording is already complete
            if not self.audio_recorder.is_recording():
                return RecordAndTranscribeResponse(
                    success=False,
                    error_message="Recording not started",
                    session=session
                )
            
            # Stop recording and get audio data
            audio_data = self.audio_recorder.stop_recording()
            session.stop()
            
            # Validate audio
            is_valid, error_msg = self.validator.validate_audio(audio_data)
            if not is_valid:
                session.fail(error_msg)
                return RecordAndTranscribeResponse(
                    success=False,
                    error_message=error_msg,
                    session=session
                )
            
            # Process audio if requested
            if request.trim_silence:
                audio_data = self.audio_processor.trim_silence(audio_data)
            
            if request.normalize_audio:
                audio_data = self.audio_processor.normalize_audio(audio_data)
            
            if request.apply_noise_gate:
                audio_data = self.audio_processor.apply_noise_gate(audio_data)
            
            # Transcribe audio
            transcription = self.transcriber.transcribe(
                audio_data,
                language=request.language
            )
            
            # Validate transcription
            is_valid, error_msg = self.validator.validate_transcription(
                transcription,
                audio_data
            )
            
            if not is_valid:
                session.fail(error_msg)
                return RecordAndTranscribeResponse(
                    success=False,
                    error_message=error_msg,
                    session=session
                )
            
            # Parse voice commands
            voice_command = self.command_parser.parse(transcription.text)
            
            # Complete session
            session.complete()
            
            return RecordAndTranscribeResponse(
                success=True,
                transcription=transcription,
                voice_command=voice_command,
                session=session
            )
            
        except Exception as e:
            session.fail(str(e))
            return RecordAndTranscribeResponse(
                success=False,
                error_message=f"Unexpected error: {str(e)}",
                session=session
            )