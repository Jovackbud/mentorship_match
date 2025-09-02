# src/constants.py
class ErrorMessages:
    MENTOR_NOT_FOUND = "Mentor not found"
    MENTEE_NOT_FOUND = "Mentee not found"
    UNAUTHORIZED_MENTOR = "Not authorized to access this mentor profile"
    UNAUTHORIZED_MENTEE = "Not authorized to access this mentee profile"
    CAPACITY_EXCEEDED = "Mentor has reached maximum capacity"
    MENTEE_LIMIT_EXCEEDED = "Mentee has reached maximum active mentorships"
    DUPLICATE_PROFILE = "Profile already exists for this user"
    INVALID_STATUS = "Invalid status transition"
    EMBEDDING_FAILED = "Failed to generate embedding"

class BusinessRules:
    MIN_BIO_LENGTH = 20
    MIN_NAME_LENGTH = 2
    MAX_NAME_LENGTH = 100
    MIN_PASSWORD_LENGTH = 6
    MAX_USERNAME_LENGTH = 50