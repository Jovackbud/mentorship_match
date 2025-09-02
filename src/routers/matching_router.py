# src/routers/matching_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..matching_service import MatchingService
from ..dependencies.auth_dependencies import get_owned_mentee
from ..dependencies.service_dependencies import get_profile_service
from ..schemas import MenteeMatchRequest, MatchResponse
from ..models import Mentee, User
from ..security import get_current_user
from ..exceptions import BusinessLogicError
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["matching"])

@router.post("/mentees/{mentee_id}/match", response_model=MatchResponse)
async def get_mentor_matches(
    owned_mentee: Mentee = Depends(get_owned_mentee),
    db: Session = Depends(get_db)
):
    """Get mentor recommendations for a mentee"""
    try:
        matching_service = MatchingService(db)
        
        # Convert mentee to dict format expected by matching service
        mentee_data = {
            'name': owned_mentee.name,
            'bio': owned_mentee.bio,
            'goals': owned_mentee.goals,
            'preferences': owned_mentee.preferences,
            'availability': owned_mentee.availability,
            'mentorship_style': owned_mentee.mentorship_style
        }
        
        recommendations = matching_service.get_mentor_recommendations(mentee_data)
        
        return MatchResponse(
            mentee_id=owned_mentee.id,
            mentee_name=owned_mentee.name,
            recommendations=recommendations
        )
    except Exception as e:
        logger.error(f"Error getting matches for mentee {owned_mentee.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate mentor recommendations")

@router.post("/mentees/match-or-create", response_model=MatchResponse)
async def match_or_create_mentee(
    mentee_request: MenteeMatchRequest,
    current_user: User = Depends(get_current_user),
    profile_service = Depends(get_profile_service),
    db: Session = Depends(get_db)
):
    """Create or update mentee profile and get mentor recommendations"""
    try:
        # Create or update mentee profile
        mentee_data = mentee_request.model_dump()
        mentee = profile_service.create_or_update_mentee(current_user.id, mentee_data)
        
        # Get matching recommendations
        matching_service = MatchingService(db)
        recommendations = matching_service.get_mentor_recommendations(mentee_data)
        
        return MatchResponse(
            mentee_id=mentee.id,
            mentee_name=mentee.name,
            recommendations=recommendations
        )
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in match_or_create_mentee: {e}")
        raise HTTPException(status_code=500, detail="Failed to process mentee request")