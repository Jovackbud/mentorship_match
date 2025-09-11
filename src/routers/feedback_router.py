from fastapi import APIRouter, Depends, HTTPException, status, Path
from ..services.feedback_service import FeedbackService
from ..dependencies.auth_dependencies import get_owned_mentee
from ..dependencies.service_dependencies import get_feedback_service
from ..schemas import FeedbackCreate, FeedbackResponse
from ..models import Mentee, User
from ..security import get_current_user
from ..exceptions import BusinessLogicError

router = APIRouter(prefix="/api", tags=["feedback"])

@router.post("/mentees/{mentee_id}/feedback", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    mentee_id: int = Path(..., description="The ID of the mentee submitting feedback"),
    feedback_data: FeedbackCreate = ...,
    owned_mentee: Mentee = Depends(get_owned_mentee),
    feedback_service: FeedbackService = Depends(get_feedback_service),
    current_user: User = Depends(get_current_user)
):
    """Submit feedback for a mentor from a mentee"""
    try:
        if feedback_data.mentee_id != mentee_id:
            raise HTTPException(status_code=400, detail="Mentee ID in payload must match URL")
        feedback = feedback_service.submit_feedback(feedback_data, current_user.id)
        return feedback
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))