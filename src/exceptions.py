# src/exceptions.py (COMPLETE)
class BusinessLogicError(Exception):
    """Base exception for business logic errors"""
    pass

class NotFoundError(BusinessLogicError):
    """Raised when a resource is not found"""
    pass

class UnauthorizedError(BusinessLogicError):
    """Raised when user lacks authorization"""
    pass

class CapacityExceededError(BusinessLogicError):
    """Raised when mentor/mentee capacity is exceeded"""
    pass

class InvalidStatusTransitionError(BusinessLogicError):
    """Raised when invalid status transition is attempted"""
    pass

class DuplicateRequestError(BusinessLogicError):
    """Raised when duplicate request is attempted"""
    pass

class ProfileAlreadyExistsError(BusinessLogicError):
    """Raised when trying to create duplicate profile"""
    pass

class EmbeddingError(BusinessLogicError):
    """Raised when embedding generation fails"""
    pass