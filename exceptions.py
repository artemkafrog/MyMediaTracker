class MediaTrackerError(Exception):
    def __init__(self, message="An error has occurred in MediaTracker"):
        self.message = message
        super().__init__(self.message)

class ValidationError(MediaTrackerError):
    def __init__(self):
        self.message = "Field validation error "
        super().__init__(self.message)

class NotFoundError(MediaTrackerError):
    def __init__(self):
        self.message = "The element wasn't found in the system"
        super().__init__(self.message)

class DuplicateError(MediaTrackerError):
    def __init__(self):
        self.message = "This element already exists"
        super().__init__(self.message)