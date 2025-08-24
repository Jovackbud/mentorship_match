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
    REJECTED = "REJECTED" # Mentor rejects, or mentee ends prematurely
    CANCELLED = "CANCELLED" # Mentee cancels a PENDING request
    COMPLETED = "COMPLETED" # Mentorship successfully concluded

class Mentor(Base):
    __tablename__ = "mentors"

    id = Column(Integer, Sequence('mentor_id_seq'), primary_key=True, index=True)
    
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

    mentorship_requests = relationship("MentorshipRequest", back_populates="mentor")

    def __repr__(self):
        return f"<Mentor(id={self.id}, expertise='{self.expertise[:20]}...')>"

class Mentee(Base):
    __tablename__ = "mentees"

    id = Column(Integer, Sequence('mentee_id_seq'), primary_key=True, index=True)

    bio = Column(Text, nullable=False)
    goals = Column(Text)
    preferences = Column(JSONB, nullable=True)
    availability = Column(JSONB, nullable=True)
    mentorship_style = Column(String, nullable=True)
    embedding = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    mentorship_requests_as_mentee = relationship("MentorshipRequest", back_populates="mentee") # Renamed back_populates to avoid conflict

    def __repr__(self):
        return f"<Mentee(id={self.id}, goals='{self.goals[:20]}...')>"

class MentorshipRequest(Base):
    __tablename__ = "mentorship_requests"

    id = Column(Integer, Sequence('mentorship_request_id_seq'), primary_key=True, index=True)
    
    mentee_id = Column(Integer, ForeignKey("mentees.id"), nullable=False)
    mentor_id = Column(Integer, ForeignKey("mentors.id"), nullable=False)
    
    status = Column(String, default=MentorshipStatus.PENDING.value, nullable=False)
    
    request_message = Column(Text, nullable=True)
    
    request_date = Column(DateTime(timezone=True), server_default=func.now())
    acceptance_date = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    completed_date = Column(DateTime(timezone=True), nullable=True) # <--- NEW FIELD

    mentee = relationship("Mentee", back_populates="mentorship_requests_as_mentee") # Adjusted back_populates
    mentor = relationship("Mentor", back_populates="mentorship_requests")

    def __repr__(self):
        return f"<MentorshipRequest(id={self.id}, mentee_id={self.mentee_id}, mentor_id={self.mentor_id}, status='{self.status}')>"

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, Sequence('feedback_id_seq'), primary_key=True, index=True)
    mentee_id = Column(Integer, nullable=False)
    mentor_id = Column(Integer, nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Feedback(id={self.id}, mentee_id={self.mentee_id}, mentor_id={self.mentor_id}, rating={self.rating})>"