import faiss
import numpy as np
import logging
import os
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Path to persist the FAISS index
FAISS_INDEX_PATH = "faiss_mentor_index.bin"

class FaissIndex:
    def __init__(self, dimension: int):
        self.dimension = dimension
        self.index = None
        self.mentor_ids = [] # To map FAISS index IDs back to Mentor database IDs
        self._load_index()

    def _load_index(self):
        """Attempts to load the FAISS index from disk, or initializes a new one."""
        if os.path.exists(FAISS_INDEX_PATH):
            try:
                self.index = faiss.read_index(FAISS_INDEX_PATH)
                # Load mentor_ids mapping - this assumes IDs are stored externally or managed consistently
                # For simplicity in baseline, we'll rebuild this on add
                logger.info(f"FAISS index loaded from {FAISS_INDEX_PATH}. Num vectors: {self.index.ntotal}")
                # In a real system, you'd load mentor_ids alongside the index for persistent mapping
                # For this baseline, we'll expect to populate it from DB if starting fresh.
                # If the index is loaded from file, we need a way to rebuild mentor_ids.
                # This could be by having a separate file for mentor_ids or reloading from DB.
                # For now, if loaded, we assume `add` will rebuild `mentor_ids`.
            except Exception as e:
                logger.warning(f"Failed to load FAISS index from {FAISS_INDEX_PATH}: {e}. Initializing new index.")
                self._initialize_new_index()
        else:
            logger.info(f"No FAISS index found at {FAISS_INDEX_PATH}. Initializing new index.")
            self._initialize_new_index()

    def _initialize_new_index(self):
        """Initializes a new flat FAISS index for Inner Product (cosine similarity)."""
        # IndexFlatIP is used for Inner Product, which is equivalent to cosine similarity
        # when vectors are L2-normalized. Sentence-transformers usually outputs normalized embeddings.
        self.index = faiss.IndexFlatIP(self.dimension)
        self.mentor_ids = [] # Reset IDs when initializing new index

    def add_embeddings(self, embeddings: List[List[float]], ids: List[int]):
        """
        Adds new embeddings to the FAISS index.
        Note: For simplicity in baseline, this method rebuilds the ID mapping.
        For incremental updates, a more sophisticated ID management (e.g., `faiss.IndexIDMap`)
        or careful appending would be needed.
        """
        if not embeddings or not ids:
            logger.warning("No embeddings or IDs provided to add to FAISS index.")
            return

        if len(embeddings) != len(ids):
            logger.error("Mismatch between number of embeddings and IDs provided.")
            return

        np_embeddings = np.array(embeddings).astype('float32')
        if np_embeddings.shape[1] != self.dimension:
            logger.error(f"Dimension mismatch: Provided embeddings are {np_embeddings.shape[1]}D, expected {self.dimension}D.")
            return

        # Clear existing index and IDs for simplicity in this baseline (rebuilds entirely)
        # In a production system, for true incremental updates, you would use IndexIDMap or similar.
        self._initialize_new_index() # Clear and re-initialize
        self.index.add(np_embeddings)
        self.mentor_ids.extend(ids) # Assume IDs are added in order

        logger.info(f"Added {len(embeddings)} embeddings to FAISS index. Total: {self.index.ntotal}")
        self._save_index() # Save after adding

    def search(self, query_embedding: List[float], k: int = 20) -> List[Tuple[int, float]]:
        """
        Searches the FAISS index for the top-K nearest neighbors.
        Returns a list of tuples (mentor_id, similarity_score).
        """
        if self.index is None or self.index.ntotal == 0:
            logger.warning("FAISS index is not initialized or empty. Cannot perform search.")
            return []

        if not query_embedding:
            logger.warning("Empty query embedding provided for search.")
            return []

        query_np = np.array([query_embedding]).astype('float32')
        if query_np.shape[1] != self.dimension:
            logger.error(f"Query embedding dimension mismatch: {query_np.shape[1]}D, expected {self.dimension}D.")
            return []

        try:
            # D = distances, I = indices (to the internal FAISS array)
            D, I = self.index.search(query_np, k)

            results = []
            for i, score in zip(I[0], D[0]):
                if i != -1: # -1 indicates a non-found element (should not happen with k <= ntotal)
                    mentor_db_id = self.mentor_ids[i] # Map FAISS internal ID back to DB ID
                    results.append((mentor_db_id, float(score))) # Convert numpy float to Python float
            return results
        except Exception as e:
            logger.error(f"Error during FAISS search: {e}")
            return []

    def _save_index(self):
        """Saves the FAISS index to disk."""
        try:
            faiss.write_index(self.index, FAISS_INDEX_PATH)
            logger.info(f"FAISS index saved to {FAISS_INDEX_PATH}")
        except Exception as e:
            logger.error(f"Failed to save FAISS index to {FAISS_INDEX_PATH}: {e}")

# Initialize FAISS index globally
# This will be initialized with the correct dimension from embeddings module
from .embeddings import EMBEDDING_DIM
faiss_index_manager = FaissIndex(dimension=EMBEDDING_DIM)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # This example requires `embeddings.py` to be functional
    from .embeddings import get_embeddings

    # Mock mentor data
    mock_mentor_ids = [101, 102, 103, 104]
    mock_mentor_texts = [
        "Experienced software engineer with 10 years in Python backend development.",
        "Product manager specializing in AI ethics and responsible AI design.",
        "Career coach helping individuals transition into tech roles.",
        "Data scientist with expertise in machine learning and deep learning."
    ]

    # Get embeddings for mock mentors
    mock_mentor_embeddings = get_embeddings(mock_mentor_texts)
    if mock_mentor_embeddings:
        print(f"Generated {len(mock_mentor_embeddings)} mock mentor embeddings.")
        # Add to FAISS index
        faiss_index_manager.add_embeddings(mock_mentor_embeddings, mock_mentor_ids)

        # Mock mentee query
        mentee_query_text = "I want to become a software developer specializing in backend systems using Python."
        mentee_query_embedding = get_embeddings([mentee_query_text])

        if mentee_query_embedding:
            # Search for top 2 mentors
            top_mentors = faiss_index_manager.search(mentee_query_embedding[0], k=2)
            print(f"\nTop 2 mentor matches for '{mentee_query_text}':")
            for mentor_id, score in top_mentors:
                print(f"  Mentor ID: {mentor_id}, Similarity: {score:.4f}")
        else:
            print("Failed to get mentee query embedding.")
    else:
        print("Failed to get mock mentor embeddings.")