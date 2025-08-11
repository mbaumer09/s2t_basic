from dataclasses import dataclass
from typing import Optional, List, Tuple

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.domain.interfaces.audio_recorder import IAudioRecorder
from src.domain.entities.recording_session import RecordingSession, RecordingState


@dataclass
class StartRecordingRequest:
    """Request DTO for starting a recording."""
    device_id: Optional[int] = None


@dataclass
class StartRecordingResponse:
    """Response DTO for starting a recording."""
    success: bool
    session: Optional[RecordingSession] = None
    error_message: Optional[str] = None


@dataclass
class StopRecordingRequest:
    """Request DTO for stopping a recording."""
    session_id: str


@dataclass
class StopRecordingResponse:
    """Response DTO for stopping a recording."""
    success: bool
    session: Optional[RecordingSession] = None
    audio_duration: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class GetDevicesResponse:
    """Response DTO for getting available devices."""
    devices: List[Tuple[int, str]]
    current_device: Optional[Tuple[int, str]] = None


class ManageRecordingUseCase:
    """Use case for managing audio recording sessions."""
    
    def __init__(self, audio_recorder: IAudioRecorder):
        """Initialize the use case with required dependencies.
        
        Args:
            audio_recorder: Audio recording service
        """
        self.audio_recorder = audio_recorder
        self.current_session: Optional[RecordingSession] = None
    
    def start_recording(self, request: StartRecordingRequest) -> StartRecordingResponse:
        """Start a new recording session.
        
        Args:
            request: Request containing recording parameters
            
        Returns:
            Response containing session information or error
        """
        try:
            # Check if already recording
            if self.audio_recorder.is_recording():
                return StartRecordingResponse(
                    success=False,
                    error_message="Already recording"
                )
            
            # Get device info
            device_id = request.device_id
            device_name = None
            
            if device_id is not None:
                # Validate device exists
                devices = self.audio_recorder.get_available_devices()
                device_found = False
                for dev_id, dev_name in devices:
                    if dev_id == device_id:
                        device_name = dev_name
                        device_found = True
                        break
                
                if not device_found:
                    return StartRecordingResponse(
                        success=False,
                        error_message=f"Device {device_id} not found"
                    )
            else:
                # Use current device
                current = self.audio_recorder.get_current_device()
                if current:
                    device_id, device_name = current
            
            # Create session
            session = RecordingSession.create(
                device_id=device_id,
                device_name=device_name
            )
            
            # Start recording
            self.audio_recorder.start_recording(device_id)
            session.start()
            
            # Store current session
            self.current_session = session
            
            return StartRecordingResponse(
                success=True,
                session=session
            )
            
        except Exception as e:
            return StartRecordingResponse(
                success=False,
                error_message=f"Failed to start recording: {str(e)}"
            )
    
    def stop_recording(self, request: StopRecordingRequest) -> StopRecordingResponse:
        """Stop a recording session.
        
        Args:
            request: Request containing session ID
            
        Returns:
            Response containing session information or error
        """
        try:
            # Validate session
            if not self.current_session or self.current_session.id != request.session_id:
                return StopRecordingResponse(
                    success=False,
                    error_message="Invalid session ID"
                )
            
            # Check if recording
            if not self.audio_recorder.is_recording():
                return StopRecordingResponse(
                    success=False,
                    error_message="Not currently recording"
                )
            
            # Stop recording
            audio_data = self.audio_recorder.stop_recording()
            self.current_session.stop()
            
            # Get duration
            duration = audio_data.duration_seconds
            
            return StopRecordingResponse(
                success=True,
                session=self.current_session,
                audio_duration=duration
            )
            
        except Exception as e:
            if self.current_session:
                self.current_session.fail(str(e))
            
            return StopRecordingResponse(
                success=False,
                error_message=f"Failed to stop recording: {str(e)}"
            )
    
    def get_available_devices(self) -> GetDevicesResponse:
        """Get available audio input devices.
        
        Returns:
            Response containing list of devices
        """
        devices = self.audio_recorder.get_available_devices()
        current = self.audio_recorder.get_current_device()
        
        return GetDevicesResponse(
            devices=devices,
            current_device=current
        )
    
    def set_device(self, device_id: int) -> bool:
        """Set the audio input device.
        
        Args:
            device_id: ID of the device to use
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.audio_recorder.set_device(device_id)
            return True
        except Exception:
            return False
    
    def get_current_session(self) -> Optional[RecordingSession]:
        """Get the current recording session.
        
        Returns:
            Current session or None
        """
        return self.current_session
    
    def is_recording(self) -> bool:
        """Check if currently recording.
        
        Returns:
            True if recording, False otherwise
        """
        return self.audio_recorder.is_recording()