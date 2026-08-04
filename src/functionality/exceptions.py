class MediaTrackerError(Exception):
    """Base exception for MediaTracker."""
    def __init__(self, message="An error has occurred in MediaTracker."):
        self.message = message
        super().__init__(self.message)

class ValidationError(MediaTrackerError):
    """Raised when validation fails."""
    def __init__(self, message="Field validation error."):
        super().__init__(message)

class NotFoundError(MediaTrackerError):
    """Raised when an item is not found."""
    def __init__(self, message="The element wasn't found in the system."):
        super().__init__(message)

class DuplicateError(MediaTrackerError):
    """Raised when attempting to add a duplicate item."""
    def __init__(self, message="This element already exists."):
        super().__init__(message)