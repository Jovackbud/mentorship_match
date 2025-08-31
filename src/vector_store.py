import faiss
import numpy as np
import logging
import os
from typing import List, Tuple, Optional
from filelock import FileLock
from .config import get_settings
from .embeddings import EMBEDDING_DIM
import traceback

logger = logging.getLogger(__name__)

settings = get_settings()
FAISS_INDEX_PATH = settings.FAISS_INDEX_PATH
FAISS_LOCK_PATH = settings.FAISS_LOCK_PATH

class FaissIndex:
    def __init__(self, dimension: int):
        self.dimension = dimension
        self.index: Optional[faiss.IndexIDMap] = None
        self.lock = FileLock(FAISS_LOCK_PATH)
        self._initialize_index()

    def _initialize_index(self):
        """
        Initializes a new FAISS index. If a persistent index file exists,
        it attempts to load it. Otherwise, it creates a new IndexIDMap.
        """
        base_index = faiss.IndexFlatIP(self.dimension)
        self.index = faiss.IndexIDMap(base_index)

        # Use the lock when reading the index to prevent reading a partially written file
        # (though for initial load, less critical than write, it's safer)
        with self.lock: # ADD THIS LINE
            if os.path.exists(FAISS_INDEX_PATH):
                try:
                    self.index = faiss.read_index(FAISS_INDEX_PATH)
                    logger.info(f"FAISS IndexIDMap loaded from {FAISS_INDEX_PATH}. Total vectors: {self.index.ntotal}")
                except Exception as e:
                    logger.warning(f"Failed to load FAISS IndexIDMap from {FAISS_INDEX_PATH}: {e}. Initializing a fresh index.")
                    logger.debug(f"FAISS index load traceback: {traceback.format_exc()}") # ADDED traceback logging
                    new_base_index = faiss.IndexFlatIP(self.dimension)
                    self.index = faiss.IndexIDMap(new_base_index)
            else:
                logger.info(f"No FAISS index found at {FAISS_INDEX_PATH}. Initializing new IndexIDMap.")

    def add_embedding(self, embedding: List[float], mentor_id: int, auto_save: bool = True):
        """
        Adds or updates a single embedding to the FAISS index with its corresponding integer ID.
        IndexIDMap's add_with_ids method inherently handles updating if the ID already exists.
        """
        if not embedding or mentor_id is None:
            logger.warning("Missing data to add embedding to FAISS index.")
            return
        if self.index is None:
            logger.error("FAISS index is not initialized. Cannot add embedding.")
            return

        np_embedding = np.array([embedding]).astype('float32')
        if np_embedding.shape[1] != self.dimension:
            logger.error(f"Dimension mismatch: Provided embedding is {np_embedding.shape[1]}D, expected {self.dimension}D.")
            return

        self.index.add_with_ids(np_embedding, np.array([mentor_id]))
        logger.info(f"Added/Updated embedding for mentor ID: {mentor_id}. Total vectors in index: {self.index.ntotal}")
        if auto_save:
            self._save_index()

    def remove_embedding(self, mentor_id: int, auto_save: bool = True):
        """
        Removes an embedding from the FAISS index using its integer ID.
        """
        if mentor_id is None:
            logger.warning("No mentor ID provided to remove from FAISS index.")
            return
        if self.index is None:
            logger.error("FAISS index is not initialized. Cannot remove embedding.")
            return
        
        initial_ntotal = self.index.ntotal
        self.index.remove_ids(np.array([mentor_id]))
        
        if self.index.ntotal < initial_ntotal:
            logger.info(f"Removed embedding for mentor ID: {mentor_id}. Total vectors in index: {self.index.ntotal}")
            if auto_save:
                self._save_index()
        else:
            logger.warning(f"Mentor ID {mentor_id} not found in FAISS index. Nothing to remove.")

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
            D, I = self.index.search(query_np, k)

            results = []
            for found_id, score in zip(I[0], D[0]):
                if found_id != -1:
                    results.append((int(found_id), float(score))) # Return integer ID directly
            return results
        except Exception as e:
            logger.error(f"Error during FAISS search: {e}")
            return []

    def _save_index(self):
        """Saves the FAISS index to disk. This operation is now protected by a file lock."""
        if self.index is None:
            logger.error("FAISS index is not initialized. Cannot save.")
            return
        
        # ADD THIS BLOCK: Acquire the lock before writing
        try:
            with self.lock:
                faiss.write_index(self.index, FAISS_INDEX_PATH)
        except Exception as e:
            logger.error(f"Failed to save FAISS index to {FAISS_INDEX_PATH}: {e}")

    def save_index(self):
        """
        Public method to explicitly save the FAISS index to disk.
        """
        self._save_index()

# Instantiate FAISS index globally
faiss_index_manager = FaissIndex(dimension=EMBEDDING_DIM)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    from .embeddings import get_embeddings
    
    # Ensure a fresh start for testing purposes
    if os.path.exists(FAISS_INDEX_PATH):
        os.remove(FAISS_INDEX_PATH)
        logger.info(f"Deleted old FAISS index file: {FAISS_INDEX_PATH}")

    faiss_index_manager = FaissIndex(dimension=EMBEDDING_DIM)

    mock_mentor_ids = [1, 2, 3] # Use integer IDs directly
    mock_mentor_texts = [
        "Experienced software engineer with 10 years in Python backend development.",
        "Product manager specializing in AI ethics and responsible AI design.",
        "Career coach helping individuals transition into tech roles."
    ]
    mock_mentor_embeddings = get_embeddings(mock_mentor_texts)

    if mock_mentor_embeddings:
        print(f"Generated {len(mock_mentor_embeddings)} mock mentor embeddings.")
        faiss_index_manager.add_embedding(mock_mentor_embeddings[0], mock_mentor_ids[0], auto_save=False)
        faiss_index_manager.add_embedding(mock_mentor_embeddings[1], mock_mentor_ids[1], auto_save=False)
        faiss_index_manager.add_embedding(mock_mentor_embeddings[2], mock_mentor_ids[2], auto_save=False)
        faiss_index_manager.save_index()

        print("\n--- Testing update of Mentor 1 ---")
        updated_text_1 = "Experienced software engineer, now specializing in AI and Machine Learning."
        updated_embedding_1 = get_embeddings([updated_text_1])
        if updated_embedding_1:
            faiss_index_manager.add_embedding(updated_embedding_1[0], mock_mentor_ids[0])
            print(f"Updated embedding for mentor ID {mock_mentor_ids[0]}. Index total: {faiss_index_manager.index.ntotal}")

        print("\n--- Testing removal of Mentor 2 ---")
        faiss_index_manager.remove_embedding(mock_mentor_ids[1])
        print(f"Removed embedding for mentor ID {mock_mentor_ids[1]}. Index total: {faiss_index_manager.index.ntotal}")
        
        mentee_query_text = "I want to become a software developer specializing in AI systems using Python."
        mentee_query_embedding = get_embeddings([mentee_query_text])

        if mentee_query_embedding:
            top_mentors = faiss_index_manager.search(mentee_query_embedding[0], k=2)
            print(f"\nTop 2 mentor matches for '{mentee_query_text}':")
            for mentor_id, score in top_mentors:
                print(f"  Mentor ID: {mentor_id}, Similarity: {score:.4f}")
        else:
            print("Failed to get mentee query embedding.")
    else:
        print("Failed to get mock mentor embeddings.")