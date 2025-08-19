from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB # Explicitly for JSONB
from .database import Base

class Mentor(Base):
    __tablename__ = "mentors"

    id = Column(Integer, primary_key=True, index=True)
    bio = Column(Text, nullable=False)
    expertise = Column(Text) # e.g., "Software Engineering, Product Management"
    capacity = Column(Integer, nullable=False, default=1) # Max mentees
    current_mentees = Column(Integer, nullable=False, default=0)
    # JSONB for availability: {'hours_per_month': 10, 'windows': {'Mon': ['09:00-10:00', '14:00-16:00'], 'Wed': ['10:00-12:00']}}
    availability = Column(JSONB, nullable=True)
    # JSONB for preferences: {'mentee_backgrounds': ['early-career', 'startup'], 'industries': ['tech', 'finance'], 'languages': ['Python', 'English']}
    preferences = Column(JSONB, nullable=True)
    demographics = Column(JSONB, nullable=True) # Optional, e.g., {'gender': 'Female', 'ethnicity': 'Asian'}
    embedding = Column(JSONB, nullable=True) # Store the embedding as a list of floats (JSONB for flexibility)
    is_active = Column(Boolean, default=True) # To easily deactivate mentors
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Mentor(id={self.id}, expertise='{self.expertise[:20]}...')>"

class Mentee(Base):
    __tablename__ = "mentees"

    id = Column(Integer, primary_key=True, index=True)
    bio = Column(Text, nullable=False) # e.g., CV summary or aspirations
    goals = Column(Text) # e.g., "Improve leadership skills, land a FAANG job"
    # JSONB for preferences: {'mentorship_style': 'hands-on', 'industries': ['tech'], 'languages': ['English']}
    preferences = Column(JSONB, nullable=True)
    # JSONB for availability: {'hours_per_month': 8, 'windows': {'Tue': ['13:00-15:00'], 'Fri': ['10:00-12:00']}}
    availability = Column(JSONB, nullable=True)
    # Style: e.g., "hands-on", "guidance-only", "brainstorming"
    mentorship_style = Column(String, nullable=True)
    embedding = Column(JSONB, nullable=True) # Store the embedding (if we decide to pre-embed mentees)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Mentee(id={self.id}, goals='{self.goals[:20]}...')>"

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    mentee_id = Column(Integer, nullable=False)
    mentor_id = Column(Integer, nullable=False)
    rating = Column(Integer, nullable=False) # e.g., 1-5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Feedback(id={self.id}, mentee_id={self.mentee_id}, mentor_id={self.mentor_id}, rating={self.rating})>"