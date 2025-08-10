"""Main entry point for the speech-to-text application.

This module provides both legacy and new architecture options during migration.
"""

import argparse
import sys
from pathlib import Path


def main():
    """Main entry point with architecture selection."""
    parser = argparse.ArgumentParser(
        description='Speech-to-Text Application',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with new architecture (default)
  python main.py --model base
  
  # Run with legacy monolithic implementation
  python main.py --legacy --model base
  
  # Run with specific configuration file
  python main.py --config config/custom.yaml
  
  # Run CLI version
  python main.py --cli --model base
        """
    )
    
    # Model selection
    parser.add_argument(
        '--model',
        type=str,
        default='base',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        help='Whisper model size (default: base)'
    )
    
    # Architecture selection
    parser.add_argument(
        '--legacy',
        action='store_true',
        help='Use legacy monolithic implementation'
    )
    
    # Interface selection
    parser.add_argument(
        '--cli',
        action='store_true',
        help='Run CLI version instead of GUI'
    )
    
    # Configuration
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file (YAML or JSON)'
    )
    
    # Device selection
    parser.add_argument(
        '--device',
        type=str,
        choices=['cpu', 'cuda'],
        help='Device for model inference (auto-detect if not specified)'
    )
    
    args = parser.parse_args()
    
    if args.legacy:
        # Run legacy implementation
        run_legacy(args)
    else:
        # Run new modular implementation
        run_modular(args)


def run_legacy(args):
    """Run the legacy monolithic implementation."""
    print("Running legacy implementation...")
    
    if args.cli:
        # Import and run CLI version
        from speech_to_text import main as legacy_cli_main
        sys.argv = ['speech_to_text.py', '--model', args.model]
        legacy_cli_main()
    else:
        # Import and run GUI version
        from speech_to_text_gui import main as legacy_gui_main
        sys.argv = ['speech_to_text_gui.py', '--model', args.model]
        legacy_gui_main()


def run_modular(args):
    """Run the new modular implementation."""
    print("Running new modular architecture...")
    
    # Add src to path
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    
    from PyQt6.QtWidgets import QApplication
    from pathlib import Path
    
    # Load configuration
    from src.core.config import Config, ConfigLoader
    from src.core.bootstrap import ApplicationBootstrap
    
    if args.config:
        config_path = Path(args.config)
        config = ConfigLoader.load_or_create_default(config_path)
    else:
        # Create default config
        config = Config()
        
        # Apply command line arguments
        config.transcription.model_size = args.model
        if args.device:
            config.transcription.device = args.device
    
    # Create bootstrap
    bootstrap = ApplicationBootstrap(config)
    
    # Initialize components
    print("Initializing application components...")
    bootstrap.setup_audio_device()
    bootstrap.initialize_model()
    bootstrap.setup_hotkeys()
    
    if args.cli:
        # Run CLI version
        run_modular_cli(bootstrap)
    else:
        # Run GUI version
        run_modular_gui(bootstrap)


def run_modular_cli(bootstrap):
    """Run the modular CLI interface."""
    print("\n=== Speech-to-Text CLI (Modular Architecture) ===")
    print(f"Model: {bootstrap.config.transcription.model_size}")
    print(f"Hotkey: {bootstrap.config.hotkey.record_key}")
    print("\nPress hotkey to record, release to transcribe.")
    print("Press Ctrl+C to exit.\n")
    
    # Get dependencies from container
    container = bootstrap.get_container()
    
    from src.domain.interfaces.audio_recorder import IAudioRecorder
    from src.domain.interfaces.transcriber import ITranscriber
    from src.domain.interfaces.text_output import ITextOutput
    from src.domain.interfaces.hotkey_handler import IHotkeyHandler
    from src.application.use_cases.manage_recording import (
        ManageRecordingUseCase,
        StartRecordingRequest
    )
    from src.application.use_cases.record_and_transcribe import (
        RecordAndTranscribeUseCase,
        RecordAndTranscribeRequest
    )
    from src.application.use_cases.send_text import SendTextUseCase, SendTextRequest
    from src.domain.value_objects.window_target import WindowTarget
    from src.infrastructure.audio.audio_feedback import AudioFeedback
    
    # Resolve dependencies
    hotkey_handler = container.resolve(IHotkeyHandler)
    manage_recording = container.resolve(ManageRecordingUseCase)
    record_and_transcribe = container.resolve(RecordAndTranscribeUseCase)
    send_text = container.resolve(SendTextUseCase)
    audio_feedback = container.resolve(AudioFeedback)
    
    # Set up hotkey handlers
    current_session = None
    
    def on_hotkey_press():
        nonlocal current_session
        print("Recording...")
        audio_feedback.play_recording_start()
        
        # Start recording
        response = manage_recording.start_recording(StartRecordingRequest())
        if response.success:
            current_session = response.session
        else:
            print(f"Error: {response.error_message}")
    
    def on_hotkey_release():
        nonlocal current_session
        if not current_session:
            return
        
        print("Processing...")
        audio_feedback.play_recording_stop()
        
        # Stop recording
        stop_response = manage_recording.stop_recording(
            StopRecordingRequest(session_id=current_session.id)
        )
        
        if not stop_response.success:
            print(f"Error: {stop_response.error_message}")
            return
        
        # Transcribe
        transcribe_response = record_and_transcribe.execute(
            RecordAndTranscribeRequest(
                session_id=current_session.id,
                language=bootstrap.config.transcription.language
            )
        )
        
        if transcribe_response.success:
            print(f"Transcribed: {transcribe_response.transcription.text}")
            
            # Send text
            if transcribe_response.voice_command:
                send_response = send_text.execute_voice_command(
                    transcribe_response.voice_command,
                    WindowTarget.create_current_focus()
                )
                
                if not send_response.success:
                    print(f"Failed to send text: {send_response.error_message}")
        else:
            print(f"Transcription failed: {transcribe_response.error_message}")
        
        current_session = None
        print("Ready")
    
    # Register hotkeys
    hotkey_handler.register_hotkey(
        bootstrap.config.hotkey.record_key,
        on_press=on_hotkey_press,
        on_release=on_hotkey_release
    )
    
    # Start listening
    hotkey_handler.start_listening()
    
    try:
        # Keep running
        import time
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        hotkey_handler.stop_listening()


def run_modular_gui(bootstrap):
    """Run the modular GUI interface."""
    from PyQt6.QtWidgets import QApplication
    import sys
    
    # Import GUI components (to be implemented)
    # For now, fall back to legacy GUI with a note
    print("\nGUI with new architecture is being implemented.")
    print("Starting legacy GUI for now...\n")
    
    from speech_to_text_gui import MainWindow
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    window = MainWindow(bootstrap.config.transcription.model_size)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()