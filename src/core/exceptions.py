"""Custom exception hierarchy for the application."""


class ApplicationError(Exception):
    """Base exception for all application errors."""
    pass


class DomainError(ApplicationError):
    """Base exception for domain layer errors."""
    pass


class InfrastructureError(ApplicationError):
    """Base exception for infrastructure layer errors."""
    pass


class ValidationError(DomainError):
    """Exception raised when validation fails."""
    pass


class RecordingError(DomainError):
    """Exception raised for recording-related errors."""
    pass


class TranscriptionError(DomainError):
    """Exception raised for transcription-related errors."""
    pass


class AudioDeviceError(InfrastructureError):
    """Exception raised for audio device errors."""
    pass


class ModelLoadError(InfrastructureError):
    """Exception raised when model loading fails."""
    pass


class WindowManagementError(InfrastructureError):
    """Exception raised for window management errors."""
    pass


class ConfigurationError(ApplicationError):
    """Exception raised for configuration errors."""
    pass


class DependencyInjectionError(ApplicationError):
    """Exception raised for dependency injection errors."""
    pass