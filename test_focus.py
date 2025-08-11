#!/usr/bin/env python3
"""
Quick test script to debug window focus and execution issues.
"""
import time
import keyboard
import win32gui
import win32con
import win32api

def get_current_window_info():
    """Get info about the currently focused window."""
    hwnd = win32gui.GetForegroundWindow()
    if hwnd:
        title = win32gui.GetWindowText(hwnd)
        class_name = win32gui.GetClassName(hwnd)
        thread_id, process_id = win32gui.GetWindowThreadProcessId(hwnd)
        return {
            'hwnd': hwnd,
            'title': title,
            'class': class_name,
            'thread_id': thread_id,
            'process_id': process_id
        }
    return None

def test_focus_and_execution():
    """Test window focus changes and key execution."""
    print("Focus Test - Click on a terminal/command prompt, then press SPACE to test")
    keyboard.wait('space')
    
    # Get current window info
    window_info = get_current_window_info()
    if not window_info:
        print("No focused window found")
        return
    
    print(f"Current window: {window_info['title']}")
    print(f"Class: {window_info['class']}")
    print(f"Handle: {window_info['hwnd']}")
    
    # Test 1: Type without changing focus
    print("\nTest 1: Typing to current focus...")
    keyboard.write("echo 'Test 1 - direct typing'")
    time.sleep(0.5)
    keyboard.press_and_release('enter')
    
    time.sleep(2)
    
    # Test 2: Force focus then type
    print("Test 2: Setting focus then typing...")
    try:
        current_hwnd = win32gui.GetForegroundWindow()
        print(f"Current foreground: {current_hwnd}")
        
        # Try to set foreground
        result = win32gui.SetForegroundWindow(window_info['hwnd'])
        print(f"SetForegroundWindow result: {result}")
        
        time.sleep(0.1)
        
        # Check if focus actually changed
        new_hwnd = win32gui.GetForegroundWindow()
        print(f"New foreground: {new_hwnd}")
        print(f"Focus changed: {new_hwnd == window_info['hwnd']}")
        
        keyboard.write("echo 'Test 2 - after focus change'")
        time.sleep(0.1)
        keyboard.press_and_release('enter')
        
    except Exception as e:
        print(f"Focus test failed: {e}")
    
    time.sleep(2)
    
    # Test 3: Alternative focus methods
    print("Test 3: Alternative focus methods...")
    try:
        # Method 1: ShowWindow + SetForegroundWindow
        win32gui.ShowWindow(window_info['hwnd'], win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(window_info['hwnd'])
        time.sleep(0.1)
        
        keyboard.write("echo 'Test 3 - ShowWindow method'")
        time.sleep(0.1)
        keyboard.press_and_release('enter')
        
    except Exception as e:
        print(f"Alternative focus method failed: {e}")

def test_window_messages():
    """Test sending messages directly to window."""
    print("\nTesting direct window messages...")
    print("Click on target window, then press 'm' to test message sending")
    keyboard.wait('m')
    
    window_info = get_current_window_info()
    if not window_info:
        print("No focused window")
        return
        
    print(f"Sending messages to: {window_info['title']}")
    
    # Try sending text via WM_CHAR messages
    try:
        test_text = "hello"
        for char in test_text:
            win32api.SendMessage(window_info['hwnd'], win32con.WM_CHAR, ord(char), 0)
            time.sleep(0.01)
        
        # Send Enter key
        win32api.SendMessage(window_info['hwnd'], win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
        time.sleep(0.01)
        win32api.SendMessage(window_info['hwnd'], win32con.WM_KEYUP, win32con.VK_RETURN, 0)
        
        print("Messages sent successfully")
        
    except Exception as e:
        print(f"Message sending failed: {e}")

if __name__ == "__main__":
    print("Window Focus & Execution Test")
    print("=============================")
    print("This will test different methods for window focus and key execution")
    print("\nPress 'f' to start focus tests, 'm' for message tests, 'q' to quit")
    
    while True:
        key = keyboard.read_event()
        if key.event_type == keyboard.KEY_DOWN:
            if key.name == 'f':
                test_focus_and_execution()
            elif key.name == 'm':
                test_window_messages()
            elif key.name == 'q':
                print("Exiting...")
                break