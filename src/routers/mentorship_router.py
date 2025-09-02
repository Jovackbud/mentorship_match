# src/routers/mentorship_router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from sqlalchemy.orm import Session

from ..services import MentorshipService
from ..dependencies.auth_dependencies import get_owned_mentor, get_owned_mentee, get_mentor_request_with_auth, get_mentee_request_with_auth
from ..dependencies.service_dependencies import get_mentorship_service
from ..utils.response_enricher import ResponseEnricher
from ..schemas import MentorshipRequestResponse
from ..models import Mentor, Mentee, MentorshipRequest
from ..exceptions import BusinessLogicError

router = APIRouter(prefix="/api", tags=["mentorship"])

@router.get("/mentors/{mentor_id}/requests", response_model=List[MentorshipRequestResponse])
async def get_mentor_requests(
    owned_mentor: Mentor = Depends(get_owned_mentor),
    mentorship_service: MentorshipService = Depends(get_mentorship_service)
):
    """Get all requests for a mentor"""
    requests = mentorship_service.get_requests_for_mentor(owned_mentor.id)
    return ResponseEnricher.enrich_requests(requests)

@router.get("/mentees/{mentee_id}/requests", response_model=List[MentorshipRequestResponse])
async def get_mentee_requests(
    owned_mentee: Mentee = Depends(get_owned_mentee),
    mentorship_service: MentorshipService = Depends(get_mentorship_service)
):
    """Get all requests for a mentee"""
    requests = mentorship_service.get_requests_for_mentee(owned_mentee.id)
    return ResponseEnricher.enrich_requests(requests)

@router.post("/mentee/{mentee_id}/pick_mentor/{mentor_id}", response_model=MentorshipRequestResponse, status_code=201)
async def pick_mentor(
    mentor_id: int,
    owned_mentee: Mentee = Depends(get_owned_mentee),
    mentorship_service: MentorshipService = Depends(get_mentorship_service),
    request_message: Optional[str] = Query(None)
):
    """Create a mentorship request"""
    try:
        request = mentorship_service.create_request(owned_mentee.id, mentor_id, request_message)
        return ResponseEnricher.enrich_single_request(request)
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/mentor/{mentor_id}/request/{request_id}/accept", response_model=MentorshipRequestResponse)
async def accept_request(
    request: MentorshipRequest = Depends(get_mentor_request_with_auth),
    mentorship_service: MentorshipService = Depends(get_mentorship_service)
):
    """Accept a mentorship request"""
    try:
        updated_request = mentorship_service.accept_request(request)
        return ResponseEnricher.enrich_single_request(updated_request)
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/mentor/{mentor_id}/request/{request_id}/reject", response_model=MentorshipRequestResponse)
async def reject_request(
    request: MentorshipRequest = Depends(get_mentor_request_with_auth),
    mentorship_service: MentorshipService = Depends(get_mentorship_service),
    rejection_reason: Optional[str] = Query(None)
):
    """Reject a mentorship request"""
    try:
        updated_request = mentorship_service.reject_request(request, rejection_reason)
        return ResponseEnricher.enrich_single_request(updated_request)
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/mentor/{mentor_id}/request/{request_id}/complete", response_model=MentorshipRequestResponse)
async def complete_request(
    request: MentorshipRequest = Depends(get_mentor_request_with_auth),
    mentorship_service: MentorshipService = Depends(get_mentorship_service)
):
    """Complete a mentorship request"""
    try:
        updated_request = mentorship_service.complete_request(request)
        return ResponseEnricher.enrich_single_request(updated_request)
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/mentee/{mentee_id}/request/{request_id}/cancel", response_model=MentorshipRequestResponse)
async def cancel_request(
    request: MentorshipRequest = Depends(get_mentee_request_with_auth),
    mentorship_service: MentorshipService = Depends(get_mentorship_service)
):
    """Cancel a mentorship request"""
    try:
        updated_request = mentorship_service.cancel_request(request)
        return ResponseEnricher.enrich_single_request(updated_request)
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/mentee/{mentee_id}/request/{request_id}/conclude", response_model=MentorshipRequestResponse)
async def conclude_request(
    request: MentorshipRequest = Depends(get_mentee_request_with_auth),
    mentorship_service: MentorshipService = Depends(get_mentorship_service)
):
    """Conclude a mentorship request as mentee"""
    try:
        updated_request = mentorship_service.complete_request(request)
        return ResponseEnricher.enrich_single_request(updated_request)
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))