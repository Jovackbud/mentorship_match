import logging
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from . import database, models
from .matching_service import MatchingService
from .embeddings import load_embedding_model, EMBEDDING_DIM
from .vector_store import faiss_index_manager # Access the global FAISS manager


# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Career-Focused Mentorship Matching API",
    description="A lightweight neural-matching pipeline for mentor-mentee recommendations.",
    version="1.0.0",
)

# --- Pydantic Models for API Input/Output ---

class AvailabilityInput(BaseModel):
    hours_per_month: Optional[int] = Field(None, description="Estimated hours available per month.")
    windows: Optional[Dict[str, List[str]]] = Field(
        None,
        example={
            "Mon": ["09:00-11:00", "14:00-16:00"],
            "Wed": ["10:00-12:00"]
        },
        description="Availability windows by day (e.g., {'Mon': ['HH:MM-HH:MM']})."
    )

class PreferencesInput(BaseModel):
    mentee_backgrounds: Optional[List[str]] = Field(None, description="Desired mentee backgrounds (for mentors).")
    industries: Optional[List[str]] = Field(None, description="Preferred industries.")
    languages: Optional[List[str]] = Field(None, description="Preferred languages for mentorship.")
    mentorship_style: Optional[str] = Field(None, description="Preferred mentorship style (for mentees).")

class MentorCreate(BaseModel):
    bio: str = Field(..., min_length=20, description="Brief biography or expertise summary.")
    expertise: Optional[str] = Field(None, description="Specific areas of expertise (e.g., 'Software Engineering, Product Management').")
    capacity: int = Field(1, ge=1, description="Maximum number of mentees this mentor can take.")
    # current_mentees is managed by the system, not directly set on creation
    availability: Optional[AvailabilityInput] = Field(None, description="Mentor's availability details.")
    preferences: Optional[PreferencesInput] = Field(None, description="Mentor's preferences for mentees.")
    demographics: Optional[Dict[str, Any]] = Field(None, description="Optional demographic information.")

class MentorResponse(BaseModel):
    id: int
    bio: str
    expertise: Optional[str]
    capacity: int
    current_mentees: int
    availability: Optional[Dict[str, Any]] # Output as dict
    preferences: Optional[Dict[str, Any]] # Output as dict
    demographics: Optional[Dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True # Enable ORM mode for Pydantic v2

class MenteeMatchRequest(BaseModel):
    bio: str = Field(..., min_length=20, description="Your brief biography or CV summary.")
    goals: Optional[str] = Field(None, description="Your mentorship goals (e.g., 'Improve leadership skills', 'Land a FAANG job').")
    preferences: Optional[PreferencesInput] = Field(None, description="Your preferences for a mentor.")
    availability: Optional[AvailabilityInput] = Field(None, description="Your availability details for mentorship.")
    mentorship_style: Optional[str] = Field(None, description="Your preferred mentorship style (e.g., 'hands-on', 'guidance-only').")

class MatchedMentor(BaseModel):
    mentor_id: int
    mentor_bio_snippet: str
    re_rank_score: float
    explanations: List[str]
    mentor_details: Dict[str, Any]

class MatchResponse(BaseModel):
    mentee_id: Optional[int] = Field(None, description="If the mentee was stored, their ID.")
    recommendations: List[MatchedMentor] = Field([], description="List of recommended mentors.")
    message: str = "Recommendations generated successfully."

class FeedbackCreate(BaseModel):
    mentee_id: int
    mentor_id: int
    rating: int = Field(..., ge=1, le=5, description="Rating of the mentor-mentee match (1-5).")
    comment: Optional[str] = Field(None, description="Optional comment about the match.")


# --- API Endpoints ---

@app.on_event("startup")
async def startup_event():
    """Initializes database, loads embedding model, and populates FAISS index on startup."""
    logger.info("Application startup event triggered.")
    try:
        database.create_db_and_tables()
        load_embedding_model() # Pre-load the Sentence Transformer model
        # Initialize FAISS index with existing mentors
        # Need to pass db session to MatchingService or fetch it here
        with database.SessionLocal() as db:
            matching_service = MatchingService(db)
            matching_service.initialize_faiss_with_mentors()
        logger.info("Startup sequence completed successfully.")
    except Exception as e:
        logger.critical(f"Critical error during startup: {e}", exc_info=True)
        # Depending on desired behavior, could sys.exit(1) here for unrecoverable errors

@app.post("/mentors/", response_model=MentorResponse, status_code=status.HTTP_201_CREATED)
async def create_mentor(mentor_data: MentorCreate, db: Session = Depends(database.get_db)):
    """
    Registers a new mentor in the system and updates their embedding in the FAISS index.
    """
    try:
        # Create new mentor ORM object
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

        # Generate and store embedding for the new mentor
        text_to_embed = f"{db_mentor.bio or ''} {db_mentor.expertise or ''}"
        mentor_embedding = embeddings.get_embeddings([text_to_embed])

        if mentor_embedding is None or not mentor_embedding:
            logger.error(f"Failed to generate embedding for new mentor {db_mentor.id}. Skipping FAISS update.")
            # Optionally, you might want to delete the mentor or mark them as 'unindexed'
            # For baseline, we just log and continue.
        else:
            db_mentor.embedding = mentor_embedding[0] # Store in DB for persistence
            db.add(db_mentor)
            db.commit()
            db.refresh(db_mentor)
            # Re-add all mentors to FAISS to rebuild the index (simplicity for baseline)
            # In production, use incremental FAISS updates or a separate process.
            matching_service = MatchingService(db)
            matching_service.initialize_faiss_with_mentors() # Re-populate index

        logger.info(f"Mentor {db_mentor.id} created and indexed successfully.")
        return db_mentor
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating mentor: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create mentor.")

@app.post("/match/", response_model=MatchResponse)
async def get_matches(
    mentee_request: MenteeMatchRequest,
    db: Session = Depends(database.get_db)
):
    """
    Recommends top mentors for a given mentee profile.
    Accepts full mentee profile details directly.
    """
    logger.info("Received a new match request.")
    matching_service = MatchingService(db)

    # Convert Pydantic model to a plain dictionary for processing by matching_service
    mentee_profile_data = mentee_request.model_dump(mode='json')

    # Add mentee to DB if you want to track them, for now we process ad-hoc
    # db_mentee = models.Mentee(
    #     bio=mentee_request.bio,
    #     goals=mentee_request.goals,
    #     preferences=mentee_request.preferences.model_dump(mode='json') if mentee_request.preferences else None,
    #     availability=mentee_request.availability.model_dump(mode='json') if mentee_request.availability else None,
    #     mentorship_style=mentee_request.mentorship_style
    # )
    # db.add(db_mentee)
    # db.commit()
    # db.refresh(db_mentee)
    # response_mentee_id = db_mentee.id # Use this if storing mentees

    recommendations = matching_service.get_mentor_recommendations(mentee_profile_data)

    if not recommendations:
        logger.warning("No recommendations found for the mentee after matching process.")
        return MatchResponse(
            recommendations=[],
            message="No suitable mentors found based on your criteria. Please try broadening your preferences."
        )

    return MatchResponse(
        # mentee_id=response_mentee_id, # Uncomment if storing mentees
        recommendations=recommendations,
        message="Top mentor recommendations generated successfully."
    )

@app.post("/feedback/", status_code=status.HTTP_201_CREATED)
async def submit_feedback(feedback: FeedbackCreate, db: Session = Depends(database.get_db)):
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