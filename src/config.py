import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class Settings(BaseSettings):
    # Pydantic Settings will automatically look for these as environment variables
    # or in a .env file (if load_dotenv is called)

    # Database Settings
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "mentorship_db"

    # SQLAlchemy Connection Pooling Settings
    # Refer to https://docs.sqlalchemy.org/en/20/core/engines.html#connection-pooling-options
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30 # seconds
    DB_POOL_RECYCLE: int = 1800 # seconds (30 minutes) - recycle connections older than this

    # Embedding Model Settings
    EMBEDDING_MODEL_NAME: str = 'all-MiniLM-L12-v2'
    EMBEDDING_DIMENSION: int = 384

    # FAISS Index Settings
    FAISS_INDEX_PATH: str = "faiss_mentor_index.bin"
    FAISS_RETRIEVAL_K: int = 20 # Number of candidates to retrieve from FAISS

    # Matching Pipeline Settings
    MATCH_FINAL_LIMIT: int = 3 # Number of final recommendations to return
    MATCH_MIN_AVAILABILITY_OVERLAP_MINUTES: int = 30 # Minimum required availability overlap

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore" # Ignore extra env variables not defined here
    )

@lru_cache() # Cache settings to avoid re-reading on every call
def get_settings():
    """Returns a cached instance of the Settings."""
    return Settings()