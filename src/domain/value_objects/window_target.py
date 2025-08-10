from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class WindowTarget:
    """Value object representing a target window for text output."""
    
    handle: Optional[int]
    title: str
    process_name: Optional[str] = None
    
    @classmethod
    def create_current_focus(cls) -> 'WindowTarget':
        """Create a WindowTarget for the current focused window."""
        return cls(
            handle=None,
            title="Current Focus",
            process_name=None
        )
    
    @classmethod
    def create_specific_window(cls, handle: int, title: str, process_name: Optional[str] = None) -> 'WindowTarget':
        """Create a WindowTarget for a specific window."""
        if handle <= 0:
            raise ValueError(f"Window handle must be positive, got {handle}")
        
        if not title or not title.strip():
            raise ValueError("Window title cannot be empty")
        
        return cls(
            handle=handle,
            title=title,
            process_name=process_name
        )
    
    @property
    def is_current_focus(self) -> bool:
        """Check if this target represents the current focused window."""
        return self.handle is None
    
    @property
    def display_name(self) -> str:
        """Get a display-friendly name for the window."""
        if self.is_current_focus:
            return "Current Focus (Default)"
        
        # Truncate long titles
        if len(self.title) > 60:
            return self.title[:57] + "..."
        return self.title
    
    def matches_handle(self, handle: int) -> bool:
        """Check if this target matches a given window handle."""
        if self.is_current_focus:
            return False
        return self.handle == handle
    
    def __str__(self) -> str:
        if self.is_current_focus:
            return "WindowTarget(Current Focus)"
        return f"WindowTarget(handle={self.handle}, title='{self.display_name}')"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, WindowTarget):
            return self.handle == other.handle and self.title == other.title
        return False
    
    def __hash__(self) -> int:
        return hash((self.handle, self.title))