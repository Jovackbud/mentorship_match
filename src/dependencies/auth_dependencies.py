# src/dependencies/auth_dependencies.py
from typing import TypeVar, Type, Callable, Optional
from fastapi import Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from ..models import User, Mentor, Mentee, MentorshipRequest
from ..database import get_db
from ..security import get_current_user
from ..constants import ErrorMessages

T = TypeVar('T')

def create_ownership_dependency(model_class: Type[T], error_message: str) -> Callable:
    """
    Factory to create ownership verification dependencies.
    The dependency function directly declares the path parameter,
    allowing FastAPI to automatically handle its parsing and documentation.
    """
    def dependency(
        # The router function (e.g., update_mentor) will explicitly define mentor_id: int = Path(...)
        # FastAPI's dependency injection will then map this path parameter to 'entity_id' here.
        # The 'alias' parameter helps document which path parameter this dependency expects.
        entity_id: int = Path(..., alias=f"{model_class.__name__.lower()}_id", description=f"The ID of the {model_class.__name__.lower()}"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ) -> T:
        entity = db.query(model_class).filter(model_class.id == entity_id).first()
        if not entity:
            raise HTTPException(status_code=404, detail=f"{model_class.__name__} not found")
        if entity.user_id != current_user.id:
            raise HTTPException(status_code=403, detail=error_message)
        return entity

    return dependency

# Create specific dependencies — explicitly bind to route variable names
get_owned_mentor = create_ownership_dependency(Mentor, ErrorMessages.UNAUTHORIZED_MENTOR)
get_owned_mentee = create_ownership_dependency(Mentee, ErrorMessages.UNAUTHORIZED_MENTEE)

def get_mentor_request_with_auth(
    mentor_id: int = Path(...),
    request_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> MentorshipRequest:
    """Gets mentorship request with mentor ownership verification"""
    # Verify mentor ownership
    mentor = db.query(Mentor).filter(Mentor.id == mentor_id, Mentor.user_id == current_user.id).first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found or not authorized")
    
    # Get request for this mentor
    request = db.query(MentorshipRequest).filter(
        MentorshipRequest.id == request_id,
        MentorshipRequest.mentor_id == mentor_id
    ).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="Mentorship request not found")
    
    return request

def get_mentee_request_with_auth(
    mentee_id: int = Path(...),
    request_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> MentorshipRequest:
    """Gets mentorship request with mentee ownership verification"""
    # Verify mentee ownership
    mentee = db.query(Mentee).filter(Mentee.id == mentee_id, Mentee.user_id == current_user.id).first()
    if not mentee:
        raise HTTPException(status_code=404, detail="Mentee not found or not authorized")
    
    # Get request for this mentee
    request = db.query(MentorshipRequest).filter(
        MentorshipRequest.id == request_id,
        MentorshipRequest.mentee_id == mentee_id
    ).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="Mentorship request not found")
    
    return request