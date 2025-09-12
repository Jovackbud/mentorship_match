from sqlalchemy import create_engine
from src.config import get_settings

settings = get_settings()
DATABASE_URL = f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
engine = create_engine(DATABASE_URL)
try:
    with engine.connect() as conn:
        print("Connection successful!")
except Exception as e:
    print(f"Connection failed: {e}")