from enum import Enum # For Mentorship Status
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey, Sequence
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .database import Base

# Enum for Mentorship Request Status
class MentorshipStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED" # If mentee cancels request before mentor acts

class Mentor(Base):
    __tablename__ = "mentors"

    # Use auto-incrementing Integer as primary key directly
    id = Column(Integer, Sequence('mentor_id_seq'), primary_key=True, index=True) # Explicit Sequence for clarity
    
    bio = Column(Text, nullable=False)
    expertise = Column(Text)
    capacity = Column(Integer, nullable=False, default=1) # Max mentees
    current_mentees = Column(Integer, nullable=False, default=0) # Track current active mentees
    availability = Column(JSONB, nullable=True)
    preferences = Column(JSONB, nullable=True)
    demographics = Column(JSONB, nullable=True)
    embedding = Column(JSONB, nullable=True) # Store the embedding as a list of floats (JSONB for flexibility)
    is_active = Column(Boolean, default=True) # To easily deactivate mentors
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Define relationship to MentorshipRequest
    mentorship_requests = relationship("MentorshipRequest", back_populates="mentor")

    def __repr__(self):
        return f"<Mentor(id={self.id}, expertise='{self.expertise[:20]}...')>"

class Mentee(Base):
    __tablename__ = "mentees"

    # Use auto-incrementing Integer as primary key directly
    id = Column(Integer, Sequence('mentee_id_seq'), primary_key=True, index=True)

    bio = Column(Text, nullable=False) # e.g., CV summary or aspirations
    goals = Column(Text) # e.g., "Improve leadership skills, land a FAANG job"
    preferences = Column(JSONB, nullable=True)
    availability = Column(JSONB, nullable=True)
    mentorship_style = Column(String, nullable=True)
    embedding = Column(JSONB, nullable=True) # Store the embedding (if we decide to pre-embed mentees)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Define relationship to MentorshipRequest
    mentorship_requests = relationship("MentorshipRequest", back_populates="mentee") 

    def __repr__(self):
        return f"<Mentee(id={self.id}, goals='{self.goals[:20]}...')>"

class MentorshipRequest(Base):
    __tablename__ = "mentorship_requests"

    id = Column(Integer, Sequence('mentorship_request_id_seq'), primary_key=True, index=True)
    
    mentee_id = Column(Integer, ForeignKey("mentees.id"), nullable=False)
    mentor_id = Column(Integer, ForeignKey("mentors.id"), nullable=False)
    
    status = Column(String, default=MentorshipStatus.PENDING.value, nullable=False)
    
    request_message = Column(Text, nullable=True) # Optional message from mentee
    
    request_date = Column(DateTime(timezone=True), server_default=func.now())
    acceptance_date = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True) # Reason if rejected

    # Relationships to Mentor and Mentee
    mentee = relationship("Mentee", back_populates="mentorship_requests") # Adjusted here
    mentor = relationship("Mentor", back_populates="mentorship_requests")

    def __repr__(self):
        return f"<MentorshipRequest(id={self.id}, mentee_id={self.mentee_id}, mentor_id={self.mentor_id}, status='{self.status}')>"

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, Sequence('feedback_id_seq'), primary_key=True, index=True)
    mentee_id = Column(Integer, nullable=False)
    mentor_id = Column(Integer, nullable=False)
    rating = Column(Integer, nullable=False) # e.g., 1-5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Feedback(id={self.id}, mentee_id={self.mentee_id}, mentor_id={self.mentor_id}, rating={self.rating})>"