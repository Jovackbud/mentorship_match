# src/dependencies/auth_dependencies.py
from typing import TypeVar, Type, Callable, Optional
from fastapi import Depends, HTTPException, status, Path, Request
from sqlalchemy.orm import Session
from ..models import User, Mentor, Mentee, MentorshipRequest
from ..database import get_db
from ..security import get_current_user
from ..constants import ErrorMessages

T = TypeVar('T')

def create_ownership_dependency(model_class: Type[T], error_message: str, path_param: Optional[str] = None) -> Callable:
    """
    Factory to create ownership verification dependencies.

    path_param: optional explicit name of the path parameter (e.g. "mentee_id").
                If not provided, defaults to "<modelclassname>_id" (lowercased).
    """
    def dependency(
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ) -> T:
        # Determine path param name
        param_name = path_param or f"{model_class.__name__.lower()}_id"
        raw_id = request.path_params.get(param_name)

        if raw_id is None:
            # This will surface as a 422 with a clearer message
            raise HTTPException(status_code=422, detail=f"Missing path parameter '{param_name}'")

        try:
            entity_id = int(raw_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail=f"Invalid path parameter '{param_name}'")

        entity = db.query(model_class).filter(model_class.id == entity_id).first()
        if not entity:
            raise HTTPException(status_code=404, detail=f"{model_class.__name__} not found")
        if entity.user_id != current_user.id:
            raise HTTPException(status_code=403, detail=error_message)
        return entity

    return dependency

# Create specific dependencies — explicitly bind to route variable names
get_owned_mentor = create_ownership_dependency(Mentor, ErrorMessages.UNAUTHORIZED_MENTOR, path_param="mentor_id")
get_owned_mentee = create_ownership_dependency(Mentee, ErrorMessages.UNAUTHORIZED_MENTEE, path_param="mentee_id")

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