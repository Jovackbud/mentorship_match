from sentence_transformers import SentenceTransformer
import numpy as np
import logging
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Export the embedding dimension constant
EMBEDDING_DIM = settings.EMBEDDING_DIMENSION

_model = None

def load_embedding_model():
    global _model
    if _model is None:
        try:
            _model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
            logger.info(f"Model {settings.EMBEDDING_MODEL_NAME} loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise RuntimeError(f"Could not load embedding model: {e}")
    return _model

def get_embeddings(texts: list[str]) -> list[list[float]] | None:
    if not texts or not all(isinstance(text, str) for text in texts):
        return None
    
    try:
        model = load_embedding_model()
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        
        if np.isnan(embeddings).any():
            logger.error("Generated embeddings contain NaN values")
            return None
        
        return embeddings.tolist()
    except Exception as e:
        logger.error(f"Error during embedding generation: {e}")
        return None