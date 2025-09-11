import faiss
import numpy as np
import logging
import os
from typing import List, Tuple, Optional
from filelock import FileLock
from ..config import get_settings
from .embeddings import EMBEDDING_DIM
import traceback
import time

logger = logging.getLogger(__name__)

settings = get_settings()
FAISS_INDEX_PATH = settings.FAISS_INDEX_PATH
FAISS_LOCK_PATH = settings.FAISS_LOCK_PATH

class FaissIndex:
    def __init__(self, dimension: int):
        self.dimension = dimension
        self.index: Optional[faiss.IndexIDMap] = None
        self.lock = FileLock(FAISS_LOCK_PATH, timeout=10)
        self._initialize_index()

    def _initialize_index(self):
        """
        Initializes a new FAISS index with proper error handling and race condition protection.
        """
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                with self.lock:
                    if os.path.exists(FAISS_INDEX_PATH):
                        # Try to load existing index
                        try:
                            self.index = faiss.read_index(FAISS_INDEX_PATH)
                            
                            # Validate the loaded index
                            if not isinstance(self.index, faiss.IndexIDMap):
                                logger.warning("Loaded index is not IndexIDMap, creating new one")
                                self._create_new_index()
                            elif self.index.d != self.dimension:
                                logger.warning(f"Index dimension mismatch: {self.index.d} vs {self.dimension}, creating new one")
                                self._create_new_index()
                            else:
                                logger.info(f"FAISS IndexIDMap loaded from {FAISS_INDEX_PATH}. Total vectors: {self.index.ntotal}")
                                return
                        except Exception as e:
                            logger.warning(f"Failed to load FAISS index (attempt {attempt + 1}): {e}")
                            logger.debug(f"FAISS index load traceback: {traceback.format_exc()}")
                            self._create_new_index()
                    else:
                        logger.info(f"No FAISS index found at {FAISS_INDEX_PATH}. Creating new IndexIDMap.")
                        self._create_new_index()
                    return
            except Exception as e:
                logger.error(f"Error during FAISS initialization (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.critical("Failed to initialize FAISS index after all retries")
                    raise RuntimeError(f"Could not initialize FAISS index: {e}")

    def _create_new_index(self):
        """Creates a new FAISS index"""
        base_index = faiss.IndexFlatIP(self.dimension)
        self.index = faiss.IndexIDMap(base_index)

    def add_embedding(self, embedding: List[float], mentor_id: int, auto_save: bool = True):
        """
        Adds or updates a single embedding to the FAISS index with its corresponding integer ID.
        """
        if not embedding or mentor_id is None:
            logger.warning("Missing data to add embedding to FAISS index.")
            return
        
        if self.index is None:
            logger.error("FAISS index is not initialized. Cannot add embedding.")
            return

        try:
            np_embedding = np.array([embedding]).astype('float32')
            if np_embedding.shape[1] != self.dimension:
                logger.error(f"Dimension mismatch: Provided embedding is {np_embedding.shape[1]}D, expected {self.dimension}D.")
                return

            # Check if embedding contains valid values
            if np.isnan(np_embedding).any() or np.isinf(np_embedding).any():
                logger.error(f"Invalid embedding values (NaN or Inf) for mentor ID: {mentor_id}")
                return

            self.index.add_with_ids(np_embedding, np.array([mentor_id]))
            logger.info(f"Added/Updated embedding for mentor ID: {mentor_id}. Total vectors in index: {self.index.ntotal}")
            
            if auto_save:
                self._save_index()
        except Exception as e:
            logger.error(f"Error adding embedding for mentor {mentor_id}: {e}")

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
        
        try:
            initial_ntotal = self.index.ntotal
            self.index.remove_ids(np.array([mentor_id]))
            
            if self.index.ntotal < initial_ntotal:
                logger.info(f"Removed embedding for mentor ID: {mentor_id}. Total vectors in index: {self.index.ntotal}")
                if auto_save:
                    self._save_index()
            else:
                logger.warning(f"Mentor ID {mentor_id} not found in FAISS index. Nothing to remove.")
        except Exception as e:
            logger.error(f"Error removing embedding for mentor {mentor_id}: {e}")

    def search(self, query_embedding: List[float], k: int = 20) -> List[Tuple[int, float]]:
        """
        Searches the FAISS index for the top-K nearest neighbors with better error handling.
        """
        if self.index is None or self.index.ntotal == 0:
            logger.warning("FAISS index is not initialized or empty. Cannot perform search.")
            return []

        if not query_embedding:
            logger.warning("Empty query embedding provided for search.")
            return []

        try:
            query_np = np.array([query_embedding]).astype('float32')
            if query_np.shape[1] != self.dimension:
                logger.error(f"Query embedding dimension mismatch: {query_np.shape[1]}D, expected {self.dimension}D.")
                return []

            # Check if query embedding contains valid values
            if np.isnan(query_np).any() or np.isinf(query_np).any():
                logger.error("Query embedding contains invalid values (NaN or Inf)")
                return []

            # Limit k to available vectors
            actual_k = min(k, self.index.ntotal)
            D, I = self.index.search(query_np, actual_k)

            results = []
            for found_id, score in zip(I[0], D[0]):
                if found_id != -1:  # -1 indicates no result found
                    results.append((int(found_id), float(score)))
            
            return results
        except Exception as e:
            logger.error(f"Error during FAISS search: {e}")
            return []

    def _save_index(self):
        """Saves the FAISS index to disk with proper error handling."""
        if self.index is None:
            logger.error("FAISS index is not initialized. Cannot save.")
            return
        
        try:
            with self.lock:
                # Create temporary file first to avoid corruption
                temp_path = f"{FAISS_INDEX_PATH}.tmp"
                faiss.write_index(self.index, temp_path)
                
                # Atomic rename on Unix-like systems
                if os.path.exists(FAISS_INDEX_PATH):
                    os.replace(temp_path, FAISS_INDEX_PATH)
                else:
                    os.rename(temp_path, FAISS_INDEX_PATH)
                
                logger.debug(f"FAISS index saved successfully to {FAISS_INDEX_PATH}")
        except Exception as e:
            logger.error(f"Failed to save FAISS index to {FAISS_INDEX_PATH}: {e}")
            # Clean up temp file if it exists
            temp_path = f"{FAISS_INDEX_PATH}.tmp"
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

    def save_index(self):
        """Public method to explicitly save the FAISS index to disk."""
        self._save_index()

    def get_stats(self) -> dict:
        """Returns statistics about the current index"""
        if self.index is None:
            return {"status": "not_initialized"}
        
        return {
            "status": "initialized",
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "index_path": FAISS_INDEX_PATH,
            "index_exists": os.path.exists(FAISS_INDEX_PATH)
        }

# Instantiate FAISS index globally
faiss_index_manager = FaissIndex(dimension=EMBEDDING_DIM)