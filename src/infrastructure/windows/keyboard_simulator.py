import time
from typing import Optional, Callable
import keyboard

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.domain.interfaces.hotkey_handler import IHotkeyHandler


class KeyboardSimulator(IHotkeyHandler):
    """Keyboard implementation of the hotkey handler interface."""
    
    def __init__(self):
        """Initialize the keyboard simulator."""
        self.registered_hotkeys = {}
        self.listening = False
        self.debounce_time = 0.5
        self.last_release_times = {}
    
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
        # Store handlers
        self.registered_hotkeys[key] = {
            'on_press': on_press,
            'on_release': on_release,
            'press_hook': None,
            'release_hook': None
        }
        
        # Register keyboard hooks if listening
        if self.listening:
            self._register_key_hooks(key)
    
    def unregister_hotkey(self, key: str) -> None:
        """Unregister a previously registered hotkey.
        
        Args:
            key: The key to unregister
        """
        if key in self.registered_hotkeys:
            # Remove keyboard hooks
            self._unregister_key_hooks(key)
            
            # Remove from registry
            del self.registered_hotkeys[key]
            
            # Clean up last release time
            if key in self.last_release_times:
                del self.last_release_times[key]
    
    def start_listening(self) -> None:
        """Start listening for hotkey events."""
        if self.listening:
            return
        
        self.listening = True
        
        # Register all hotkey hooks
        for key in self.registered_hotkeys:
            self._register_key_hooks(key)
    
    def stop_listening(self) -> None:
        """Stop listening for hotkey events."""
        if not self.listening:
            return
        
        self.listening = False
        
        # Unregister all hotkey hooks
        for key in list(self.registered_hotkeys.keys()):
            self._unregister_key_hooks(key)
    
    def is_listening(self) -> bool:
        """Check if currently listening for hotkey events.
        
        Returns:
            True if listening, False otherwise
        """
        return self.listening
    
    def _register_key_hooks(self, key: str) -> None:
        """Register keyboard hooks for a specific key.
        
        Args:
            key: The key to register hooks for
        """
        if key not in self.registered_hotkeys:
            return
        
        handlers = self.registered_hotkeys[key]
        
        # Create debounced handlers
        def on_press_handler(_):
            if handlers['on_press']:
                handlers['on_press']()
        
        def on_release_handler(_):
            # Debounce release events
            current_time = time.time()
            last_release = self.last_release_times.get(key, 0)
            
            if current_time - last_release >= self.debounce_time:
                self.last_release_times[key] = current_time
                if handlers['on_release']:
                    handlers['on_release']()
        
        # Register hooks
        if handlers['on_press']:
            handlers['press_hook'] = keyboard.on_press_key(key, on_press_handler)
        
        if handlers['on_release']:
            handlers['release_hook'] = keyboard.on_release_key(key, on_release_handler)
    
    def _unregister_key_hooks(self, key: str) -> None:
        """Unregister keyboard hooks for a specific key.
        
        Args:
            key: The key to unregister hooks for
        """
        if key not in self.registered_hotkeys:
            return
        
        handlers = self.registered_hotkeys[key]
        
        # Unhook press handler
        if handlers['press_hook']:
            try:
                keyboard.unhook(handlers['press_hook'])
            except:
                pass
            handlers['press_hook'] = None
        
        # Unhook release handler
        if handlers['release_hook']:
            try:
                keyboard.unhook(handlers['release_hook'])
            except:
                pass
            handlers['release_hook'] = None
    
    def set_debounce_time(self, seconds: float) -> None:
        """Set the debounce time for key releases.
        
        Args:
            seconds: Debounce time in seconds
        """
        self.debounce_time = max(0.0, seconds)
    
    def is_key_pressed(self, key: str) -> bool:
        """Check if a key is currently pressed.
        
        Args:
            key: The key to check
            
        Returns:
            True if the key is pressed, False otherwise
        """
        try:
            return keyboard.is_pressed(key)
        except:
            return False
    
    def wait_for_key_release(self, key: str, timeout: float = 5.0) -> bool:
        """Wait for a key to be released.
        
        Args:
            key: The key to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if key was released, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if not self.is_key_pressed(key):
                return True
            time.sleep(0.01)
        
        return False
    
    def __del__(self):
        """Cleanup on destruction."""
        self.stop_listening()