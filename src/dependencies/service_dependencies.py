# src/dependencies/service_dependencies.py (COMPLETE)
from fastapi import Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.mentorship_service import MentorshipService
from ..services.profile_service import ProfileService
from ..services.feedback_service import FeedbackService

def get_mentorship_service(db: Session = Depends(get_db)) -> MentorshipService:
    return MentorshipService(db)

def get_profile_service(db: Session = Depends(get_db)) -> ProfileService:
    return ProfileService(db)

def get_feedback_service(db: Session = Depends(get_db)) -> FeedbackService:
    return FeedbackService(db)id: int, mentor_id: int):
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