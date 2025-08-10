from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CommandType(Enum):
    """Types of voice commands."""
    TEXT = "text"  # Regular text input
    EXECUTE = "execute"  # Execute command (press Enter)
    WINDOW_TARGET = "window_target"  # Target specific window
    CONFIG = "config"  # Configuration command


@dataclass
class VoiceCommand:
    """Domain entity representing a parsed voice command."""
    
    command_type: CommandType
    text: str
    original_text: str
    execute: bool = False
    target_window: Optional[str] = None
    
    @classmethod
    def create_text(cls, text: str) -> 'VoiceCommand':
        """Create a regular text command."""
        return cls(
            command_type=CommandType.TEXT,
            text=text,
            original_text=text,
            execute=False
        )
    
    @classmethod
    def create_execute(cls, text: str, original_text: str) -> 'VoiceCommand':
        """Create an execute command."""
        return cls(
            command_type=CommandType.EXECUTE,
            text=text,
            original_text=original_text,
            execute=True
        )
    
    def should_execute(self) -> bool:
        """Check if the command should be executed (Enter pressed)."""
        return self.execute or self.command_type == CommandType.EXECUTE
    
    def has_text(self) -> bool:
        """Check if the command has text to type."""
        return len(self.text.strip()) > 0
    
    def __str__(self) -> str:
        execute_str = " [EXECUTE]" if self.execute else ""
        return f"VoiceCommand({self.command_type.value}: '{self.text[:30]}...'{execute_str})"