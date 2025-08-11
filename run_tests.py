"""Test runner for the refactored application."""

import sys
import subprocess
from pathlib import Path
import os

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def run_unit_tests():
    """Run unit tests with coverage."""
    print("=" * 60)
    print("Running Unit Tests")
    print("=" * 60)
    
    # Check if pytest-cov is installed
    try:
        import pytest_cov
        coverage_args = ["--cov=src", "--cov-report=term-missing"]
    except ImportError:
        print("Note: pytest-cov not installed, running without coverage")
        coverage_args = []
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/unit", "-v"] + coverage_args,
        capture_output=False
    )
    
    return result.returncode == 0


def run_integration_test():
    """Run a simple integration test."""
    print("\n" + "=" * 60)
    print("Running Integration Test")
    print("=" * 60)
    
    # Add src to path
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    
    try:
        # Test dependency injection
        from src.core.bootstrap import ApplicationBootstrap
        from src.core.config import Config
        
        print("\n1. Testing configuration loading...")
        config = Config()
        print(f"   [OK] Config created with model: {config.transcription.model_size}")
        
        print("\n2. Testing dependency injection container...")
        bootstrap = ApplicationBootstrap(config)
        container = bootstrap.get_container()
        print("   [OK] Container created")
        
        print("\n3. Testing service resolution...")
        from src.domain.interfaces.audio_recorder import IAudioRecorder
        from src.domain.services.voice_command_parser import VoiceCommandParser
        
        audio_recorder = container.resolve(IAudioRecorder)
        print(f"   [OK] Resolved IAudioRecorder: {type(audio_recorder).__name__}")
        
        parser = container.resolve(VoiceCommandParser)
        print(f"   [OK] Resolved VoiceCommandParser: {type(parser).__name__}")
        
        print("\n4. Testing use case resolution...")
        from src.application.use_cases.manage_recording import ManageRecordingUseCase
        
        use_case = container.resolve(ManageRecordingUseCase)
        print(f"   [OK] Resolved ManageRecordingUseCase: {type(use_case).__name__}")
        
        print("\n5. Testing domain logic...")
        command = parser.parse("execute mode python test.py")
        print(f"   [OK] Parsed command: type={command.command_type.value}, execute={command.execute}")
        
        print("\n[SUCCESS] All integration tests passed!")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test runner."""
    print("Starting test suite for refactored application\n")
    
    # Check if pytest is installed
    try:
        import pytest
    except ImportError:
        print("[ERROR] pytest not installed. Run: pip install pytest pytest-cov pytest-mock")
        return 1
    
    # Run tests
    unit_success = run_unit_tests()
    integration_success = run_integration_test()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Unit Tests: {'PASSED' if unit_success else 'FAILED'}")
    print(f"Integration Tests: {'PASSED' if integration_success else 'FAILED'}")
    
    if unit_success and integration_success:
        print("\n[SUCCESS] All tests passed! The refactoring is working correctly.")
        return 0
    else:
        print("\n[WARNING] Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())