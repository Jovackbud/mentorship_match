import logging
from typing import List, Dict, Any, Tuple, cast
from sqlalchemy.orm import Session
from . import models, embeddings, vector_store, filtering, re_ranking, post_processing
from .config import get_settings # <--- IMPORT SETTINGS

logger = logging.getLogger(__name__)

settings = get_settings() # <--- GET SETTINGS INSTANCE

class MatchingService:
    def __init__(self, db: Session):
        self.db = db
        self.faiss_manager = vector_store.faiss_index_manager

    def initialize_faiss_with_mentors(self):
        """
        Populates (or re-populates) the FAISS index with embeddings of all active mentors from the database.
        This ensures the IndexIDMap is in sync with the DB on startup or major updates.
        """
        logger.info("Initializing FAISS index with existing mentor embeddings.")
        mentors = self.db.query(models.Mentor).filter(models.Mentor.is_active == True).all()

        if not mentors:
            logger.warning("No active mentors found in the database to initialize FAISS index.")
            return

        for mentor in mentors:
            if mentor.embedding:
                # Use add_embedding which handles both add and update
                self.faiss_manager.add_embedding(cast(List[float], mentor.embedding), mentor.id)
            else:
                # Generate embedding if not present (should ideally be done on mentor creation)
                text_to_embed = f"{mentor.bio or ''} {mentor.expertise or ''}"
                new_embedding = embeddings.get_embeddings([text_to_embed])
                if new_embedding:
                    mentor.embedding = cast(List[float], new_embedding[0]) # Store in DB
                    self.db.add(mentor)
                    self.db.commit()
                    self.db.refresh(mentor)
                    self.faiss_manager.add_embedding(cast(List[float], mentor.embedding), mentor.id)
                    logger.info(f"Generated and added embedding for mentor ID: {mentor.id} during initialization.")
                else:
                    logger.error(f"Failed to generate embedding for mentor ID: {mentor.id} during initialization.")

        logger.info(f"Successfully synchronized {self.faiss_manager.index.ntotal} mentor embeddings with FAISS index.")


    def get_mentor_recommendations(
        self,
        mentee_profile_data: Dict[str, Any],
        k_retrieval: int = settings.FAISS_RETRIEVAL_K, # <--- USE SETTINGS
        k_final_recommendations: int = settings.MATCH_FINAL_LIMIT # <--- USE SETTINGS
    ) -> List[Dict[str, Any]]:
        """
        Executes the full mentor matching pipeline for a given mentee profile.

        Args:
            mentee_profile_data (Dict[str, Any]): Dictionary containing mentee's bio, goals, preferences, etc.
            k_retrieval (int): Number of top candidates to retrieve from FAISS.
            k_final_recommendations (int): Number of final recommendations to return.

        Returns:
            List[Dict[str, Any]]: A list of recommended mentor profiles with explanations.
        """
        logger.info(f"Starting matching process for mentee.")

        # 1. Embedding Mentee Profile
        mentee_text = f"{mentee_profile_data.get('bio', '')} {mentee_profile_data.get('goals', '')}"
        mentee_embedding = embeddings.get_embeddings([mentee_text])

        if mentee_embedding is None or not mentee_embedding:
            logger.error("Failed to generate embedding for mentee. Falling back to random or empty list.")
            return []

        mentee_embedding = mentee_embedding[0]

        # 2. Retrieval (FAISS Search)
        raw_faiss_results: List[Tuple[int, float]] = self.faiss_manager.search(mentee_embedding, k=k_retrieval)

        if not raw_faiss_results:
            logger.warning("FAISS search returned no results. No mentors to filter/re-rank.")
            return []

        # Fetch full mentor profiles from DB for candidates
        candidate_mentor_ids = [res[0] for res in raw_faiss_results]
        mentor_id_to_score = {res[0]: res[1] for res in raw_faiss_results}

        candidate_mentors_db = self.db.query(models.Mentor).filter(
            models.Mentor.id.in_(candidate_mentor_ids),
            models.Mentor.is_active == True
        ).all()

        candidate_mentors_dicts = []
        for mentor_orm in candidate_mentors_db:
            mentor_dict = {
                'id': mentor_orm.id,
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
            min_overlap_minutes=settings.MATCH_MIN_AVAILABILITY_OVERLAP_MINUTES # <--- USE SETTINGS
        )

        # 4. Re-Ranking
        ranked_mentors = re_ranking.re_rank_mentors(filtered_mentors)

        # 5. Post-Processing
        final_recommendations = post_processing.post_process_matches(
            ranked_mentors, mentee_profile_data, limit=k_final_recommendations
        )

        logger.info(f"Matching process completed. Found {len(final_recommendations)} recommendations.")
        return final_recommendations