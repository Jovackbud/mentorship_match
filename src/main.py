import os
import logging
from fastapi import FastAPI, Depends, HTTPException, status, Query
from typing import List, Dict, Any, Optional, cast
from sqlalchemy.orm import Session
from datetime import datetime

from .config import get_settings
from . import database, models
from . import schemas # <--- IMPORT SCHEMAS
from .matching_service import MatchingService
from . import embeddings
from .embeddings import load_embedding_model
from .vector_store import faiss_index_manager

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Career-Focused Mentorship Matching API",
    description="A lightweight neural-matching pipeline for mentor-mentee recommendations.",
    version="1.0.0",
)

# --- API Endpoints ---

@app.on_event("startup")
async def startup_event():
    """Initializes database, loads embedding model, and populates FAISS index on startup."""
    logger.info("Application startup event triggered.")
    try:
        database.create_db_and_tables()
        load_embedding_model() # Pre-load the Sentence Transformer model
        
        with database.SessionLocal() as db:
            matching_service = MatchingService(db)
            matching_service.initialize_faiss_with_mentors()
        logger.info("Startup sequence completed successfully.")
    except Exception as e:
        logger.critical(f"Critical error during startup: {e}", exc_info=True)
        # Depending on desired behavior, could sys.exit(1) here for unrecoverable errors

@app.post("/mentors/", response_model=schemas.MentorResponse, status_code=status.HTTP_201_CREATED)
async def create_mentor(mentor_data: schemas.MentorCreate, db: Session = Depends(database.get_db)):
    """
    Registers a new mentor in the system and adds their embedding to the FAISS index.
    The database will assign the integer ID automatically.
    """
    try:
        db_mentor = models.Mentor(
            bio=mentor_data.bio,
            expertise=mentor_data.expertise,
            capacity=mentor_data.capacity,
            availability=mentor_data.availability.model_dump(mode='json') if mentor_data.availability else None,
            preferences=mentor_data.preferences.model_dump(mode='json') if mentor_data.preferences else None,
            demographics=mentor_data.demographics
        )
        db.add(db_mentor)
        db.commit()
        db.refresh(db_mentor)

        text_to_embed = f"{db_mentor.bio or ''} {db_mentor.expertise or ''}"
        mentor_embedding = embeddings.get_embeddings([text_to_embed])

        if mentor_embedding is None or not mentor_embedding:
            logger.error(f"Failed to generate embedding for new mentor {db_mentor.id}. Skipping FAISS update.")
        else:
            db_mentor.embedding = cast(List[float], mentor_embedding[0])
            db.add(db_mentor)
            db.commit()
            db.refresh(db_mentor)
            
            faiss_index_manager.add_embedding(
                cast(List[float], db_mentor.embedding), db_mentor.id
            )

        logger.info(f"Mentor {db_mentor.id} created and indexed successfully.")
        return db_mentor
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating mentor: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create mentor.")

@app.put("/mentors/{mentor_id}", response_model=schemas.MentorResponse)
async def update_mentor(
    mentor_id: int,
    mentor_data: schemas.MentorUpdate,
    db: Session = Depends(database.get_db)
):
    """
    Updates an existing mentor's profile and re-indexes their embedding in FAISS if text fields change.
    """
    db_mentor = db.query(models.Mentor).filter(models.Mentor.id == mentor_id).first()
    if db_mentor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentor not found")

    old_text_to_embed = f"{db_mentor.bio or ''} {db_mentor.expertise or ''}"
    text_fields_changed = False

    update_data = mentor_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if key == 'availability' or key == 'preferences' or key == 'demographics': # Include demographics
            setattr(db_mentor, key, value if value is not None else None)
        elif key in ['bio', 'expertise']:
            if getattr(db_mentor, key) != value:
                text_fields_changed = True
            setattr(db_mentor, key, value)
        else:
            setattr(db_mentor, key, value)

    db.add(db_mentor)
    db.commit()
    db.refresh(db_mentor)

    new_text_to_embed = f"{db_mentor.bio or ''} {db_mentor.expertise or ''}"
    if text_fields_changed or new_text_to_embed != old_text_to_embed:
        new_embedding = embeddings.get_embeddings([new_text_to_embed])
        if new_embedding is None or not new_embedding:
            logger.error(f"Failed to generate embedding for updated mentor {db_mentor.id}. FAISS index not updated for text changes.")
        else:
            db_mentor.embedding = cast(List[float], new_embedding[0])
            db.add(db_mentor)
            db.commit()
            db.refresh(db_mentor)
            faiss_index_manager.add_embedding(
                cast(List[float], db_mentor.embedding), db_mentor.id
            )
            logger.info(f"Mentor {db_mentor.id} updated and re-indexed in FAISS successfully.")
    else:
        logger.info(f"Mentor {db_mentor.id} updated in DB, no text changes, FAISS index not touched.")

    return db_mentor

