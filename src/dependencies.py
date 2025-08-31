# src/dependencies.py
from fastapi import HTTPException, status, Depends, Path
from sqlalchemy.orm import Session
from . import models, database, security
from typing import Optional # Import Optional for verify_feedback_submission

# Dependency to get an owned Mentor profile
def get_owned_mentor_profile(
    mentor_id: int = Path(..., description="The ID of the mentor profile."),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
) -> models.Mentor:
    """
    Verifies that the current authenticated user owns the mentor profile
    identified by mentor_id in the path. Returns the Mentor object.
    """
    mentor = db.query(models.Mentor).filter(models.Mentor.id == mentor_id).first()
    if not mentor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentor not found.")
    if mentor.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this mentor profile.")
    return mentor

# Dependency to get an owned Mentee profile
def get_owned_mentee_profile(
    mentee_id: int = Path(..., description="The ID of the mentee profile."),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
) -> models.Mentee:
    """
    Verifies that the current authenticated user owns the mentee profile
    identified by mentee_id in the path. Returns the Mentee object.
    """
    mentee = db.query(models.Mentee).filter(models.Mentee.id == mentee_id).first()
    if not mentee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentee not found.")
    if mentee.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this mentee profile.")
    return mentee

# Dependency to get a MentorshipRequest that the current user's MENTOR profile is associated with
def get_mentor_owned_request(
    mentor_id: int = Path(..., description="The ID of the mentor profile involved in the request."),
    request_id: int = Path(..., description="The ID of the mentorship request."),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
) -> models.MentorshipRequest:
    """
    Verifies that the current authenticated user owns the mentor profile
    identified by mentor_id, AND that this mentor profile is the mentor
    associated with the mentorship request identified by request_id.
    Returns the MentorshipRequest object.
    """
    # First, verify the user owns the mentor profile
    mentor_profile = get_owned_mentor_profile(mentor_id=mentor_id, db=db, current_user=current_user)

    # Then, verify the request exists and is for this specific mentor
    db_request = db.query(models.MentorshipRequest).filter(
        models.MentorshipRequest.id == request_id,
        models.MentorshipRequest.mentor_id == mentor_profile.id # Ensure request is for this mentor
    ).first()

    if not db_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentorship request not found for this mentor.")
    
    return db_request

# Dependency to get a MentorshipRequest that the current user's MENTEE profile is associated with
def get_mentee_owned_request(
    mentee_id: int = Path(..., description="The ID of the mentee profile involved in the request."),
    request_id: int = Path(..., description="The ID of the mentorship request."),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
) -> models.MentorshipRequest:
    """
    Verifies that the current authenticated user owns the mentee profile
    identified by mentee_id, AND that this mentee profile is the mentee
    associated with the mentorship request identified by request_id.
    Returns the MentorshipRequest object.
    """
    # First, verify the user owns the mentee profile
    mentee_profile = get_owned_mentee_profile(mentee_id=mentee_id, db=db, current_user=current_user)

    # Then, verify the request exists and is for this specific mentee
    db_request = db.query(models.MentorshipRequest).filter(
        models.MentorshipRequest.id == request_id,
        models.MentorshipRequest.mentee_id == mentee_profile.id # Ensure request is for this mentee
    ).first()

    if not db_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentorship request not found for this mentee.")
    
    return db_request

# Dependency for feedback submission - ensure current_user is the mentee submitting feedback
def verify_feedback_submission_ownership(
    feedback: Optional[dict] = None, # Feedback data from the request body
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
) -> None:
    """
    Verifies that the mentee_id specified in the feedback payload belongs to the current user.
    """
    if not feedback: # If feedback is None, perhaps it was not provided in the body (unlikely for POST)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Feedback data is required.")
        
    mentee_id_from_payload = feedback.get('mentee_id')
    if not mentee_id_from_payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mentee ID is required in feedback.")

    db_mentee = db.query(models.Mentee).filter(models.Mentee.id == mentee_id_from_payload).first()

    if not db_mentee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentee profile not found.")
    
    if db_mentee.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to submit feedback for this mentee profile.")
    
    # If successful, no return value needed for this dependency, it just performs a check.
    # The actual FeedbackCreate schema validation happens in the endpoint.