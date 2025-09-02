# src/matching_service.py
import logging
from typing import List, Dict, Any, Tuple, cast
from sqlalchemy.orm import Session
from .models import Mentor
from .core.embeddings import get_embeddings
from .core import vector_store, filtering, re_ranking, post_processing
from .config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

class MatchingService:
    def __init__(self, db: Session):
        self.db = db
        self.faiss_manager = vector_store.faiss_index_manager

    def batch_update_faiss_index(self, mentor_embeddings_data: List[Tuple[List[float], int]]):
        """
        Adds/updates multiple embeddings to the FAISS index and then saves it once.
        """
        if not mentor_embeddings_data:
            return

        # Add/update all embeddings without immediate saving
        for embedding, mentor_id in mentor_embeddings_data:
            self.faiss_manager.add_embedding(embedding, mentor_id, auto_save=False)
        
        # Save the index once after all operations
        self.faiss_manager.save_index()
        logger.info(f"FAISS index saved after batch update with {len(mentor_embeddings_data)} embeddings.")

    def initialize_faiss_with_mentors(self):
        logger.info("Initializing FAISS index with existing mentor embeddings.")
        all_active_mentors = self.db.query(Mentor).filter(Mentor.is_active == True).all()

        embeddings_to_add = []
        for mentor in all_active_mentors:
            if mentor.embedding:
                embeddings_to_add.append((cast(List[float], mentor.embedding), mentor.id))
            else:
                logger.error(f"Mentor ID: {mentor.id} is missing embedding during FAISS initialization. Skipping.")
        
        self.batch_update_faiss_index(embeddings_to_add)
        logger.info(f"Successfully synchronized {self.faiss_manager.index.ntotal} mentor embeddings with FAISS index.")

    def get_mentor_recommendations(
        self,
        mentee_profile_data: Dict[str, Any],
        k_retrieval: int = settings.FAISS_RETRIEVAL_K,
        k_final_recommendations: int = settings.MATCH_FINAL_LIMIT
    ) -> List[Dict[str, Any]]:
        """
        Executes the full mentor matching pipeline for a given mentee profile.
        """
        logger.info(f"Starting matching process for mentee: {mentee_profile_data.get('name', 'Unknown Mentee')}.")

        # 1. Embedding Mentee Profile
        mentee_text = f"{mentee_profile_data.get('bio', '')} {mentee_profile_data.get('goals', '')} {mentee_profile_data.get('name', '')}" 
        mentee_embedding = get_embeddings([mentee_text])

        if mentee_embedding is None or not mentee_embedding:
            logger.error("Failed to generate embedding for mentee. Returning empty list.")
            return []

        mentee_embedding = mentee_embedding[0]

        # 2. Retrieval (FAISS Search) - returns integer IDs now
        raw_faiss_results: List[Tuple[int, float]] = self.faiss_manager.search(mentee_embedding, k=k_retrieval)

        if not raw_faiss_results:
            logger.warning("FAISS search returned no results. No mentors to filter/re-rank.")
            return []

        # Fetch full mentor profiles from DB for candidates
        candidate_mentor_ids = [res[0] for res in raw_faiss_results]
        mentor_id_to_score = {res[0]: res[1] for res in raw_faiss_results}

        # Query database using integer IDs
        candidate_mentors_db = self.db.query(Mentor).filter(
            Mentor.id.in_(candidate_mentor_ids),
            Mentor.is_active == True
        ).all()

        candidate_mentors_dicts = []
        for mentor_orm in candidate_mentors_db:
            mentor_dict = {
                'id': mentor_orm.id,
                'name': mentor_orm.name,
                'bio': mentor_orm.bio,
                'expertise': mentor_orm.expertise,
                'capacity': mentor_orm.capacity,
                'current_mentees': mentor_orm.current_mentees,
                'availability': mentor_orm.availability,
                'preferences': mentor_orm.preferences,
                'demographics': mentor_orm.demographics,
                '__score': mentor_id_to_score.get(mentor_orm.id, 0.0)
            }
            candidate_mentors_dicts.append(mentor_dict)

        candidate_mentors_dicts.sort(key=lambda x: x['__score'], reverse=True)

        # 3. Filtering
        filtered_mentors = filtering.apply_filters(
            mentee_profile_data,
            candidate_mentors_dicts,
            min_overlap_minutes=settings.MATCH_MIN_AVAILABILITY_OVERLAP_MINUTES
        )

        # 4. Re-Ranking
        ranked_mentors = re_ranking.re_rank_mentors(filtered_mentors)

        # 5. Post-Processing
        final_recommendations = post_processing.post_process_matches(
            ranked_mentors, mentee_profile_data, limit=k_final_recommendations
        )

        logger.info(f"Matching process completed. Found {len(final_recommendations)} recommendations.")
        return final_recommendations