@app.delete("/mentors/{mentor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mentor(mentor_id: int, db: Session = Depends(database.get_db)):
    """
    Deletes a mentor from the system and removes their embedding from the FAISS index.
    """
    db_mentor = db.query(models.Mentor).filter(models.Mentor.id == mentor_id).first()
    if db_mentor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentor not found")

    active_mentees_for_mentor = db.query(models.MentorshipRequest).filter(
        models.MentorshipRequest.mentor_id == mentor_id,
        models.MentorshipRequest.status == models.MentorshipStatus.ACCEPTED.value
    ).count()

    if active_mentees_for_mentor > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Mentor has {active_mentees_for_mentor} active mentees. Cannot delete until relationships are ended (by REJECT or COMPLETE).")

    db.delete(db_mentor)
    db.commit()

    faiss_index_manager.remove_embedding(mentor_id)
    logger.info(f"Mentor {mentor_id} deleted from DB and FAISS index.")
    return # 204 No Content

@app.post("/match/", response_model=schemas.MatchResponse)
async def get_matches(
    mentee_request: schemas.MenteeMatchRequest, # Use schema model
    db: Session = Depends(database.get_db)
):
    """
    Recommends top mentors for a given mentee profile.
    Accepts full mentee profile details directly and stores the mentee,
    returning the generated mentee_id for feedback.
    """
    logger.info("Received a new match request.")
    matching_service = MatchingService(db)

    mentee_profile_data = mentee_request.model_dump(mode='json')

    db_mentee = models.Mentee(
        bio=mentee_request.bio,
        goals=mentee_request.goals,
        preferences=mentee_request.preferences.model_dump(mode='json') if mentee_request.preferences else None,
        availability=mentee_request.availability.model_dump(mode='json') if mentee_request.availability else None,
        mentorship_style=mentee_request.mentorship_style
    )
    db.add(db_mentee)
    db.commit()
    db.refresh(db_mentee)
    generated_mentee_id = cast(int, db_mentee.id)

    recommendations = matching_service.get_mentor_recommendations(mentee_profile_data)

    if not recommendations:
        logger.warning("No recommendations found for the mentee after matching process.")
        return schemas.MatchResponse( # Use schema model
            mentee_id=generated_mentee_id,
            recommendations=[],
            message=f"No suitable mentors found based on your criteria for mentee_id={generated_mentee_id}. Please try broadening your preferences."
        )

    matched_mentors_response = [
        schemas.MatchedMentor(**rec) for rec in recommendations # Use schema model
    ]

    return schemas.MatchResponse( # Use schema model
        mentee_id=generated_mentee_id,
        recommendations=matched_mentors_response,
        message="Top mentor recommendations generated successfully."
    )

@app.post("/mentee/{mentee_id}/pick_mentor/{mentor_id}", response_model=schemas.MentorshipRequestResponse, status_code=status.HTTP_201_CREATED)
async def pick_mentor(
    mentee_id: int,
    mentor_id: int,
    request_message: Optional[str] = Query(None, description="Optional message for the mentor."),
    db: Session = Depends(database.get_db)
):
    """
    Allows a mentee to pick a mentor from the recommendations, creating a PENDING mentorship request.
    This also checks the mentee's current active mentorship count.
    """
    db_mentee = db.query(models.Mentee).filter(models.Mentee.id == mentee_id).first()
    if db_mentee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentee not found")

    db_mentor = db.query(models.Mentor).filter(models.Mentor.id == mentor_id).first()
    if db_mentor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentor not found")
    
    # Check mentee's active mentorship limit
    active_mentorships_for_mentee = db.query(models.MentorshipRequest).filter(
        models.MentorshipRequest.mentee_id == mentee_id,
        models.MentorshipRequest.status == models.MentorshipStatus.ACCEPTED.value
    ).count()

    if active_mentorships_for_mentee >= settings.MENTEE_MAX_ACTIVE_MENTORS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Mentee has reached maximum limit of {settings.MENTEE_MAX_ACTIVE_MENTORS} active mentorships.")

    # Check if a pending request already exists for this pair
    existing_pending_request = db.query(models.MentorshipRequest).filter(
        models.MentorshipRequest.mentee_id == mentee_id,
        models.MentorshipRequest.mentor_id == mentor_id,
        models.MentorshipRequest.status == models.MentorshipStatus.PENDING.value
    ).first()
    if existing_pending_request:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A pending request already exists for this mentee and mentor.")

    # Check mentor capacity before creating request (optional, can also be done on accept)
    if db_mentor.current_mentees >= db_mentor.capacity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mentor has reached maximum capacity.")


    db_request = models.MentorshipRequest(
        mentee_id=mentee_id,
        mentor_id=mentor_id,
        status=models.MentorshipStatus.PENDING.value,
        request_message=request_message
    )
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    logger.info(f"Mentee {mentee_id} picked mentor {mentor_id}. Request {db_request.id} created with PENDING status.")
    return db_request

@app.put("/mentor/{mentor_id}/request/{request_id}/accept", response_model=schemas.MentorshipRequestResponse)
async def accept_mentee_request(
    mentor_id: int,
    request_id: int,
    db: Session = Depends(database.get_db)
):
    """
    Allows a mentor to accept a pending mentorship request from a mentee.
    Increments mentor's current_mentees count.
    """
    db_request = db.query(models.MentorshipRequest).filter(
        models.MentorshipRequest.id == request_id,
        models.MentorshipRequest.mentor_id == mentor_id
    ).first()

    if db_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentorship request not found for this mentor.")
    if db_request.status != models.MentorshipStatus.PENDING.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Request is not PENDING (current status: {db_request.status}). Only PENDING requests can be ACCEPTED.")

    db_mentor = db.query(models.Mentor).filter(models.Mentor.id == mentor_id).first()
    if db_mentor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentor not found (internal error).")

    if db_mentor.current_mentees >= db_mentor.capacity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mentor has reached maximum capacity and cannot accept more mentees.")
    
    # Check mentee's active mentorship limit before accepting
    active_mentorships_for_mentee = db.query(models.MentorshipRequest).filter(
        models.MentorshipRequest.mentee_id == db_request.mentee_id,
        models.MentorshipRequest.status == models.MentorshipStatus.ACCEPTED.value
    ).count()

    if active_mentorships_for_mentee >= settings.MENTEE_MAX_ACTIVE_MENTORS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Mentee has reached maximum limit of {settings.MENTEE_MAX_ACTIVE_MENTORS} active mentorships. Mentor cannot accept.")


    db_request.status = models.MentorshipStatus.ACCEPTED.value
    db_request.acceptance_date = datetime.now()
    db_mentor.current_mentees += 1

    db.add(db_request)
    db.add(db_mentor)
    db.commit()
    db.refresh(db_request)
    db.refresh(db_mentor)

    logger.info(f"Mentorship request {request_id} from mentee {db_request.mentee_id} accepted by mentor {mentor_id}.")
    return db_request

@app.put("/mentor/{mentor_id}/request/{request_id}/reject", response_model=schemas.MentorshipRequestResponse)
async def reject_mentee_request(
    mentor_id: int,
    request_id: int,
    rejection_reason: Optional[str] = Query(None, description="Optional reason for rejection."),
    db: Session = Depends(database.get_db)
):
    """
    Allows a mentor to reject a mentorship request (either PENDING or ACCEPTED).
    If the request was ACCEPTED, it decrements the current_mentees count.
    """
    db_request = db.query(models.MentorshipRequest).filter(
        models.MentorshipRequest.id == request_id,
        models.MentorshipRequest.mentor_id == mentor_id
    ).first()

    if db_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentorship request not found for this mentor.")
    if db_request.status in [models.MentorshipStatus.REJECTED.value, models.MentorshipStatus.COMPLETED.value, models.MentorshipStatus.CANCELLED.value]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Request is already {db_request.status}.")

    db_mentor = db.query(models.Mentor).filter(models.Mentor.id == mentor_id).first()
    if db_mentor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentor not found (internal error).")

    # If the request was previously accepted, decrement current_mentees
    if db_request.status == models.MentorshipStatus.ACCEPTED.value:
        if db_mentor.current_mentees > 0:
            db_mentor.current_mentees -= 1
        db.add(db_mentor)
        logger.info(f"Mentor {mentor_id} current_mentees decremented due to rejection of ACCEPTED request {request_id}.")

    db_request.status = models.MentorshipStatus.REJECTED.value
    db_request.rejection_reason = rejection_reason
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    db.refresh(db_mentor) # Refresh mentor to get updated count

    logger.info(f"Mentorship request {request_id} from mentee {db_request.mentee_id} rejected by mentor {mentor_id}.")
    return db_request

@app.put("/mentor/{mentor_id}/request/{request_id}/complete", response_model=schemas.MentorshipRequestResponse)
async def complete_mentee_request(
    mentor_id: int,
    request_id: int,
    db: Session = Depends(database.get_db)
):
    """
    Allows a mentor to mark an ACCEPTED mentorship request as COMPLETED.
    Decrements mentor's current_mentees count.
    """
    db_request = db.query(models.MentorshipRequest).filter(
        models.MentorshipRequest.id == request_id,
        models.MentorshipRequest.mentor_id == mentor_id
    ).first()

    if db_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentorship request not found for this mentor.")
    if db_request.status != models.MentorshipStatus.ACCEPTED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Request is not ACCEPTED (current status: {db_request.status}). Only ACCEPTED requests can be COMPLETED.")

    db_mentor = db.query(models.Mentor).filter(models.Mentor.id == mentor_id).first()
    if db_mentor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentor not found (internal error).")

    db_request.status = models.MentorshipStatus.COMPLETED.value
    db_request.completed_date = datetime.now()
    if db_mentor.current_mentees > 0:
        db_mentor.current_mentees -= 1 # Free up capacity

    db.add(db_request)
    db.add(db_mentor)
    db.commit()
    db.refresh(db_request)
    db.refresh(db_mentor)

    logger.info(f"Mentorship request {request_id} from mentee {db_request.mentee_id} marked as COMPLETED by mentor {mentor_id}.")
    return db_request

@app.put("/mentee/{mentee_id}/request/{request_id}/cancel", response_model=schemas.MentorshipRequestResponse)
async def cancel_mentee_request(
    mentee_id: int,
    request_id: int,
    db: Session = Depends(database.get_db)
):
    """
    Allows a mentee to cancel a PENDING mentorship request.
    No impact on mentor's current_mentees as it was never accepted.
    """
    db_request = db.query(models.MentorshipRequest).filter(
        models.MentorshipRequest.id == request_id,
        models.MentorshipRequest.mentee_id == mentee_id
    ).first()

    if db_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentorship request not found for this mentee.")
    if db_request.status != models.MentorshipStatus.PENDING.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Request is not PENDING (current status: {db_request.status}). Only PENDING requests can be CANCELLED.")

    db_request.status = models.MentorshipStatus.CANCELLED.value
    db.add(db_request)
    db.commit()
    db.refresh(db_request)

    logger.info(f"Mentorship request {request_id} from mentee {mentee_id} cancelled.")
    return db_request


@app.put("/mentee/{mentee_id}/request/{request_id}/conclude", response_model=schemas.MentorshipRequestResponse)
async def conclude_mentorship_as_mentee(
    mentee_id: int,
    request_id: int,
    db: Session = Depends(database.get_db)
):
    """
    Allows a mentee to conclude an ACCEPTED mentorship request.
    This will mark the request as COMPLETED and decrement the mentor's current_mentees count.
    """
    db_request = db.query(models.MentorshipRequest).filter(
        models.MentorshipRequest.id == request_id,
        models.MentorshipRequest.mentee_id == mentee_id
    ).first()

    if db_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentorship request not found for this mentee.")
    if db_request.status != models.MentorshipStatus.ACCEPTED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Request is not ACCEPTED (current status: {db_request.status}). Only ACCEPTED requests can be concluded.")

    db_mentor = db.query(models.Mentor).filter(models.Mentor.id == db_request.mentor_id).first()
    if db_mentor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated mentor not found (internal error).")

    db_request.status = models.MentorshipStatus.COMPLETED.value
    db_request.completed_date = datetime.now()
    if db_mentor.current_mentees > 0:
        db_mentor.current_mentees -= 1 # Free up capacity

    db.add(db_request)
    db.add(db_mentor)
    db.commit()
    db.refresh(db_request)
    db.refresh(db_mentor)

    logger.info(f"Mentee {mentee_id} concluded mentorship request {request_id}. Status set to COMPLETED.")
    return db_request


@app.post("/feedback/", status_code=status.HTTP_201_CREATED)
async def submit_feedback(feedback: schemas.FeedbackCreate, db: Session = Depends(database.get_db)): # Use schema model
    """
    Submits feedback on a mentor-mentee match.
    """
    try:
        db_feedback = models.Feedback(
            mentee_id=feedback.mentee_id,
            mentor_id=feedback.mentor_id,
            rating=feedback.rating,
            comment=feedback.comment
        )
        db.add(db_feedback)
        db.commit()
        db.refresh(db_feedback)
        logger.info(f"Feedback submitted for mentee {feedback.mentee_id} and mentor {feedback.mentor_id}.")
        return {"message": "Feedback submitted successfully."}
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting feedback: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not submit feedback.")