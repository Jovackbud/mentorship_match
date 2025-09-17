from fastapi import APIRouter, Depends, HTTPException, status, Path, Body
from ..services.feedback_service import FeedbackService
from ..dependencies.auth_dependencies import get_owned_mentee
from ..dependencies.service_dependencies import get_feedback_service
from ..schemas import FeedbackCreate, FeedbackResponse
from ..models import Mentee, User, MentorshipRequest, Mentor
from ..security import get_current_user
from ..exceptions import BusinessLogicError
from sqlalchemy.orm import Session
from ..database import get_db

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

# New: Submit feedback tied to a mentorship request (works for both mentor and mentee roles)
@router.post("/requests/{request_id}/feedback", status_code=201, response_model=FeedbackResponse)
async def submit_request_feedback(
    request_id: int = Path(..., description="The mentorship request ID this feedback refers to"),
    rating: int | None = Body(None, embed=True),
    comment: str | None = Body(None, embed=True),
    current_user: User = Depends(get_current_user),
    feedback_service: FeedbackService = Depends(get_feedback_service),
    db: Session = Depends(get_db)
):
    """Submit optional feedback (rating/comment) for a mentorship request.
    Accepts submissions from either the mentor or the mentee involved in the request.
    If neither rating nor comment is provided, no feedback is created and a 204 is returned.
    """
    try:
        # If nothing provided, treat as skip gracefully
        if rating is None and (comment is None or comment.strip() == ""):
            # No content to create
            from fastapi import Response
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        # Load the request and verify the current user is a participant
        req: MentorshipRequest | None = db.query(MentorshipRequest).filter(MentorshipRequest.id == request_id).first()
        if not req:
            raise HTTPException(status_code=404, detail="Mentorship request not found")

        # Resolve mentor and mentee to their owning users
        mentee: Mentee | None = db.query(Mentee).filter(Mentee.id == req.mentee_id).first()
        mentor: Mentor | None = db.query(Mentor).filter(Mentor.id == req.mentor_id).first()
        if not mentee or not mentor:
            raise HTTPException(status_code=400, detail="Invalid mentorship request participants")

        if current_user.id not in {mentee.user_id, mentor.user_id}:
            raise HTTPException(status_code=403, detail="Not authorized to submit feedback for this request")

        # Build FeedbackCreate using authoritative IDs from the request (ignore any client-provided IDs)
        feedback_payload = FeedbackCreate(
            mentee_id=mentee.id,
            mentor_id=mentor.id,
            rating=rating,
            comment=comment.strip() if comment else None,
        )
        feedback = feedback_service.submit_feedback(feedback_payload, current_user.id)
        return feedback
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))