import os
import sys
import time
import queue
import threading
import tempfile
import argparse
import torch
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf
import keyboard
import whisper


class SpeechToText:
    def __init__(self, model_size='base'):
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
        self.log_dir = Path("logs")
        self.session_log = None
        self.recording_start_time = 0
        self.use_gpu = torch.cuda.is_available()
        
    def setup_logging(self):
        self.log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_log = self.log_dir / f"session_{timestamp}.txt"
        self.log(f"Session started at {datetime.now()}")
        
    def log(self, message):
        if self.session_log:
            with open(self.session_log, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        print(message)
        
    def detect_microphones(self):
        devices = sd.query_devices()
        input_devices = []
        seen_names = set()
        
        for idx, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                name = device['name']
                # Filter out duplicates and system mappers
                if name not in seen_names and 'mapper' not in name.lower() and 'primary' not in name.lower():
                    input_devices.append((idx, name, device['default_samplerate']))
                    seen_names.add(name)
                
        return input_devices
    
    def select_microphone(self):
        input_devices = self.detect_microphones()
        
        if not input_devices:
            self.log("ERROR: No microphone detected!")
            self.log("Please check:")
            self.log("  1. Your microphone is properly connected")
            self.log("  2. Microphone drivers are installed")
            self.log("  3. Microphone is not disabled in Windows Sound Settings")
            self.log("  4. No other application is exclusively using the microphone")
            return False
            
        if len(input_devices) == 1:
            self.device = input_devices[0][0]
            self.log(f"Using microphone: {input_devices[0][1]}")
            return True
            
        self.log("Available microphones:")
        for i, (idx, name, rate) in enumerate(input_devices):
            self.log(f"  {i + 1}. {name}")
            
        while True:
            try:
                choice = input("Select microphone number: ")
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(input_devices):
                    self.device = input_devices[choice_idx][0]
                    self.log(f"Selected: {input_devices[choice_idx][1]}")
                    return True
                else:
                    self.log("Invalid selection. Please try again.")
            except ValueError:
                self.log("Please enter a valid number.")
                
    def load_model(self):
        self.log(f"Loading Whisper '{self.model_size}' model...")
        
        # Check GPU availability
        if self.use_gpu:
            self.log(f"GPU detected: {torch.cuda.get_device_name(0)}")
            self.log(f"CUDA version: {torch.version.cuda}")
            device = "cuda"
        else:
            self.log("No GPU detected, using CPU")
            device = "cpu"
            
        try:
            # Load model with explicit device placement
            self.model = whisper.load_model(self.model_size, device=device)
            
            # Show model info
            n_params = sum(p.numel() for p in self.model.parameters())
            self.log(f"Model loaded successfully ({n_params/1e6:.0f}M parameters)")
            self.log(f"Running on: {device.upper()}")
            
            # Warm up the model with a dummy transcription
            self.log("Warming up model...")
            dummy_audio = np.zeros(16000, dtype=np.float32)
            temp_path = Path.cwd() / "warmup.wav"
            sf.write(str(temp_path), dummy_audio, self.sample_rate)
            self.model.transcribe(str(temp_path), language='en', fp16=(device=="cuda"))
            temp_path.unlink()
            self.log("Model ready!")
            
            return True
        except Exception as e:
            self.log(f"ERROR: Failed to load Whisper model: {e}")
            return False
            
    def audio_callback(self, indata, frames, time_info, status):
        if status:
            self.log(f"Audio callback status: {status}")
        if self.recording:
            self.audio_queue.put(indata.copy())
            
    def play_beep(self, frequency, duration):
        try:
            sample_rate = 44100
            t = np.linspace(0, duration, int(sample_rate * duration))
            beep = np.sin(frequency * 2 * np.pi * t) * 0.3  # Reduced volume
            sd.play(beep, sample_rate)
            sd.wait()
        except Exception as e:
            self.log(f"Could not play beep: {e}")
            
    def start_recording(self):
        current_time = time.time()
        if current_time - self.last_release_time < self.debounce_cooldown:
            return
            
        if not self.recording:
            self.recording = True
            self.audio_queue = queue.Queue()
            self.recording_start_time = time.time()
            self.play_beep(800, 0.1)
            self.log("Recording...")
            
    def stop_recording(self):
        if self.recording:
            self.recording = False
            self.last_release_time = time.time()
            self.play_beep(600, 0.1)
            self.log("Processing...")
            
            # Give callback time to process final audio
            time.sleep(0.2)
            
            audio_data = []
            while not self.audio_queue.empty():
                audio_data.append(self.audio_queue.get())
                
            if audio_data:
                audio_data = np.concatenate(audio_data, axis=0)
                self.log(f"Audio data shape: {audio_data.shape}, duration: {len(audio_data)/self.sample_rate:.2f}s")
                self.process_audio(audio_data)
            else:
                self.log("No audio recorded")
                
    def process_audio(self, audio_data):
        try:
            audio_data = audio_data.flatten()
            
            # Check if we have actual audio
            if len(audio_data) < 1000:  # Less than 0.06 seconds
                self.log("Audio too short to process")
                return
            
            max_val = np.max(np.abs(audio_data))
            if max_val > 0:
                audio_data = audio_data / max_val * 0.9
            else:
                self.log("Audio is silent")
                return
                
            # Use current directory for temp file
            temp_path = Path.cwd() / f"temp_audio_{int(time.time())}.wav"
            
            try:
                sf.write(str(temp_path), audio_data, self.sample_rate)
                self.log(f"Saved audio to {temp_path}")
                
                # Verify file exists
                if not temp_path.exists():
                    self.log(f"ERROR: Audio file was not created at {temp_path}")
                    return
                    
                self.log(f"File size: {temp_path.stat().st_size} bytes")
                
                self.log("Transcribing...")
                start_time = time.time()
                
                # Use GPU if available
                result = self.model.transcribe(
                    str(temp_path.absolute()), 
                    language='en',
                    fp16=self.use_gpu,  # Use FP16 on GPU for faster inference
                    beam_size=5,  # Better accuracy with beam search
                    best_of=5,  # Sample 5 times and pick the best
                    temperature=0.0  # More deterministic results
                )
                
                transcribe_time = time.time() - start_time
                text = result['text'].strip()
                
                if temp_path.exists():
                    temp_path.unlink()
                
                if text:
                    self.log(f"Transcribed in {transcribe_time:.2f}s: {text}")
                    
                    if keyboard.is_pressed('shift') or keyboard.is_pressed('ctrl') or keyboard.is_pressed('alt'):
                        time.sleep(0.1)
                        
                    text = ' ' + text
                        
                    keyboard.write(text)
                    self.log(f"Text typed: {text}")
                else:
                    self.log("No speech detected")
                    
            except Exception as e:
                self.log(f"ERROR processing audio file: {e}")
                if temp_path.exists():
                    temp_path.unlink()
                
        except Exception as e:
            self.log(f"ERROR during processing: {e}")
            
    def audio_monitor(self):
        try:
            with sd.InputStream(callback=self.audio_callback,
                               device=self.device,
                               channels=self.channels,
                               samplerate=self.sample_rate,
                               blocksize=512):  # Smaller blocksize for better responsiveness
                while True:
                    time.sleep(0.1)
                    if self.recording and self.recording_start_time > 0:
                        elapsed = time.time() - self.recording_start_time
                        if elapsed > self.max_recording_duration:
                            self.log(f"Max recording duration ({self.max_recording_duration}s) reached")
                            self.stop_recording()
        except Exception as e:
            self.log(f"Audio monitor error: {e}")
                        
    def run(self):
        self.setup_logging()
        self.log("Speech-to-Text Utility Starting...")
        self.log(f"Model: {self.model_size}")
        
        if not self.select_microphone():
            return
            
        if not self.load_model():
            return
            
        self.log(f"Setting up hotkey: {self.hotkey}")
        keyboard.on_press_key(self.hotkey, lambda _: self.start_recording())
        keyboard.on_release_key(self.hotkey, lambda _: self.stop_recording())
        
        audio_thread = threading.Thread(target=self.audio_monitor, daemon=True)
        audio_thread.start()
        
        self.log(f"Ready! Hold [{self.hotkey}] to record, release to transcribe")
        self.log("Press Ctrl+C to exit")
        
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.log("\nShutting down...")
            

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Speech-to-Text Utility')
    parser.add_argument(
        '--model', 
        type=str, 
        default='base',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        help='Whisper model size (default: base)'
    )
    
    args = parser.parse_args()
    
    app = SpeechToText(model_size=args.model)
    app.run()