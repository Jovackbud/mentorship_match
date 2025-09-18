# src/utils/validation_utils.py
from typing import Optional
from sqlalchemy.orm import Session
from ..models import Mentor, Mentee, MentorshipRequest, MentorshipStatus
from ..config import get_settings
from ..exceptions import CapacityExceededError, InvalidStatusTransitionError, DuplicateRequestError, NotFoundError

class ValidationUtils:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
    
    def get_mentor_or_404(self, mentor_id: int) -> Mentor:
        mentor = self.db.query(Mentor).filter(Mentor.id == mentor_id).first()
        if not mentor:
            raise NotFoundError("Mentor not found")
        return mentor
    
    def get_mentee_or_404(self, mentee_id: int) -> Mentee:
        mentee = self.db.query(Mentee).filter(Mentee.id == mentee_id).first()
        if not mentee:
            raise NotFoundError("Mentee not found")
        return mentee
    
    def get_request_or_404(self, request_id: int) -> MentorshipRequest:
        request = self.db.query(MentorshipRequest).filter(MentorshipRequest.id == request_id).first()
        if not request:
            raise NotFoundError("Mentorship request not found")
        return request
    
    def validate_mentor_capacity(self, mentor: Mentor):
        if mentor.current_mentees >= mentor.capacity:
            raise CapacityExceededError("Mentor has reached maximum capacity")
    
    def validate_mentee_capacity(self, mentee_id: int):
        active_count = self.db.query(MentorshipRequest).filter(
            MentorshipRequest.mentee_id == mentee_id,
            MentorshipRequest.status == MentorshipStatus.ACCEPTED
        ).count()
        
        if active_count >= self.settings.MENTEE_MAX_ACTIVE_MENTORS:
            raise CapacityExceededError(f"Mentee has reached maximum limit of {self.settings.MENTEE_MAX_ACTIVE_MENTORS} active mentorships")
    
    def check_no_pending_request(self, mentee_id: int, mentor_id: int):
        existing = self.db.query(MentorshipRequest).filter(
            MentorshipRequest.mentee_id == mentee_id,
            MentorshipRequest.mentor_id == mentor_id,
            MentorshipRequest.status == MentorshipStatus.PENDING
        ).first()
        
        if existing:
            raise DuplicateRequestError("A pending request already exists for this mentor-mentee pair")
    
    def validate_request_status(self, request: MentorshipRequest, expected_status: MentorshipStatus):
        if request.status != expected_status:
            raise InvalidStatusTransitionError(f"Request is not {expected_status.value} (current: {request.status})")
    
    def count_active_mentorships_for_mentor(self, mentor_id: int) -> int:
        return self.db.query(MentorshipRequest).filter(
            MentorshipRequest.mentor_id == mentor_id,
            MentorshipRequest.status == MentorshipStatus.ACCEPTED
        ).count()