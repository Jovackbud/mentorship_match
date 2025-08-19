import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from . import models, embeddings, vector_store, filtering, re_ranking, post_processing

logger = logging.getLogger(__name__)

class MatchingService:
    def __init__(self, db: Session):
        self.db = db
        # Initialize the FAISS index manager
        # It's a global instance in vector_store.py, so we just reference it.
        self.faiss_manager = vector_store.faiss_index_manager

    def initialize_faiss_with_mentors(self):
        """
        Populates the FAISS index with embeddings of all active mentors from the database.
        This should be called on application startup or when mentors are significantly updated.
        """
        logger.info("Initializing FAISS index with existing mentor embeddings.")
        mentors = self.db.query(models.Mentor).filter(models.Mentor.is_active == True).all()
        if not mentors:
            logger.warning("No active mentors found in the database to initialize FAISS index.")
            return

        mentor_texts = []
        mentor_ids = []
        for mentor in mentors:
            # Prioritize bio for embedding, append expertise/other text if valuable
            text_to_embed = f"{mentor.bio or ''} {mentor.expertise or ''}"
            mentor_texts.append(text_to_embed)
            mentor_ids.append(mentor.id)

        # Get embeddings
        mentor_embeddings_list = embeddings.get_embeddings(mentor_texts)
        if mentor_embeddings_list is None or not mentor_embeddings_list:
            logger.error("Failed to generate embeddings for existing mentors during FAISS initialization. Index might be empty.")
            return

        # Add to FAISS index (this rebuilds the index for baseline simplicity)
        self.faiss_manager.add_embeddings(mentor_embeddings_list, mentor_ids)
        logger.info(f"Successfully added {len(mentor_embeddings_list)} mentor embeddings to FAISS index.")


    def get_mentor_recommendations(
        self,
        mentee_profile_data: Dict[str, Any],
        k_retrieval: int = 20, # Number of candidates from FAISS
        k_final_recommendations: int = 3 # Number of final recommendations
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
            # Fallback to empty list or random mentors (if random logic is implemented)
            # For baseline, we return an empty list or log severe error.
            return [] # In a real system, you might implement random fallback here

        mentee_embedding = mentee_embedding[0] # Take the first (and only) embedding

        # 2. Retrieval (FAISS Search)
        # The FAISS index stores mentor embeddings and returns IDs and scores
        raw_faiss_results: List[Tuple[int, float]] = self.faiss_manager.search(mentee_embedding, k=k_retrieval)

        if not raw_faiss_results:
            logger.warning("FAISS search returned no results. No mentors to filter/re-rank.")
            return []

        # Fetch full mentor profiles from DB for candidates
        candidate_mentor_ids = [res[0] for res in raw_faiss_results]
        mentor_id_to_score = {res[0]: res[1] for res in raw_faiss_results} # Map ID to similarity score

        candidate_mentors_db = self.db.query(models.Mentor).filter(
            models.Mentor.id.in_(candidate_mentor_ids),
            models.Mentor.is_active == True # Ensure only active mentors are considered
        ).all()

        # Convert ORM objects to dictionaries for easier processing in subsequent steps
        # Also attach the FAISS similarity score
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
                '__score': mentor_id_to_score.get(mentor_orm.id, 0.0) # Attach cosine similarity score
            }
            candidate_mentors_dicts.append(mentor_dict)
        
        # Sort by initial similarity score to ensure top K are truly high-similarity before filtering
        # This isn't strictly necessary if FAISS returns sorted, but good for robustness
        candidate_mentors_dicts.sort(key=lambda x: x['__score'], reverse=True)


        # 3. Filtering
        filtered_mentors = filtering.apply_filters(mentee_profile_data, candidate_mentors_dicts)

        # 4. Re-Ranking
        ranked_mentors = re_ranking.re_rank_mentors(filtered_mentors)

        # 5. Post-Processing
        final_recommendations = post_processing.post_process_matches(
            ranked_mentors, mentee_profile_data, limit=k_final_recommendations
        )

        logger.info(f"Matching process completed. Found {len(final_recommendations)} recommendations.")
        return final_recommendations