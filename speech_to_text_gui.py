import os
import sys
import time
import queue
import threading
import tempfile
import argparse
import torch
import winsound
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf
import keyboard
import whisper
import pystray
from PIL import Image, ImageDraw
import win32gui
import win32con
import win32api
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, QLabel, 
                             QComboBox, QSystemTrayIcon, QMenu, QGroupBox,
                             QProgressBar, QCheckBox, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, pyqtSlot
from PyQt6.QtGui import QIcon, QPixmap, QFont, QTextCursor


class AudioWorker(QThread):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    recording_signal = pyqtSignal(bool)
    transcription_signal = pyqtSignal(str)
    
    def __init__(self, model_size='base'):
        super().__init__()
        self.recording = False
        self.audio_queue = queue.Queue()
        self.sample_rate = 16000
        self.channels = 1
        self.max_recording_duration = 30
        self.debounce_cooldown = 0.5
        self.last_release_time = 0
        self.hotkey = 'right ctrl'
        self.device = None
        self.model = None
        self.model_size = model_size
        self.recording_start_time = 0
        self.use_gpu = torch.cuda.is_available()
        self.running = True
        self.beep_enabled = True
        self.target_window_handle = None  # Specific window to send text to
        self.auto_execute = False  # Auto-press Enter after text
        
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_signal.emit(f"[{timestamp}] {message}")
        
    def detect_microphones(self):
        devices = sd.query_devices()
        input_devices = []
        seen_names = set()
        
        for idx, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                name = device['name']
                if name not in seen_names and 'mapper' not in name.lower() and 'primary' not in name.lower():
                    input_devices.append((idx, name))
                    seen_names.add(name)
                
        return input_devices
    
    def set_microphone(self, device_idx):
        self.device = device_idx
        
    def load_model(self):
        self.log(f"Loading Whisper '{self.model_size}' model...")
        self.status_signal.emit(f"Loading {self.model_size} model...")
        
        if self.use_gpu:
            self.log(f"GPU detected: {torch.cuda.get_device_name(0)}")
            device = "cuda"
        else:
            self.log("No GPU detected, using CPU")
            device = "cpu"
            
        try:
            self.model = whisper.load_model(self.model_size, device=device)
            n_params = sum(p.numel() for p in self.model.parameters())
            self.log(f"Model loaded ({n_params/1e6:.0f}M params) on {device.upper()}")
            self.status_signal.emit("Ready")
            
            # Warm up
            dummy_audio = np.zeros(16000, dtype=np.float32)
            temp_path = Path.cwd() / "warmup.wav"
            sf.write(str(temp_path), dummy_audio, self.sample_rate)
            self.model.transcribe(str(temp_path), language='en', fp16=(device=="cuda"))
            temp_path.unlink()
            
            return True
        except Exception as e:
            self.log(f"ERROR: Failed to load model: {e}")
            self.status_signal.emit("Model load failed")
            return False
            
    def audio_callback(self, indata, frames, time_info, status):
        if status:
            self.log(f"Audio status: {status}")
        if self.recording:
            self.audio_queue.put(indata.copy())
            
    def play_beep(self, frequency, duration_ms=100):
        if self.beep_enabled:
            try:
                winsound.Beep(frequency, duration_ms)
            except Exception as e:
                self.log(f"Beep failed: {e}")
            
    def start_recording(self):
        current_time = time.time()
        if current_time - self.last_release_time < self.debounce_cooldown:
            return
            
        if not self.recording:
            self.recording = True
            self.audio_queue = queue.Queue()
            self.recording_start_time = time.time()
            self.recording_signal.emit(True)
            self.status_signal.emit("Recording...")
            self.play_beep(800, 100)
            self.log("Recording started")
            
    def stop_recording(self):
        if self.recording:
            self.recording = False
            self.last_release_time = time.time()
            self.recording_signal.emit(False)
            self.status_signal.emit("Processing...")
            self.play_beep(600, 100)
            self.log("Recording stopped")
            
            # Process audio
            time.sleep(0.2)
            
            audio_data = []
            while not self.audio_queue.empty():
                audio_data.append(self.audio_queue.get())
                
            if audio_data:
                audio_data = np.concatenate(audio_data, axis=0)
                duration = len(audio_data)/self.sample_rate
                self.log(f"Processing {duration:.1f}s of audio")
                self.process_audio(audio_data)
            else:
                self.log("No audio recorded")
                self.status_signal.emit("Ready")
                
    def process_audio(self, audio_data):
        try:
            audio_data = audio_data.flatten()
            
            # Check minimum duration (0.5 seconds minimum)
            min_samples = int(0.5 * self.sample_rate)
            if len(audio_data) < min_samples:
                self.log("Recording too short (< 0.5s)")
                self.status_signal.emit("Ready")
                return
            
            # Check for silence - calculate RMS energy
            rms = np.sqrt(np.mean(audio_data**2))
            silence_threshold = 0.001  # Adjust if needed
            
            if rms < silence_threshold:
                self.log("Audio is too quiet (likely silence)")
                self.status_signal.emit("Ready")
                return
            
            # Store RMS for later hallucination detection
            audio_rms = rms
            
            # Check peak amplitude
            max_val = np.max(np.abs(audio_data))
            if max_val < 0.01:  # Very low volume
                self.log("Audio volume too low")
                self.status_signal.emit("Ready")
                return
                
            # Normalize audio
            if max_val > 0:
                audio_data = audio_data / max_val * 0.9
                
            temp_path = Path.cwd() / f"temp_audio_{int(time.time())}.wav"
            
            try:
                sf.write(str(temp_path), audio_data, self.sample_rate)
                
                self.status_signal.emit("Transcribing...")
                start_time = time.time()
                
                result = self.model.transcribe(
                    str(temp_path.absolute()), 
                    language='en',
                    fp16=self.use_gpu,
                    beam_size=5,
                    best_of=5,
                    temperature=0.0
                )
                
                transcribe_time = time.time() - start_time
                text = result['text'].strip()
                
                if temp_path.exists():
                    temp_path.unlink()
                
                # Filter out common Whisper hallucinations
                hallucinations = [
                    "thank you", "thanks", "thank you.", "thanks.", 
                    "thank you for watching", "thanks for watching",
                    "please subscribe", "subscribe", "bye", "bye.",
                    "you", "you.", "♪", "[music]", "[applause]",
                    ".", "..", "...", ""
                ]
                
                if text and text.lower() not in hallucinations:
                    # Additional check: very short text with high silence ratio is likely hallucination
                    if len(text) > 15 or audio_rms > 0.01:  # Either long text or clear audio
                        self.log(f"Transcribed in {transcribe_time:.2f}s")
                        
                        # Check for voice commands
                        original_text = text
                        execute_this_command = self.auto_execute  # Default to GUI setting
                        
                        # Parse voice commands
                        text, voice_commands = self.parse_voice_commands(text)
                        
                        if 'execute' in voice_commands:
                            execute_this_command = True
                            self.log("Voice command: Execute mode enabled for this transcription")
                        
                        self.transcription_signal.emit(original_text)  # Show original in history
                        
                        # Type the text to target window or current focus
                        self.send_text_to_target(text, execute_this_command)
                    else:
                        self.log(f"Filtered possible hallucination: '{text}'")
                else:
                    self.log("No speech detected or hallucination filtered")
                    
                self.status_signal.emit("Ready")
                    
            except Exception as e:
                self.log(f"ERROR: {e}")
                self.status_signal.emit("Ready")
                if temp_path.exists():
                    temp_path.unlink()
                
        except Exception as e:
            self.log(f"ERROR: {e}")
            self.status_signal.emit("Ready")
            
    def run(self):
        if self.device is None:
            devices = self.detect_microphones()
            if devices:
                self.device = devices[0][0]
                self.log(f"Using microphone: {devices[0][1]}")
            else:
                self.log("No microphone found!")
                return
                
        if not self.load_model():
            return
            
        # Setup hotkey
        keyboard.on_press_key(self.hotkey, lambda _: self.start_recording())
        keyboard.on_release_key(self.hotkey, lambda _: self.stop_recording())
        
        # Audio stream
        try:
            with sd.InputStream(callback=self.audio_callback,
                               device=self.device,
                               channels=self.channels,
                               samplerate=self.sample_rate,
                               blocksize=512):
                self.log(f"Ready! Hold [{self.hotkey}] to record")
                while self.running:
                    time.sleep(0.1)
                    if self.recording and self.recording_start_time > 0:
                        elapsed = time.time() - self.recording_start_time
                        if elapsed > self.max_recording_duration:
                            self.log("Max duration reached")
                            self.stop_recording()
        except Exception as e:
            self.log(f"Audio error: {e}")
            
    def get_window_list(self):
        """Get list of visible windows with their handles and titles."""
        def enum_window_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                if window_text.strip():  # Only include windows with titles
                    windows.append((hwnd, window_text))
            return True
        
        windows = []
        win32gui.EnumWindows(enum_window_callback, windows)
        
        # Filter out empty titles and sort by title
        windows = [(hwnd, title) for hwnd, title in windows if title.strip()]
        windows.sort(key=lambda x: x[1].lower())
        
        return windows
    
    def parse_voice_commands(self, text):
        """Parse voice commands from transcribed text."""
        commands = []
        cleaned_text = text.lower()
        
        # Define voice command patterns and their variations
        execute_patterns = [
            'execute mode',
            'execute command', 
            'execute',
            'run command',
            'run this',
            'command mode'
        ]
        
        # Check for execute commands at the beginning of text
        for pattern in execute_patterns:
            if cleaned_text.startswith(pattern):
                commands.append('execute')
                # Remove the command from the text
                text = text[len(pattern):].strip()
                break
        
        return text, commands
    
    def set_target_window(self, window_handle):
        """Set the target window for text output."""
        self.target_window_handle = window_handle
        if window_handle:
            window_title = win32gui.GetWindowText(window_handle)
            self.log(f"Target window set to: {window_title}")
        else:
            self.log("Target window cleared (using current focus)")
    
    def send_text_to_target(self, text, execute_command=None):
        """Send text to target window or current focus."""
        if execute_command is None:
            execute_command = self.auto_execute
            
        self.log(f"send_text_to_target called: text='{text}', execute_command={execute_command}")
        
        try:
            if keyboard.is_pressed('shift') or keyboard.is_pressed('ctrl') or keyboard.is_pressed('alt'):
                self.log("Modifier keys detected, waiting...")
                time.sleep(0.1)
            
            text_to_type = ' ' + text
            success = False
            
            if self.target_window_handle:
                self.log(f"Using target window mode (handle: {self.target_window_handle})")
                success = self._send_to_target_window(text_to_type, execute_command)
            else:
                self.log("Using current focus mode")
                success = self._send_to_current_focus(text_to_type, execute_command)
                
            if success:
                execute_msg = " (with execution)" if execute_command else ""
                self.log(f"Text sent successfully{execute_msg}: '{text_to_type}'")
            else:
                self.log("Text sending failed!")
                
        except Exception as e:
            self.log(f"Error in send_text_to_target: {e}")
    
    def _send_to_target_window(self, text, execute_command):
        """Send text to a specific target window."""
        try:
            # Check if window still exists
            if not win32gui.IsWindow(self.target_window_handle):
                self.log("Target window no longer exists, clearing target")
                self.target_window_handle = None
                return self._send_to_current_focus(text, execute_command)
            
            # Get window info for logging
            target_title = win32gui.GetWindowText(self.target_window_handle)
            current_window = win32gui.GetForegroundWindow()
            current_title = win32gui.GetWindowText(current_window) if current_window else "None"
            
            self.log(f"Target window: '{target_title}' (handle: {self.target_window_handle})")
            self.log(f"Current window: '{current_title}' (handle: {current_window})")
            
            # Attempt to bring target window to foreground
            try:
                focus_result = win32gui.SetForegroundWindow(self.target_window_handle)
                self.log(f"SetForegroundWindow result: {focus_result}")
                time.sleep(0.1)  # Give time for focus change
                
                # Verify focus change
                new_foreground = win32gui.GetForegroundWindow()
                focus_success = (new_foreground == self.target_window_handle)
                self.log(f"Focus change successful: {focus_success} (new foreground: {new_foreground})")
                
                if not focus_success:
                    self.log("WARNING: SetForegroundWindow may have failed, continuing anyway")
                
            except Exception as e:
                self.log(f"SetForegroundWindow failed: {e}")
                
            # Send the text
            self.log(f"Typing text: '{text}'")
            keyboard.write(text)
            
            # Auto-execute if enabled
            if execute_command:
                self.log("Executing command (pressing Enter)...")
                time.sleep(0.1)  # Pause before execution
                
                # Verify we're still focused on target before execution
                current_focus = win32gui.GetForegroundWindow()
                if current_focus != self.target_window_handle:
                    self.log(f"WARNING: Focus lost before execution! Current: {current_focus}, Target: {self.target_window_handle}")
                    # Try to regain focus
                    try:
                        win32gui.SetForegroundWindow(self.target_window_handle)
                        time.sleep(0.05)
                    except:
                        pass
                
                keyboard.press_and_release('end')  # Ensure cursor at end
                time.sleep(0.05)
                self.log("Pressing Enter key...")
                keyboard.press_and_release('enter')
                self.log("Enter key pressed")
            
            # Restore original window focus if it was different
            try:
                if current_window and current_window != self.target_window_handle:
                    self.log(f"Restoring focus to original window: {current_window}")
                    win32gui.SetForegroundWindow(current_window)
            except Exception as e:
                self.log(f"Failed to restore original focus: {e}")
            
            return True
            
        except Exception as e:
            self.log(f"Error in _send_to_target_window: {e}")
            # Fallback to current focus
            return self._send_to_current_focus(text, execute_command)
    
    def _send_to_current_focus(self, text, execute_command):
        """Send text to currently focused window."""
        try:
            current_window = win32gui.GetForegroundWindow()
            current_title = win32gui.GetWindowText(current_window) if current_window else "None"
            self.log(f"Sending to current focus: '{current_title}' (handle: {current_window})")
            
            # Send the text
            self.log(f"Typing text: '{text}'")
            keyboard.write(text)
            
            # Auto-execute if enabled
            if execute_command:
                self.log("Executing command (pressing Enter)...")
                time.sleep(0.1)  # Pause before execution
                
                # Verify focus hasn't changed
                new_focus = win32gui.GetForegroundWindow()
                if new_focus != current_window:
                    self.log(f"WARNING: Focus changed during typing! Original: {current_window}, Current: {new_focus}")
                
                self.log("Pressing Enter key...")
                keyboard.press_and_release('enter')
                self.log("Enter key pressed")
            
            return True
            
        except Exception as e:
            self.log(f"Error in _send_to_current_focus: {e}")
            return False

    def stop(self):
        self.running = False


