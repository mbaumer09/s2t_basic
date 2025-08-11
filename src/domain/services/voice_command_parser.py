from typing import List, Optional
from src.domain.entities.voice_command import VoiceCommand, CommandType
from src.domain.value_objects.transcription_text import TranscriptionText


class VoiceCommandParser:
    """Domain service for parsing voice commands from transcribed text."""
    
    # Command patterns that trigger execution
    EXECUTE_PATTERNS = [
        'execute mode',
        'execute command',
        'execute',
        'run command',
        'run this',
        'command mode'
    ]
    
    # Command patterns for window targeting
    WINDOW_PATTERNS = [
        'target window',
        'send to window',
        'window'
    ]
    
    # Command patterns for configuration
    CONFIG_PATTERNS = [
        'config',
        'configure',
        'settings',
        'setup'
    ]
    
    def parse(self, text: str) -> VoiceCommand:
        """Parse a voice command from transcribed text.
        
        Args:
            text: The transcribed text to parse
            
        Returns:
            VoiceCommand entity representing the parsed command
        """
        if not text or not text.strip():
            return VoiceCommand.create_text("")
        
        transcription = TranscriptionText.create(text)
        
        # Check for execute commands
        has_execute, execute_prefix = transcription.contains_command_prefix(self.EXECUTE_PATTERNS)
        if has_execute:
            cleaned_text = transcription.remove_prefix(execute_prefix)
            return VoiceCommand.create_execute(
                text=cleaned_text.cleaned_text,
                original_text=text
            )
        
        # Check for window targeting commands
        has_window, window_prefix = transcription.contains_command_prefix(self.WINDOW_PATTERNS)
        if has_window:
            cleaned_text = transcription.remove_prefix(window_prefix)
            return VoiceCommand(
                command_type=CommandType.WINDOW_TARGET,
                text=cleaned_text.cleaned_text,
                original_text=text,
                execute=False,
                target_window=cleaned_text.cleaned_text
            )
        
        # Check for configuration commands
        has_config, config_prefix = transcription.contains_command_prefix(self.CONFIG_PATTERNS)
        if has_config:
            cleaned_text = transcription.remove_prefix(config_prefix)
            return VoiceCommand(
                command_type=CommandType.CONFIG,
                text=cleaned_text.cleaned_text,
                original_text=text,
                execute=False
            )
        
        # Default to regular text command
        return VoiceCommand.create_text(transcription.cleaned_text)
    
    def parse_multiple(self, texts: List[str]) -> List[VoiceCommand]:
        """Parse multiple voice commands.
        
        Args:
            texts: List of transcribed texts to parse
            
        Returns:
            List of VoiceCommand entities
        """
        return [self.parse(text) for text in texts]
    
    def extract_command_type(self, text: str) -> CommandType:
        """Extract just the command type without full parsing.
        
        Args:
            text: The text to analyze
            
        Returns:
            The detected CommandType
        """
        transcription = TranscriptionText.create(text)
        
        if transcription.contains_command_prefix(self.EXECUTE_PATTERNS)[0]:
            return CommandType.EXECUTE
        elif transcription.contains_command_prefix(self.WINDOW_PATTERNS)[0]:
            return CommandType.WINDOW_TARGET
        elif transcription.contains_command_prefix(self.CONFIG_PATTERNS)[0]:
            return CommandType.CONFIG
        else:
            return CommandType.TEXT
    
    def is_execute_command(self, text: str) -> bool:
        """Quick check if text is an execute command.
        
        Args:
            text: The text to check
            
        Returns:
            True if the text is an execute command
        """
        return self.extract_command_type(text) == CommandType.EXECUTE