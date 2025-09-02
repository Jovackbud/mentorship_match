# src/services/mentorship_service.py
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timezone
from ..models import MentorshipRequest, Mentor, Mentee, MentorshipStatus
from ..config import get_settings
from ..exceptions import CapacityExceededError, InvalidStatusTransitionError, DuplicateRequestError
from ..utils.validation_utils import ValidationUtils

class MentorshipService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.validator = ValidationUtils(db)
    
    def create_request(self, mentee_id: int, mentor_id: int, message: Optional[str] = None) -> MentorshipRequest:
        """Creates a mentorship request with all necessary validations"""
        # Validate capacities and existing requests
        self.validator.validate_mentee_capacity(mentee_id)
        mentor = self.validator.get_mentor_or_404(mentor_id)
        self.validator.validate_mentor_capacity(mentor)
        self.validator.check_no_pending_request(mentee_id, mentor_id)
        
        request = MentorshipRequest(
            mentee_id=mentee_id,
            mentor_id=mentor_id,
            status=MentorshipStatus.PENDING,
            request_message=message
        )
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        return request
    
    def accept_request(self, request: MentorshipRequest) -> MentorshipRequest:
        """Accepts a mentorship request"""
        self.validator.validate_request_status(request, MentorshipStatus.PENDING)
        self.validator.validate_mentor_capacity(request.mentor)
        self.validator.validate_mentee_capacity(request.mentee_id)
        
        request.status = MentorshipStatus.ACCEPTED
        request.acceptance_date = datetime.now(timezone.utc)
        request.mentor.current_mentees += 1
        
        self.db.add_all([request, request.mentor])
        self.db.commit()
        return request
    
    def reject_request(self, request: MentorshipRequest, reason: Optional[str] = None) -> MentorshipRequest:
        """Rejects a mentorship request"""
        if request.status in [MentorshipStatus.REJECTED, MentorshipStatus.COMPLETED, MentorshipStatus.CANCELLED]:
            raise InvalidStatusTransitionError(f"Request is already {request.status}")
        
        # If previously accepted, decrement counter
        if request.status == MentorshipStatus.ACCEPTED and request.mentor.current_mentees > 0:
            request.mentor.current_mentees -= 1
            self.db.add(request.mentor)
        
        request.status = MentorshipStatus.REJECTED
        request.rejection_reason = reason
        self.db.add(request)
        self.db.commit()
        return request
    
    def complete_request(self, request: MentorshipRequest) -> MentorshipRequest:
        """Completes a mentorship request"""
        self.validator.validate_request_status(request, MentorshipStatus.ACCEPTED)
        
        request.status = MentorshipStatus.COMPLETED
        request.completed_date = datetime.now(timezone.utc)
        if request.mentor.current_mentees > 0:
            request.mentor.current_mentees -= 1
        
        self.db.add_all([request, request.mentor])
        self.db.commit()
        return request
    
    def cancel_request(self, request: MentorshipRequest) -> MentorshipRequest:
        """Cancels a pending mentorship request"""
        self.validator.validate_request_status(request, MentorshipStatus.PENDING)
        
        request.status = MentorshipStatus.CANCELLED
        self.db.add(request)
        self.db.commit()
        return request
    
    def get_requests_for_mentor(self, mentor_id: int) -> list[MentorshipRequest]:
        """Get all requests for a mentor with eager loading"""
        return self.db.query(MentorshipRequest).options(
            joinedload(MentorshipRequest.mentee)
        ).filter(MentorshipRequest.mentor_id == mentor_id).all()
    
    def get_requests_for_mentee(self, mentee_id: int) -> list[MentorshipRequest]:
        """Get all requests for a mentee with eager loading"""
        return self.db.query(MentorshipRequest).options(
            joinedload(MentorshipRequest.mentor)
        ).filter(MentorshipRequest.mentee_id == mentee_id).all()