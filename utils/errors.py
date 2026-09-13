"""Custom exceptions for StegoHide."""


class StegoHideError(Exception):
    """Base class for project-specific errors."""


class UnsupportedImageFormatError(StegoHideError):
    """Raised when an unsupported image format is detected."""


class InvalidImageDataError(StegoHideError):
    """Raised when image data is missing, invalid, or malformed."""


class InvalidHeaderError(StegoHideError):
    """Raised when the StegoHide header is missing or invalid."""


class NoStegoMessageFoundError(StegoHideError):
    """Raised when no StegoHide signature is found in the image."""


class InvalidMessageLengthError(StegoHideError):
    """Raised when the embedded message length is invalid."""


class InsufficientCapacityError(StegoHideError):
    """Raised when image space is not large enough."""


class CorruptedDataError(StegoHideError):
    """Raised when image or hidden data is corrupted."""


class ConfigurationError(StegoHideError):
    """Raised when configuration is invalid."""
