import faiss
import numpy as np
import logging
import os
from typing import List, Tuple, Optional
from .config import get_settings # IMPORT SETTINGS for configuration
from .embeddings import EMBEDDING_DIM # Keep this for dimension (defined in embeddings.py, now also in config)

logger = logging.getLogger(__name__)

settings = get_settings() # GET SETTINGS INSTANCE
FAISS_INDEX_PATH = settings.FAISS_INDEX_PATH # USE SETTINGS for index path

class FaissIndex:
    def __init__(self, dimension: int):
        self.dimension = dimension
        self.index: Optional[faiss.IndexIDMap] = None # Explicitly type hint for clarity
        self._initialize_index()

    def _initialize_index(self):
        """
        Initializes a new FAISS index. If a persistent index file exists,
        it attempts to load it. Otherwise, it creates a new IndexIDMap.
        """
        # A flat index (IndexFlatIP) is used as the base index for Inner Product (cosine similarity)
        base_index = faiss.IndexFlatIP(self.dimension)
        # Wrap the base index with IndexIDMap for explicit ID management
        self.index = faiss.IndexIDMap(base_index)

        if os.path.exists(FAISS_INDEX_PATH):
            try:
                # Attempt to load the IndexIDMap directly from the file
                self.index = faiss.read_index(FAISS_INDEX_PATH)
                logger.info(f"FAISS IndexIDMap loaded from {FAISS_INDEX_PATH}. Total vectors: {self.index.ntotal}")
            except Exception as e:
                logger.warning(f"Failed to load FAISS IndexIDMap from {FAISS_INDEX_PATH}: {e}. Initializing a fresh index.")
                # If loading fails (e.g., corrupted file, old format), re-initialize an empty IndexIDMap
                new_base_index = faiss.IndexFlatIP(self.dimension)
                self.index = faiss.IndexIDMap(new_base_index)
        else:
            logger.info(f"No FAISS index found at {FAISS_INDEX_PATH}. Initializing new IndexIDMap.")
            # If no file exists, the index is already initialized as an empty IndexIDMap above.

    def add_embedding(self, embedding: List[float], id: int):
        """
        Adds or updates a single embedding to the FAISS index with its corresponding ID.
        IndexIDMap's add_with_ids method inherently handles updating if the ID already exists.
        """
        if not embedding or id is None:
            logger.warning("No embedding or ID provided to add to FAISS index.")
            return
        if self.index is None:
            logger.error("FAISS index is not initialized. Cannot add embedding.")
            return

        np_embedding = np.array([embedding]).astype('float32')
        if np_embedding.shape[1] != self.dimension:
            logger.error(f"Dimension mismatch: Provided embedding is {np_embedding.shape[1]}D, expected {self.dimension}D.")
            return

        # IndexIDMap.add_with_ids takes care of adding a new ID or updating an existing one.
        # No explicit check for existence (like `id_mapper.has`) is needed or directly available in this manner.
        # The logging can simply state it's adding/updating.
        self.index.add_with_ids(np_embedding, np.array([id]))
        logger.info(f"Added/Updated embedding for mentor ID: {id}. Total vectors in index: {self.index.ntotal}")
        self._save_index() # Save after each addition/update for persistence

    def remove_embedding(self, id: int):
        """
        Removes an embedding from the FAISS index using its ID.
        """
        if id is None:
            logger.warning("No ID provided to remove from FAISS index.")
            return
        if self.index is None:
            logger.error("FAISS index is not initialized. Cannot remove embedding.")
            return
        
        # Checking if ID exists before attempting removal (IndexIDMap.remove_ids doesn't error if ID not found)
        # One way to check is to try and search for it, or iterate id_map (less efficient for large indices)
        # For this context, faiss.IndexIDMap.remove_ids will just have no effect if the ID isn't there.
        # So, simply calling it and then checking total count is sufficient for our logging.
        initial_ntotal = self.index.ntotal
        self.index.remove_ids(np.array([id]))
        if self.index.ntotal < initial_ntotal:
            logger.info(f"Removed embedding for mentor ID: {id}. Total vectors in index: {self.index.ntotal}")
            self._save_index() # Save after removal for persistence
        else:
            logger.warning(f"Mentor ID {id} not found in FAISS index. Nothing to remove.")


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
            # D = distances, I = indices (these are the original IDs when using IndexIDMap)
            D, I = self.index.search(query_np, k)

            results = []
            for i_id, score in zip(I[0], D[0]):
                if i_id != -1: # -1 indicates a non-found element (should not happen with k <= ntotal)
                    results.append((int(i_id), float(score))) # Convert numpy types to Python types
            return results
        except Exception as e:
            logger.error(f"Error during FAISS search: {e}")
            return []

    def _save_index(self):
        """Saves the FAISS index to disk."""
        if self.index is None:
            logger.error("FAISS index is not initialized. Cannot save.")
            return
        try:
            faiss.write_index(self.index, FAISS_INDEX_PATH)
            # logger.debug(f"FAISS index saved to {FAISS_INDEX_PATH}") # Use debug to avoid excessive logging
        except Exception as e:
            logger.error(f"Failed to save FAISS index to {FAISS_INDEX_PATH}: {e}")

