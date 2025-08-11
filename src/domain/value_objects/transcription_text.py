from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class TranscriptionText:
    """Value object representing transcribed text with additional metadata."""
    
    raw_text: str
    cleaned_text: str
    language: str = 'en'
    
    @classmethod
    def create(cls, raw_text: str, language: str = 'en') -> 'TranscriptionText':
        """Factory method to create a TranscriptionText with automatic cleaning."""
        cleaned = cls._clean_text(raw_text)
        return cls(
            raw_text=raw_text,
            cleaned_text=cleaned,
            language=language
        )
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean the transcribed text."""
        # Remove extra whitespace
        cleaned = ' '.join(text.split())
        
        # Remove leading/trailing whitespace
        cleaned = cleaned.strip()
        
        return cleaned
    
    @property
    def is_empty(self) -> bool:
        """Check if the text is empty."""
        return len(self.cleaned_text) == 0
    
    @property
    def word_count(self) -> int:
        """Get the word count of the cleaned text."""
        if self.is_empty:
            return 0
        return len(self.cleaned_text.split())
    
    @property
    def character_count(self) -> int:
        """Get the character count of the cleaned text."""
        return len(self.cleaned_text)
    
    def contains_command_prefix(self, prefixes: List[str]) -> Tuple[bool, str]:
        """Check if the text starts with any command prefix."""
        lower_text = self.cleaned_text.lower()
        for prefix in prefixes:
            if lower_text.startswith(prefix.lower()):
                return True, prefix
        return False, ""
    
    def remove_prefix(self, prefix: str) -> 'TranscriptionText':
        """Return a new TranscriptionText with the prefix removed."""
        if self.cleaned_text.lower().startswith(prefix.lower()):
            new_text = self.cleaned_text[len(prefix):].strip()
            return TranscriptionText(
                raw_text=self.raw_text,
                cleaned_text=new_text,
                language=self.language
            )
        return self
    
    def add_leading_space(self) -> 'TranscriptionText':
        """Return a new TranscriptionText with a leading space."""
        return TranscriptionText(
            raw_text=self.raw_text,
            cleaned_text=' ' + self.cleaned_text,
            language=self.language
        )
    
    def __str__(self) -> str:
        preview = self.cleaned_text[:50] + "..." if len(self.cleaned_text) > 50 else self.cleaned_text
        return f"TranscriptionText('{preview}', {self.word_count} words)"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, TranscriptionText):
            return self.cleaned_text == other.cleaned_text
        return False