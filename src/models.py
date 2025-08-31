# src/models.py
from enum import Enum
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

# --- NEW: User Model for Authentication ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, Sequence('user_id_seq'), primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True) # Can be used to disable user accounts
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # This should correctly update or be None if never updated, ensuring consistency with schemas
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True) # ADDED nullable=True here

    # Relationships are implicitly defined by backref on Mentee and explicit below for Mentor
    mentor_profile = relationship("Mentor", back_populates="user", uselist=False) # ADDED explicit relationship for Mentor
    mentee_profile = relationship("Mentee", back_populates="user", uselist=False) # ADDED explicit relationship for Mentee

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class Mentor(Base):
    __tablename__ = "mentors"

    id = Column(Integer, Sequence('mentor_id_seq'), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False) # ADDED this line
    name = Column(String, nullable=False, index=True)

    bio = Column(Text, nullable=False)
    expertise = Column(Text)
    capacity = Column(Integer, nullable=False, default=1)
    current_mentees = Column(Integer, nullable=False, default=0)
    availability = Column(JSONB, nullable=True)
    preferences = Column(JSONB, nullable=True)
    demographics = Column(JSONB, nullable=True)
    embedding = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    user = relationship("User", back_populates="mentor_profile", uselist=False) 
    mentorship_requests = relationship("MentorshipRequest", back_populates="mentor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Mentor(id={self.id}, name='{self.name}', expertise='{self.expertise[:20]}...')>"

class Mentee(Base):
    __tablename__ = "mentees"

    id = Column(Integer, Sequence('mentee_id_seq'), primary_key=True, index=True)

    # This was already added in previous discussion
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False) 
    name = Column(String, nullable=False, index=True) 
    
    bio = Column(Text, nullable=False)
    goals = Column(Text)
    preferences = Column(JSONB, nullable=True)
    availability = Column(JSONB, nullable=True)
    mentorship_style = Column(String, nullable=True)
    embedding = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    user = relationship("User", back_populates="mentee_profile", uselist=False) # UPDATED backref to back_populates
    mentorship_requests_as_mentee = relationship("MentorshipRequest", back_populates="mentee", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Mentee(id={self.id}, user_id={self.user_id}, name='{self.name}', goals='{self.goals[:20]}...')>"

class MentorshipRequest(Base):
    __tablename__ = "mentorship_requests"

    id = Column(Integer, Sequence('mentorship_request_id_seq'), primary_key=True, index=True)
    
    mentee_id = Column(Integer, ForeignKey("mentees.id"), nullable=False)
    mentor_id = Column(Integer, ForeignKey("mentors.id", ondelete="CASCADE"), nullable=False)
    
    status = Column(String, default=MentorshipStatus.PENDING.value, nullable=False)
    
    request_message = Column(Text, nullable=True)
    
    request_date = Column(DateTime(timezone=True), server_default=func.now())
    acceptance_date = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    completed_date = Column(DateTime(timezone=True), nullable=True)

    mentee = relationship("Mentee", back_populates="mentorship_requests_as_mentee")
    mentor = relationship("Mentor", back_populates="mentorship_requests")

    def __repr__(self):
        return f"<MentorshipRequest(id={self.id}, mentee_id={self.mentee_id}, mentor_id={self.mentor_id}, status='{self.status}')>"

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, Sequence('feedback_id_seq'), primary_key=True, index=True)
    mentee_id = Column(Integer, ForeignKey("mentees.id", ondelete="SET NULL"), nullable=True)
    mentor_id = Column(Integer, ForeignKey("mentors.id", ondelete="SET NULL"), nullable=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Optional: Add relationships for easier ORM navigation if needed
    mentee = relationship("Mentee", foreign_keys=[mentee_id], viewonly=True)
    mentor = relationship("Mentor", foreign_keys=[mentor_id], viewonly=True)

    def __repr__(self):
        return f"<Feedback(id={self.id}, mentee_id={self.mentee_id}, mentor_id={self.mentor_id}, rating={self.rating})>"