import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from .models import MentorshipStatus

# --- NEW: Authentication Schemas ---
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserLogin(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    # ADDED: Fields for associated profile IDs
    mentor_profile_id: Optional[int] = None
    mentee_profile_id: Optional[int] = None

    model_config = {
        "from_attributes": True,
        "arbitrary_types_allowed": True
    }

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# --- Input Models (Existing) ---

class AvailabilityInput(BaseModel):
    hours_per_month: Optional[int] = Field(None, description="Estimated hours available per month.")
    windows: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="Availability windows by day (e.g., {'Mon': ['HH:MM-HH:MM']})."
    )

class PreferencesInput(BaseModel):
    mentee_backgrounds: Optional[List[str]] = Field(None, description="Desired mentee backgrounds (for mentors).")
    industries: Optional[List[str]] = Field(None, description="Preferred industries.")
    languages: Optional[List[str]] = Field(None, description="Preferred languages for mentorship.")
    mentorship_style: Optional[str] = Field(None, description="Preferred mentorship style (for mentees).")

class MentorCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="The mentor's full name.") # ADDED name
    bio: str = Field(..., min_length=20, description="Brief biography or expertise summary.")
    expertise: Optional[str] = Field(None, description="Specific areas of expertise (e.g., 'Software Engineering, Product Management').")
    capacity: int = Field(1, ge=1, description="Maximum number of mentees this mentor can take.")
    availability: Optional[AvailabilityInput] = Field(None, description="Mentor's availability details.")
    preferences: Optional[PreferencesInput] = Field(None, description="Mentor's preferences for mentees.")
    demographics: Optional[Dict[str, Any]] = Field(None, description="Optional demographic information.")

class MentorUpdate(MentorCreate):
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="The mentor's full name.") # ADDED name
    bio: Optional[str] = Field(None, min_length=20, description="Brief biography or expertise summary.")
    capacity: Optional[int] = Field(None, ge=1, description="Maximum number of mentees this mentor can take.")
    expertise: Optional[str] = None
    availability: Optional[AvailabilityInput] = None
    preferences: Optional[PreferencesInput] = None
    demographics: Optional[Dict[str, Any]] = None


class MenteeMatchRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Your full name.") # ADDED name
    bio: str = Field(..., min_length=20, description="Your brief biography or CV summary.")
    goals: Optional[str] = Field(None, description="Your mentorship goals (e.g., 'Improve leadership skills', 'Land a FAANG job').")
    preferences: Optional[PreferencesInput] = Field(None, description="Your preferences for a mentor.")
    availability: Optional[AvailabilityInput] = Field(None, description="Your availability details for mentorship.")
    mentorship_style: Optional[str] = Field(None, description="Your preferred mentorship style (e.g., 'hands-on', 'guidance-only').")
    request_message: Optional[str] = Field(None, description="Optional message to be sent with mentorship requests (will be used for pick_mentor).")

class MentorshipStatusUpdate(BaseModel):
    status: MentorshipStatus
    rejection_reason: Optional[str] = Field(None, description="Only relevant for REJECTED status.")

class FeedbackCreate(BaseModel):
    mentee_id: int
    mentor_id: int
    rating: int = Field(..., ge=1, le=5, description="Rating of the mentor-mentee match (1-5).")
    comment: Optional[str] = Field(None, description="Optional comment about the match.")


# --- Output Models (Existing + MenteeResponse) ---

class MentorResponse(BaseModel):
    id: int
    user_id: int
    name: str # ADDED name
    bio: str
    expertise: Optional[str]
    capacity: int
    current_mentees: int
    availability: Optional[Dict[str, Any]]
    preferences: Optional[Dict[str, Any]]
    demographics: Optional[Dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {
        "from_attributes": True,
        "arbitrary_types_allowed": True
    }

class MenteeResponse(BaseModel):
    id: int
    user_id: int
    name: str # ADDED name
    bio: str
    goals: Optional[str]
    preferences: Optional[Dict[str, Any]]
    availability: Optional[Dict[str, Any]]
    mentorship_style: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {
        "from_attributes": True,
        "arbitrary_types_allowed": True
    }

class MatchedMentor(BaseModel):
    mentor_id: int
    mentor_name: str # ADDED name
    mentor_bio_snippet: str
    re_rank_score: float
    explanations: List[str]
    mentor_details: Dict[str, Any]

class MatchResponse(BaseModel):
    mentee_id: int = Field(..., description="The ID of the mentee whose match was requested.")
    mentee_name: str = Field(..., description="The name of the mentee whose match was requested.") # ADDED name
    recommendations: List[MatchedMentor] = Field([], description="List of recommended mentors.")
    message: str = "Recommendations generated successfully."

class MentorshipRequestResponse(BaseModel):
    id: int
    mentee_id: int
    mentee_name: Optional[str] = None # ADDED name (Optional as it's populated dynamically from relationships)
    mentor_id: int
    mentor_name: Optional[str] = None # ADDED name (Optional as it's populated dynamically from relationships)
    status: MentorshipStatus
    request_message: Optional[str]
    request_date: datetime
    acceptance_date: Optional[datetime]
    rejection_reason: Optional[str]
    completed_date: Optional[datetime]

    model_config = {
        "from_attributes": True,
        "arbitrary_types_allowed": True
    }