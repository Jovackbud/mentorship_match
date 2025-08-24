import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import URL
from .config import get_settings

# --- Database Configuration ---
settings = get_settings()

# Construct the database URL
DATABASE_URL = URL.create(
    "postgresql+psycopg2",
    username=settings.POSTGRES_USER,
    password=settings.POSTGRES_PASSWORD,
    host=settings.POSTGRES_HOST,
    port=settings.POSTGRES_PORT,
    database=settings.POSTGRES_DB,
)

# Create the SQLAlchemy engine with connection pooling settings
engine = create_engine(
    DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    # echo=True
)

# Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()

# Dependency to get a DB session
def get_db():
    """Provides a database session for a request and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper function to create all tables
def create_db_and_tables():
    """Creates all defined database tables."""
    Base.metadata.create_all(bind=engine)
    print("Database tables created or already exist.")

if __name__ == "__main__":
    create_db_and_tables()