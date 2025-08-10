from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from domain.value_objects.window_target import WindowTarget


class ITextOutput(ABC):
    """Interface for text output functionality."""
    
    @abstractmethod
    def send_text(
        self,
        text: str,
        target: WindowTarget,
        execute: bool = False
    ) -> bool:
        """Send text to the specified window target.
        
        Args:
            text: The text to send
            target: The window target to send text to
            execute: Whether to press Enter after sending text
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_available_windows(self) -> List[WindowTarget]:
        """Get list of available windows that can receive text.
        
        Returns:
            List of WindowTarget objects
        """
        pass
    
    @abstractmethod
    def get_current_window(self) -> WindowTarget:
        """Get the currently focused window.
        
        Returns:
            WindowTarget representing the current window
        """
        pass
    
    @abstractmethod
    def focus_window(self, target: WindowTarget) -> bool:
        """Focus the specified window.
        
        Args:
            target: The window to focus
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def is_window_valid(self, target: WindowTarget) -> bool:
        """Check if a window target is still valid (exists).
        
        Args:
            target: The window target to check
            
        Returns:
            True if the window exists, False otherwise
        """
        pass