"""Unit tests for Transcription entity."""

import pytest
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.domain.entities.transcription import Transcription


class TestTranscription:
    """Test suite for Transcription entity."""
    
    def test_create_transcription(self):
        """Test creating a transcription entity."""
        transcription = Transcription.create(
            text="Hello world",
            duration_seconds=2.5,
            model_size="base",
            confidence=0.95,
            audio_rms=0.05
        )
        
        assert transcription.text == "Hello world"
        assert transcription.duration_seconds == 2.5
        assert transcription.model_size == "base"
        assert transcription.confidence == 0.95
        assert transcription.audio_rms == 0.05
        assert transcription.id is not None
        assert isinstance(transcription.timestamp, datetime)
    
    def test_is_valid_with_valid_transcription(self):
        """Test validation with valid transcription."""
        transcription = Transcription.create(
            text="Valid text",
            duration_seconds=1.0,
            model_size="base"
        )
        
        assert transcription.is_valid() == True
    
    def test_is_valid_with_empty_text(self):
        """Test validation with empty text."""
        transcription = Transcription.create(
            text="",
            duration_seconds=1.0,
            model_size="base"
        )
        
        assert transcription.is_valid() == False
    
    def test_is_valid_with_short_duration(self):
        """Test validation with duration too short."""
        transcription = Transcription.create(
            text="Text",
            duration_seconds=0.3,
            model_size="base"
        )
        
        assert transcription.is_valid() == False
    
    def test_is_likely_hallucination_with_common_phrases(self):
        """Test hallucination detection with common phrases."""
        hallucination_texts = [
            "thank you",
            "thanks",
            "thank you for watching",
            "please subscribe",
            "bye",
            "you",
            ".",
            ""
        ]
        
        for text in hallucination_texts:
            transcription = Transcription.create(
                text=text,
                duration_seconds=1.0,
                model_size="base"
            )
            assert transcription.is_likely_hallucination() == True
    
    def test_is_likely_hallucination_with_short_text_low_rms(self):
        """Test hallucination detection with short text and low RMS."""
        transcription = Transcription.create(
            text="short",
            duration_seconds=1.0,
            model_size="base",
            audio_rms=0.005  # Very low RMS
        )
        
        assert transcription.is_likely_hallucination() == True
    
    def test_is_likely_hallucination_with_valid_text(self):
        """Test hallucination detection with valid text."""
        transcription = Transcription.create(
            text="This is a longer valid transcription",
            duration_seconds=3.0,
            model_size="base",
            audio_rms=0.05
        )
        
        assert transcription.is_likely_hallucination() == False
    
    def test_string_representation(self):
        """Test string representation of transcription."""
        transcription = Transcription.create(
            text="Test text",
            duration_seconds=2.5,
            model_size="base"
        )
        
        str_repr = str(transcription)
        assert "Test text" in str_repr
        assert "2.5s" in str_repr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])