class MainWindow(QMainWindow):
    def __init__(self, model_size='base'):
        super().__init__()
        self.model_size = model_size
        self.audio_worker = None
        self.init_ui()
        self.setup_system_tray()
        self.start_audio_worker()
        
    def init_ui(self):
        self.setWindowTitle("Speech-to-Text")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Status bar
        status_group = QGroupBox("Status")
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        self.recording_indicator = QLabel("⚫")
        self.recording_indicator.setStyleSheet("font-size: 20px; color: gray;")
        status_layout.addWidget(self.recording_indicator)
        
        status_layout.addStretch()
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Controls
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout()
        
        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(['tiny', 'base', 'small', 'medium', 'large'])
        self.model_combo.setCurrentText(self.model_size)
        self.model_combo.currentTextChanged.connect(self.change_model)
        model_layout.addWidget(self.model_combo)
        
        # Microphone selection
        model_layout.addWidget(QLabel("Microphone:"))
        self.mic_combo = QComboBox()
        self.refresh_microphones()
        model_layout.addWidget(self.mic_combo)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_microphones)
        model_layout.addWidget(refresh_btn)
        
        model_layout.addStretch()
        controls_layout.addLayout(model_layout)
        
        # Options
        options_layout = QHBoxLayout()
        self.beep_checkbox = QCheckBox("Audio feedback")
        self.beep_checkbox.setChecked(True)
        self.beep_checkbox.stateChanged.connect(self.toggle_beep)
        options_layout.addWidget(self.beep_checkbox)
        
        self.auto_space_checkbox = QCheckBox("Auto-add space")
        self.auto_space_checkbox.setChecked(True)
        options_layout.addWidget(self.auto_space_checkbox)
        
        self.auto_execute_checkbox = QCheckBox("Auto-execute (Enter)")
        self.auto_execute_checkbox.setChecked(False)
        self.auto_execute_checkbox.stateChanged.connect(self.toggle_auto_execute)
        self.auto_execute_checkbox.setToolTip("Automatically press Enter after typing text")
        options_layout.addWidget(self.auto_execute_checkbox)
        
        options_layout.addStretch()
        controls_layout.addLayout(options_layout)
        
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        # Window targeting
        window_group = QGroupBox("Window Targeting")
        window_layout = QVBoxLayout()
        
        window_select_layout = QHBoxLayout()
        window_select_layout.addWidget(QLabel("Target Window:"))
        self.window_combo = QComboBox()
        self.window_combo.addItem("Current Focus (Default)", None)
        self.window_combo.currentIndexChanged.connect(self.select_target_window)
        window_select_layout.addWidget(self.window_combo)
        
        refresh_windows_btn = QPushButton("Refresh")
        refresh_windows_btn.clicked.connect(self.refresh_windows)
        window_select_layout.addWidget(refresh_windows_btn)
        
        window_layout.addLayout(window_select_layout)
        window_group.setLayout(window_layout)
        layout.addWidget(window_group)
        
        # Transcription history
        history_group = QGroupBox("Transcription History")
        history_layout = QVBoxLayout()
        
        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)
        self.history_text.setMaximumHeight(150)
        history_layout.addWidget(self.history_text)
        
        clear_btn = QPushButton("Clear History")
        clear_btn.clicked.connect(self.history_text.clear)
        history_layout.addWidget(clear_btn)
        
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        # Log output
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create icon
        icon = self.create_icon()
        self.tray_icon.setIcon(icon)
        self.setWindowIcon(icon)
        
        # Tray menu
        tray_menu = QMenu()
        
        show_action = tray_menu.addAction("Show Window")
        show_action.triggered.connect(self.show)
        
        tray_menu.addSeparator()
        
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_application)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
        
    def create_icon(self):
        # Create a simple icon
        img = Image.new('RGB', (64, 64), color='black')
        draw = ImageDraw.Draw(img)
        draw.ellipse([8, 8, 56, 56], fill='white', outline='gray')
        draw.ellipse([24, 24, 40, 40], fill='red')
        
        # Convert to QIcon
        img.save("icon.png")
        return QIcon("icon.png")
        
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            
    def refresh_microphones(self):
        self.mic_combo.clear()
        if self.audio_worker:
            devices = self.audio_worker.detect_microphones()
            for idx, name in devices:
                self.mic_combo.addItem(name, idx)
                
    def change_model(self, model_name):
        reply = QMessageBox.question(self, 'Change Model', 
                                    f'Change to {model_name} model? This will restart the worker.',
                                    QMessageBox.StandardButton.Yes | 
                                    QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.model_size = model_name
            self.restart_audio_worker()
            
    def toggle_beep(self, state):
        if self.audio_worker:
            self.audio_worker.beep_enabled = (state == 2)
            
    def toggle_auto_execute(self, state):
        if self.audio_worker:
            self.audio_worker.auto_execute = (state == 2)
            mode_status = "enabled" if state == 2 else "disabled"
            self.append_log(f"Auto-execute mode {mode_status}")
            
    def refresh_windows(self):
        """Refresh the list of available windows."""
        if not self.audio_worker:
            return
            
        # Clear current items except the default
        self.window_combo.clear()
        self.window_combo.addItem("Current Focus (Default)", None)
        
        # Get window list from worker
        try:
            windows = self.audio_worker.get_window_list()
            for hwnd, title in windows:
                # Truncate very long titles
                display_title = title[:60] + "..." if len(title) > 60 else title
                self.window_combo.addItem(display_title, hwnd)
        except Exception as e:
            self.append_log(f"Error refreshing windows: {e}")
            
    def select_target_window(self, index):
        """Select target window from dropdown."""
        if not self.audio_worker:
            return
            
        selected_data = self.window_combo.itemData(index)
        self.audio_worker.set_target_window(selected_data)
            
    def start_audio_worker(self):
        self.audio_worker = AudioWorker(self.model_size)
        self.audio_worker.log_signal.connect(self.append_log)
        self.audio_worker.status_signal.connect(self.update_status)
        self.audio_worker.recording_signal.connect(self.update_recording_indicator)
        self.audio_worker.transcription_signal.connect(self.add_transcription)
        
        # Set microphone if selected
        if self.mic_combo.currentData():
            self.audio_worker.set_microphone(self.mic_combo.currentData())
            
        self.audio_worker.start()
        
        # Auto-refresh windows list
        QTimer.singleShot(1000, self.refresh_windows)
        
    def restart_audio_worker(self):
        if self.audio_worker:
            self.audio_worker.stop()
            self.audio_worker.wait()
        self.start_audio_worker()
        
    @pyqtSlot(str)
    def append_log(self, message):
        self.log_text.append(message)
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
        
    @pyqtSlot(str)
    def update_status(self, status):
        self.status_label.setText(status)
        
    @pyqtSlot(bool)
    def update_recording_indicator(self, is_recording):
        if is_recording:
            self.recording_indicator.setText("🔴")
            self.recording_indicator.setStyleSheet("font-size: 20px; color: red;")
        else:
            self.recording_indicator.setText("⚫")
            self.recording_indicator.setStyleSheet("font-size: 20px; color: gray;")
            
    @pyqtSlot(str)
    def add_transcription(self, text):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.history_text.append(f"[{timestamp}] {text}")
        
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Speech-to-Text",
            "Application minimized to tray",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
        
    def quit_application(self):
        if self.audio_worker:
            self.audio_worker.stop()
            self.audio_worker.wait()
        QApplication.quit()


def main():
    parser = argparse.ArgumentParser(description='Speech-to-Text with GUI')
    parser.add_argument('--model', type=str, default='base',
                       choices=['tiny', 'base', 'small', 'medium', 'large'],
                       help='Whisper model size')
    args = parser.parse_args()
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    window = MainWindow(args.model)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()