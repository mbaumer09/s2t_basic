from abc import ABC, abstractmethod
from typing import Callable, Optional


class IHotkeyHandler(ABC):
    """Interface for hotkey handling functionality."""
    
    @abstractmethod
    def register_hotkey(
        self,
        key: str,
        on_press: Optional[Callable[[], None]] = None,
        on_release: Optional[Callable[[], None]] = None
    ) -> None:
        """Register a hotkey with press and/or release handlers.
        
        Args:
            key: The key to register (e.g., 'right ctrl', 'f13')
            on_press: Callback to execute when key is pressed
            on_release: Callback to execute when key is released
        """
        pass
    
    @abstractmethod
    def unregister_hotkey(self, key: str) -> None:
        """Unregister a previously registered hotkey.
        
        Args:
            key: The key to unregister
        """
        pass
    
    @abstractmethod
    def start_listening(self) -> None:
        """Start listening for hotkey events."""
        pass
    
    @abstractmethod
    def stop_listening(self) -> None:
        """Stop listening for hotkey events."""
        pass
    
    @abstractmethod
    def is_listening(self) -> bool:
        """Check if currently listening for hotkey events.
        
        Returns:
            True if listening, False otherwise
        """
        pass