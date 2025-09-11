# src/dependencies/service_dependencies.py
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
    return FeedbackService(db)