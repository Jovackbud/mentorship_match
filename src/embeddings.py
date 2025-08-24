from sentence_transformers import SentenceTransformer
import numpy as np
import logging
from .config import get_settings

logger = logging.getLogger(__name__)

_model = None
settings = get_settings()

MODEL_NAME = settings.EMBEDDING_MODEL_NAME
EMBEDDING_DIM = settings.EMBEDDING_DIMENSION

def load_embedding_model():
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
    if not texts:
        return []

    model = load_embedding_model()
    embeddings = None
    try:
        raw_embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        embeddings = raw_embeddings.tolist()

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

    print("\nTesting with empty list:")
    empty_embeddings = get_embeddings([])
    print(f"Empty list result: {empty_embeddings}")

    print("\nTesting with problematic input (should log error and return None):")
    problematic_embeddings = get_embeddings([None, "valid text"])
    print(f"Problematic input result: {problematic_embeddings}")