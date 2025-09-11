# src/routers/profile_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Response, Path
from sqlalchemy.orm import Session

from ..services import ProfileService
from ..dependencies.auth_dependencies import get_owned_mentor
from ..dependencies.service_dependencies import get_profile_service
from ..schemas import MentorCreate, MentorUpdate, MentorResponse
from ..models import User, Mentor
from ..security import get_current_user
from ..exceptions import BusinessLogicError

router = APIRouter(tags=["profiles"])

@router.post("/mentors/", response_model=MentorResponse, status_code=201)
async def create_mentor(
    mentor_data: MentorCreate,
    current_user: User = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """Create a mentor profile"""
    try:
        mentor = profile_service.create_mentor(current_user.id, mentor_data.model_dump())
        return mentor
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/mentors/{mentor_id}", response_model=MentorResponse)
async def update_mentor(
    mentor_id: int = Path(..., description="The ID of the mentor to update"),
    mentor_data: MentorUpdate = ...,
    owned_mentor: Mentor = Depends(get_owned_mentor),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """Update a mentor profile"""
    try:
        mentor = profile_service.update_mentor(owned_mentor, mentor_data.model_dump(exclude_unset=True))
        return mentor
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/mentors/{mentor_id}", status_code=204)
async def delete_mentor(
    mentor_id: int = Path(..., description="The ID of the mentor to delete"),
    owned_mentor: Mentor = Depends(get_owned_mentor),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """Delete a mentor profile"""
    try:
        profile_service.delete_mentor(owned_mentor)
        return Response(status_code=204)
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))