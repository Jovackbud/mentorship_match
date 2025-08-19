import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import URL

# --- Database Configuration ---
# You would typically load these from environment variables or a config file
DB_USER = os.getenv("POSTGRES_USER", "user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "mentorship_db")

# Construct the database URL
DATABASE_URL = URL.create(
    "postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
)

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)

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
    # Example usage for creating tables
    # In a real application, this would be part of a migration script or init
    create_db_and_tables()