# Instantiate FAISS index globally
faiss_index_manager = FaissIndex(dimension=EMBEDDING_DIM)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    from .embeddings import get_embeddings # Import for testing

    # Ensure a fresh start for testing purposes
    if os.path.exists(FAISS_INDEX_PATH):
        os.remove(FAISS_INDEX_PATH)
        logger.info(f"Deleted old FAISS index file: {FAISS_INDEX_PATH}")

    # Re-instantiate the manager to ensure a fresh IndexIDMap is created
    faiss_index_manager = FaissIndex(dimension=EMBEDDING_DIM)

    # Mock mentor data
    mock_mentor_ids = [101, 102, 103]
    mock_mentor_texts = [
        "Experienced software engineer with 10 years in Python backend development.",
        "Product manager specializing in AI ethics and responsible AI design.",
        "Career coach helping individuals transition into tech roles."
    ]
    mock_mentor_embeddings = get_embeddings(mock_mentor_texts)

    if mock_mentor_embeddings:
        print(f"Generated {len(mock_mentor_embeddings)} mock mentor embeddings.")
        # Add to FAISS index one by one
        faiss_index_manager.add_embedding(mock_mentor_embeddings[0], mock_mentor_ids[0])
        faiss_index_manager.add_embedding(mock_mentor_embeddings[1], mock_mentor_ids[1])
        faiss_index_manager.add_embedding(mock_mentor_embeddings[2], mock_mentor_ids[2])

        # Test updating an embedding (Mentor 101 changes expertise)
        print("\n--- Testing update of Mentor 101 ---")
        updated_text_101 = "Experienced software engineer, now specializing in AI and Machine Learning."
        updated_embedding_101 = get_embeddings([updated_text_101])
        if updated_embedding_101:
            faiss_index_manager.add_embedding(updated_embedding_101[0], mock_mentor_ids[0])
            print(f"Updated embedding for mentor ID {mock_mentor_ids[0]}. Index total: {faiss_index_manager.index.ntotal}")

        # Test removing an embedding (Mentor 102 is no longer available)
        print("\n--- Testing removal of Mentor 102 ---")
        faiss_index_manager.remove_embedding(mock_mentor_ids[1])
        print(f"Removed mentor ID {mock_mentor_ids[1]}. Index total: {faiss_index_manager.index.ntotal}")
        faiss_index_manager.remove_embedding(999) # Test removing non-existent ID

        # Mock mentee query
        mentee_query_text = "I want to become a software developer specializing in AI systems using Python."
        mentee_query_embedding = get_embeddings([mentee_query_text])

        if mentee_query_embedding:
            # Search for top 2 mentors (should prioritize the updated 101)
            top_mentors = faiss_index_manager.search(mentee_query_embedding[0], k=2)
            print(f"\nTop 2 mentor matches for '{mentee_query_text}':")
            for mentor_id, score in top_mentors:
                print(f"  Mentor ID: {mentor_id}, Similarity: {score:.4f}")
        else:
            print("Failed to get mentee query embedding.")
    else:
        print("Failed to get mock mentor embeddings.")