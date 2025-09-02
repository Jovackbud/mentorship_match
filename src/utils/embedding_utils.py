# src/utils/embedding_utils.py
from typing import List, cast
from ..models import Mentor, Mentee
from ..core.embeddings import get_embeddings
from ..vector_store import faiss_index_manager
import logging

logger = logging.getLogger(__name__)

class EmbeddingUtils:
    @staticmethod
    def generate_mentor_text(mentor: Mentor) -> str:
        """Generates embedding text for mentor"""
        return f"{mentor.bio or ''} {mentor.expertise or ''} {mentor.name or ''}"
    
    @staticmethod
    def generate_mentee_text(mentee: Mentee) -> str:
        """Generates embedding text for mentee"""
        return f"{mentee.bio or ''} {mentee.goals or ''} {mentee.name or ''}"
    
    @classmethod
    def update_mentor_embedding(cls, mentor: Mentor) -> bool:
        """Updates mentor embedding and FAISS index"""
        text = cls.generate_mentor_text(mentor)
        embeddings = get_embeddings([text])
        
        if not embeddings:
            logger.error(f"Failed to generate embedding for mentor {mentor.id}")
            return False
        
        mentor.embedding = cast(List[float], embeddings[0])
        faiss_index_manager.add_embedding(mentor.embedding, mentor.id)
        return True
    
    @classmethod
    def update_mentee_embedding(cls, mentee: Mentee) -> bool:
        """Updates mentee embedding"""
        text = cls.generate_mentee_text(mentee)
        embeddings = get_embeddings([text])
        
        if not embeddings:
            logger.error(f"Failed to generate embedding for mentee {mentee.id}")
            return False
        
        mentee.embedding = cast(List[float], embeddings[0])
        return True