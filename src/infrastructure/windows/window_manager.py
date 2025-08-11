import time
from typing import List, Optional
import win32gui
import win32con
import keyboard

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.domain.interfaces.text_output import ITextOutput
from src.domain.value_objects.window_target import WindowTarget


class WindowManager(ITextOutput):
    """Windows implementation of the text output interface."""
    
    def __init__(self):
        """Initialize the window manager."""
        self.type_delay = 0.0  # Delay between keystrokes
        self.focus_delay = 0.1  # Delay after focusing window
        self.execute_delay = 0.1  # Delay before pressing Enter
    
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
        try:
            # Save current window if we need to restore it
            original_window = None
            if not target.is_current_focus:
                original_window = win32gui.GetForegroundWindow()
            
            # Focus target window if specified
            if not target.is_current_focus:
                if not self.focus_window(target):
                    return False
            
            # Wait for any modifier keys to be released
            self._wait_for_modifiers_release()
            
            # Type the text (with leading space by default)
            text_to_type = ' ' + text if text and not text.startswith(' ') else text
            keyboard.write(text_to_type, delay=self.type_delay)
            
            # Execute if requested
            if execute:
                time.sleep(self.execute_delay)
                
                # Ensure we're still focused on the right window
                if not target.is_current_focus:
                    current = win32gui.GetForegroundWindow()
                    if current != target.handle:
                        # Try to refocus
                        self.focus_window(target)
                        time.sleep(0.05)
                
                # Move cursor to end and press Enter
                keyboard.press_and_release('end')
                time.sleep(0.05)
                keyboard.press_and_release('enter')
            
            # Restore original window if we changed focus
            if original_window and not target.is_current_focus:
                try:
                    win32gui.SetForegroundWindow(original_window)
                except:
                    pass  # Don't fail if we can't restore
            
            return True
            
        except Exception as e:
            print(f"Error sending text: {e}")
            return False
    
    def get_available_windows(self) -> List[WindowTarget]:
        """Get list of available windows that can receive text.
        
        Returns:
            List of WindowTarget objects
        """
        windows = []
        
        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title and title.strip():
                    try:
                        # Get process name if possible
                        process_name = None
                        # Note: Getting process name requires additional Win32 API calls
                        # For simplicity, we'll skip it for now
                        
                        windows.append(WindowTarget.create_specific_window(
                            handle=hwnd,
                            title=title,
                            process_name=process_name
                        ))
                    except ValueError:
                        pass  # Skip invalid windows
            return True
        
        win32gui.EnumWindows(enum_callback, None)
        
        # Sort by title
        windows.sort(key=lambda w: w.title.lower())
        
        # Add current focus option at the beginning
        windows.insert(0, WindowTarget.create_current_focus())
        
        return windows
    
    def get_current_window(self) -> WindowTarget:
        """Get the currently focused window.
        
        Returns:
            WindowTarget representing the current window
        """
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                title = win32gui.GetWindowText(hwnd)
                if title:
                    return WindowTarget.create_specific_window(
                        handle=hwnd,
                        title=title
                    )
        except Exception as e:
            print(f"Error getting current window: {e}")
        
        return WindowTarget.create_current_focus()
    
    def focus_window(self, target: WindowTarget) -> bool:
        """Focus the specified window.
        
        Args:
            target: The window to focus
            
        Returns:
            True if successful, False otherwise
        """
        if target.is_current_focus:
            return True  # Already using current focus
        
        try:
            # Check if window still exists
            if not self.is_window_valid(target):
                return False
            
            # Attempt to bring window to foreground
            win32gui.SetForegroundWindow(target.handle)
            time.sleep(self.focus_delay)
            
            # Verify focus change
            current = win32gui.GetForegroundWindow()
            return current == target.handle
            
        except Exception as e:
            print(f"Error focusing window: {e}")
            return False
    
    def is_window_valid(self, target: WindowTarget) -> bool:
        """Check if a window target is still valid (exists).
        
        Args:
            target: The window target to check
            
        Returns:
            True if the window exists, False otherwise
        """
        if target.is_current_focus:
            return True  # Current focus is always valid
        
        try:
            return win32gui.IsWindow(target.handle)
        except:
            return False
    
    def _wait_for_modifiers_release(self, timeout: float = 0.5) -> None:
        """Wait for modifier keys to be released.
        
        Args:
            timeout: Maximum time to wait in seconds
        """
        start_time = time.time()
        modifiers = ['shift', 'ctrl', 'alt', 'cmd']
        
        while time.time() - start_time < timeout:
            all_released = True
            for mod in modifiers:
                if keyboard.is_pressed(mod):
                    all_released = False
                    break
            
            if all_released:
                break
            
            time.sleep(0.01)
    
    def set_delays(
        self,
        type_delay: Optional[float] = None,
        focus_delay: Optional[float] = None,
        execute_delay: Optional[float] = None
    ) -> None:
        """Configure delays for various operations.
        
        Args:
            type_delay: Delay between keystrokes
            focus_delay: Delay after focusing window
            execute_delay: Delay before pressing Enter
        """
        if type_delay is not None:
            self.type_delay = type_delay
        if focus_delay is not None:
            self.focus_delay = focus_delay
        if execute_delay is not None:
            self.execute_delay = execute_delay