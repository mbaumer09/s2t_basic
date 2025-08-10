"""Unit tests for VoiceCommandParser domain service."""

import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.domain.services.voice_command_parser import VoiceCommandParser
from src.domain.entities.voice_command import CommandType


class TestVoiceCommandParser:
    """Test suite for VoiceCommandParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = VoiceCommandParser()
    
    def test_parse_regular_text(self):
        """Test parsing regular text without commands."""
        command = self.parser.parse("This is regular text")
        
        assert command.command_type == CommandType.TEXT
        assert command.text == "This is regular text"
        assert command.execute == False
        assert command.original_text == "This is regular text"
    
    def test_parse_execute_mode_command(self):
        """Test parsing execute mode command."""
        command = self.parser.parse("execute mode python main.py")
        
        assert command.command_type == CommandType.EXECUTE
        assert command.text == "python main.py"
        assert command.execute == True
        assert command.original_text == "execute mode python main.py"
    
    def test_parse_execute_command(self):
        """Test parsing execute command variation."""
        command = self.parser.parse("execute command npm test")
        
        assert command.command_type == CommandType.EXECUTE
        assert command.text == "npm test"
        assert command.execute == True
    
    def test_parse_run_command(self):
        """Test parsing run command variation."""
        command = self.parser.parse("run command git status")
        
        assert command.command_type == CommandType.EXECUTE
        assert command.text == "git status"
        assert command.execute == True
    
    def test_parse_case_insensitive(self):
        """Test that command parsing is case insensitive."""
        command = self.parser.parse("EXECUTE MODE test")
        
        assert command.command_type == CommandType.EXECUTE
        assert command.text == "test"
        assert command.execute == True
    
    def test_parse_empty_string(self):
        """Test parsing empty string."""
        command = self.parser.parse("")
        
        assert command.command_type == CommandType.TEXT
        assert command.text == ""
        assert command.execute == False
    
    def test_parse_none_input(self):
        """Test parsing None input."""
        command = self.parser.parse(None)
        
        assert command.command_type == CommandType.TEXT
        assert command.text == ""
        assert command.execute == False
    
    def test_parse_whitespace_only(self):
        """Test parsing whitespace-only string."""
        command = self.parser.parse("   \n\t  ")
        
        assert command.command_type == CommandType.TEXT
        assert command.text == ""
        assert command.execute == False
    
    def test_parse_window_target_command(self):
        """Test parsing window targeting command."""
        command = self.parser.parse("target window Visual Studio Code")
        
        assert command.command_type == CommandType.WINDOW_TARGET
        assert command.text == "Visual Studio Code"
        assert command.execute == False
        assert command.target_window == "Visual Studio Code"
    
    def test_parse_multiple_commands(self):
        """Test parsing multiple commands in batch."""
        texts = [
            "execute mode test",
            "normal text",
            "run command ls",
            ""
        ]
        
        commands = self.parser.parse_multiple(texts)
        
        assert len(commands) == 4
        assert commands[0].command_type == CommandType.EXECUTE
        assert commands[1].command_type == CommandType.TEXT
        assert commands[2].command_type == CommandType.EXECUTE
        assert commands[3].command_type == CommandType.TEXT
    
    def test_extract_command_type(self):
        """Test extracting command type without full parsing."""
        assert self.parser.extract_command_type("execute mode test") == CommandType.EXECUTE
        assert self.parser.extract_command_type("normal text") == CommandType.TEXT
        assert self.parser.extract_command_type("target window chrome") == CommandType.WINDOW_TARGET
    
    def test_is_execute_command(self):
        """Test quick check for execute commands."""
        assert self.parser.is_execute_command("execute mode test") == True
        assert self.parser.is_execute_command("run command test") == True
        assert self.parser.is_execute_command("normal text") == False
        assert self.parser.is_execute_command("target window test") == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])