# src/services/feedback_service.py
from sqlalchemy.orm import Session
from ..models import Feedback, Mentee
from ..schemas import FeedbackCreate
from ..exceptions import NotFoundError, UnauthorizedError

class FeedbackService:
    def __init__(self, db: Session):
        self.db = db
    
    def submit_feedback(self, feedback_data: FeedbackCreate, current_user_id: int) -> Feedback:
        """Submits feedback with authorization check"""
        # Verify mentee ownership
        mentee = self.db.query(Mentee).filter(Mentee.id == feedback_data.mentee_id).first()
        if not mentee:
            raise NotFoundError("Mentee profile not found")
        if mentee.user_id != current_user_id:
            raise UnauthorizedError("Not authorized to submit feedback for this mentee")
        
        feedback = Feedback(
            mentee_id=feedback_data.mentee_id,
            mentor_id=feedback_data.mentor_id,
            rating=feedback_data.rating,
            comment=feedback_data.comment
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback