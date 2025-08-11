from dataclasses import dataclass
from typing import Optional

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.domain.interfaces.text_output import ITextOutput
from src.domain.entities.voice_command import VoiceCommand
from src.domain.value_objects.window_target import WindowTarget
from src.domain.value_objects.transcription_text import TranscriptionText


@dataclass
class SendTextRequest:
    """Request DTO for sending text to a window."""
    text: str
    target: WindowTarget
    execute: bool = False
    add_leading_space: bool = True


@dataclass
class SendTextResponse:
    """Response DTO for sending text to a window."""
    success: bool
    error_message: Optional[str] = None
    text_sent: Optional[str] = None
    target_window: Optional[WindowTarget] = None


class SendTextUseCase:
    """Use case for sending text to a target window."""
    
    def __init__(self, text_output: ITextOutput):
        """Initialize the use case with required dependencies.
        
        Args:
            text_output: Text output service
        """
        self.text_output = text_output
    
    def execute(self, request: SendTextRequest) -> SendTextResponse:
        """Execute the text sending process.
        
        Args:
            request: Request containing text and target window
            
        Returns:
            Response indicating success or failure
        """
        try:
            # Validate request
            if not request.text or not request.text.strip():
                return SendTextResponse(
                    success=False,
                    error_message="No text to send"
                )
            
            # Process text
            transcription_text = TranscriptionText.create(request.text)
            
            # Add leading space if requested
            if request.add_leading_space:
                transcription_text = transcription_text.add_leading_space()
            
            # Validate target window if not current focus
            if not request.target.is_current_focus:
                if not self.text_output.is_window_valid(request.target):
                    return SendTextResponse(
                        success=False,
                        error_message=f"Target window no longer exists: {request.target.title}"
                    )
            
            # Send text
            success = self.text_output.send_text(
                text=transcription_text.cleaned_text,
                target=request.target,
                execute=request.execute
            )
            
            if success:
                return SendTextResponse(
                    success=True,
                    text_sent=transcription_text.cleaned_text,
                    target_window=request.target
                )
            else:
                return SendTextResponse(
                    success=False,
                    error_message="Failed to send text to target window"
                )
                
        except Exception as e:
            return SendTextResponse(
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def execute_voice_command(self, command: VoiceCommand, target: WindowTarget) -> SendTextResponse:
        """Execute a voice command by sending its text to a window.
        
        Args:
            command: Voice command to execute
            target: Target window
            
        Returns:
            Response indicating success or failure
        """
        if not command.has_text():
            return SendTextResponse(
                success=False,
                error_message="Voice command has no text to send"
            )
        
        request = SendTextRequest(
            text=command.text,
            target=target,
            execute=command.should_execute(),
            add_leading_space=True
        )
        
        return self.execute(request)