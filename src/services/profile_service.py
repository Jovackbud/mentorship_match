# src/services/profile_service.py
from typing import Dict, Any, Optional, cast, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime, timezone

from ..models import Mentor, Mentee
from ..utils.embedding_utils import EmbeddingUtils
from ..utils.validation_utils import ValidationUtils
from ..exceptions import ProfileAlreadyExistsError, EmbeddingError, BusinessLogicError
from ..core.vector_store import faiss_index_manager
import logging

logger = logging.getLogger(__name__)

class ProfileService:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_utils = EmbeddingUtils()
        self.validator = ValidationUtils(db)
    
    def create_mentor(self, user_id: int, data: Dict[str, Any]) -> Mentor:
        """Creates a new mentor profile with embedding"""
        try:
            # Check for existing profile
            existing = self.db.query(Mentor).filter(Mentor.user_id == user_id).first()
            if existing:
                raise ProfileAlreadyExistsError("You already have a mentor profile")
            
            # Validate required fields
            if not data.get('name') or not data.get('bio'):
                raise BusinessLogicError("Name and bio are required fields")
            
            # Create mentor
            mentor_data = self._prepare_profile_data(data)
            mentor = Mentor(user_id=user_id, **mentor_data)
            self.db.add(mentor)
            self.db.flush()  # Get ID for embedding
            
            # Generate and store embedding
            if not self.embedding_utils.update_mentor_embedding(mentor):
                self.db.rollback()
                raise EmbeddingError("Failed to generate mentor embedding")
            
            self.db.commit()
            self.db.refresh(mentor)
            logger.info(f"Mentor {mentor.id} ({mentor.name}) created for user {user_id}")
            return mentor
            
        except (ProfileAlreadyExistsError, EmbeddingError, BusinessLogicError):
            raise
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Database integrity error creating mentor: {e}")
            raise BusinessLogicError("Database constraint violation - mentor may already exist")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating mentor: {e}")
            raise BusinessLogicError("Database error occurred while creating mentor profile")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error creating mentor: {e}")
            raise BusinessLogicError("An unexpected error occurred while creating mentor profile")
    
    def update_mentor(self, mentor: Mentor, data: Dict[str, Any]) -> Mentor:
        """Updates an existing mentor profile with improved error handling"""
        try:
            old_text = self.embedding_utils.generate_mentor_text(mentor)
            
            # Update fields
            for key, value in data.items():
                if hasattr(mentor, key) and value is not None:
                    setattr(mentor, key, self._process_field_value(key, value))

            mentor.updated_at = datetime.now(timezone.utc)
            self.db.add(mentor)
            
            # Update embedding if text changed
            new_text = self.embedding_utils.generate_mentor_text(mentor)
            if new_text != old_text:
                if not self.embedding_utils.update_mentor_embedding(mentor):
                    logger.warning(f"Failed to update embedding for mentor {mentor.id}")
                    # Don't fail the entire update for embedding issues
            
            self.db.commit()
            self.db.refresh(mentor)
            logger.info(f"Mentor {mentor.id} ({mentor.name}) updated")
            return mentor
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating mentor {mentor.id}: {e}")
            raise BusinessLogicError("Database error occurred while updating mentor profile")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error updating mentor {mentor.id}: {e}")
            raise BusinessLogicError("An unexpected error occurred while updating mentor profile")
    
    def delete_mentor(self, mentor: Mentor):
        """Deletes a mentor profile with proper validation"""
        try:
            # Check for active mentorships
            active_count = self.validator.count_active_mentorships_for_mentor(mentor.id)
            if active_count > 0:
                raise BusinessLogicError(f"Cannot delete mentor with {active_count} active mentees")
            
            mentor_id = mentor.id
            self.db.delete(mentor)
            self.db.commit()
            
            # Remove from FAISS (don't fail if this fails)
            try:
                faiss_index_manager.remove_embedding(mentor_id)
                logger.info(f"Mentor {mentor_id} deleted and removed from FAISS")
            except Exception as e:
                logger.warning(f"Failed to remove mentor {mentor_id} from FAISS: {e}")
                
        except BusinessLogicError:
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deleting mentor {mentor.id}: {e}")
            raise BusinessLogicError("Database error occurred while deleting mentor profile")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error deleting mentor {mentor.id}: {e}")
            raise BusinessLogicError("An unexpected error occurred while deleting mentor profile")
    
    def create_or_update_mentee(self, user_id: int, data: Dict[str, Any]) -> Mentee:
        """Creates or updates a mentee profile with better error handling"""
        try:
            mentee = self.db.query(Mentee).filter(Mentee.user_id == user_id).first()
            
            if mentee:
                return self._update_mentee(mentee, data)
            else:
                return self._create_mentee(user_id, data)
                
        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in create_or_update_mentee: {e}")
            raise BusinessLogicError("An unexpected error occurred while processing mentee profile")
    
    def _create_mentee(self, user_id: int, data: Dict[str, Any]) -> Mentee:
        """Creates a new mentee profile"""
        try:
            # Validate required fields
            if not data.get('name') or not data.get('bio'):
                raise BusinessLogicError("Name and bio are required fields")
                
            mentee_data = self._prepare_profile_data(data)
            mentee = Mentee(
                user_id=user_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                **mentee_data
            )
            self.db.add(mentee)
            self.db.flush()
            
            # Generate embedding (don't fail if this fails)
            if not self.embedding_utils.update_mentee_embedding(mentee):
                logger.warning(f"Failed to generate embedding for new mentee {mentee.id}")
            
            self.db.commit()
            self.db.refresh(mentee)
            logger.info(f"Mentee {mentee.id} ({mentee.name}) created for user {user_id}")
            return mentee
            
        except BusinessLogicError:
            raise
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Database integrity error creating mentee: {e}")
            raise BusinessLogicError("Database constraint violation - mentee may already exist")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating mentee: {e}")
            raise BusinessLogicError("Database error occurred while creating mentee profile")
    
    def _update_mentee(self, mentee: Mentee, data: Dict[str, Any]) -> Mentee:
        """Updates an existing mentee profile"""
        try:
            old_text = self.embedding_utils.generate_mentee_text(mentee)
            
            # Update provided fields only
            update_fields = {k: v for k, v in data.items() if v is not None}
            for key, value in update_fields.items():
                if hasattr(mentee, key):
                    setattr(mentee, key, self._process_field_value(key, value))
            
            mentee.updated_at = datetime.now(timezone.utc)
            self.db.add(mentee)
            
            # Update embedding if text changed
            new_text = self.embedding_utils.generate_mentee_text(mentee)
            if new_text != old_text:
                if not self.embedding_utils.update_mentee_embedding(mentee):
                    logger.warning(f"Failed to update embedding for mentee {mentee.id}")
            
            self.db.commit()
            self.db.refresh(mentee)
            logger.info(f"Mentee {mentee.id} ({mentee.name}) updated")
            return mentee
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating mentee {mentee.id}: {e}")
            raise BusinessLogicError("Database error occurred while updating mentee profile")
    
    def _prepare_profile_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepares profile data for database insertion"""
        prepared = {}
        for key, value in data.items():
            prepared[key] = self._process_field_value(key, value)
        return prepared
    
    def _process_field_value(self, key: str, value: Any) -> Any:
        """Processes field values based on their type"""
        if key in ['availability', 'preferences'] and hasattr(value, 'model_dump'):
            return value.model_dump(mode='json') if value else None
        return value