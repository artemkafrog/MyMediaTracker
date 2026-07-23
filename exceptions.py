class MediaTrackerError(Exception):
    pass

class ValidationError(MediaTrackerError):
    pass

class NotFoundError(MediaTrackerError):
    pass

class DuplicateError(MediaTrackerError):
    pass