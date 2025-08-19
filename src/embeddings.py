from sentence_transformers import SentenceTransformer
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Global model instance to avoid reloading for every request
_model = None
MODEL_NAME = 'all-MiniLM-L12-v2'
EMBEDDING_DIM = 384 # Dimension of all-MiniLM-L12-v2 embeddings

def load_embedding_model():
    """Loads the SentenceTransformer model if not already loaded."""
    global _model
    if _model is None:
        try:
            logger.info(f"Loading SentenceTransformer model: {MODEL_NAME}")
            _model = SentenceTransformer(MODEL_NAME)
            logger.info("Model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer model {MODEL_NAME}: {e}")
            raise RuntimeError(f"Could not load embedding model: {e}")
    return _model

def get_embeddings(texts: list[str]) -> list[list[float]] | None:
    """
    Encodes a list of texts into embeddings.
    Handles potential errors during encoding and checks output validity.
    Returns a list of lists of floats (embeddings) or None if encoding fails fundamentally.
    """
    if not texts:
        return []

    model = load_embedding_model()
    embeddings = None
    try:
        # Encode with show_progress_bar=False for server environments
        raw_embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        embeddings = raw_embeddings.tolist() # Convert numpy array to list of lists for JSONB storage

        # Validate output: check for NaN or incorrect dimensions
        if not isinstance(embeddings, list) or not all(isinstance(emb, list) for emb in embeddings):
            logger.error(f"Embeddings output is not a list of lists: {type(embeddings)}")
            return None

        if any(np.isnan(emb).any() for emb in raw_embeddings):
            logger.error("Generated embeddings contain NaN values.")
            return None

        if any(len(emb) != EMBEDDING_DIM for emb in embeddings):
            logger.error(f"Generated embeddings have incorrect dimensions. Expected {EMBEDDING_DIM}.")
            return None

    except Exception as e:
        logger.error(f"Error during text embedding: {e}")
        return None

    return embeddings

# Initialize the model on import (or explicitly call load_embedding_model)
# It's good practice to call it explicitly on app startup in main.py
# load_embedding_model()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_texts = [
        "I am a software engineer looking for career growth.",
        "A mentor focused on product management.",
        "Another test sentence."
    ]
    test_embeddings = get_embeddings(test_texts)
    if test_embeddings:
        print(f"Generated {len(test_embeddings)} embeddings, each of dimension {len(test_embeddings[0])}")
        print(f"First embedding snippet: {test_embeddings[0][:5]}...")
    else:
        print("Failed to generate embeddings.")

    # Test error handling (e.g., passing non-string data or empty list)
    print("\nTesting with empty list:")
    empty_embeddings = get_embeddings([])
    print(f"Empty list result: {empty_embeddings}")

    print("\nTesting with problematic input (should log error and return None):")
    problematic_embeddings = get_embeddings([None, "valid text"]) # This would raise an internal error in SentenceTransformers
    print(f"Problematic input result: {problematic_embeddings}")