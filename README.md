# MentorMatch

A career-focused mentorship matching platform that connects mentees with suitable mentors using AI-powered semantic similarity. Built with FastAPI backend and vanilla JavaScript frontend.

## Overview

MentorMatch facilitates meaningful mentorship connections by matching mentees with mentors based on bios, goals, preferences, and availability. The platform supports user registration, profile creation, and AI-driven recommendations using transformer-based embeddings and FAISS for efficient search.

## Technical Implementation

MentorMatch uses a modular architecture with FastAPI handling backend logic and vanilla JavaScript for frontend interactions. Authentication relies on JWT tokens stored in cookies and headers for security.

### AI Matching Logic

Matching is powered by semantic similarity using SentenceTransformer embeddings:
- User profiles (mentee/mentor bios, goals) are embedded into vectors via a pre-trained transformer model.
- Vectors are L2-normalized and searched in FAISS for efficient cosine similarity approximation.
- Initial retrieval uses embedding similarity, followed by filtering (availability, preferences) and re-ranking (weighted combination of similarity, overlap, and preference matches).

### Data Processing

- **Bios and Goals**: Text data is embedded using SentenceTransformer for semantic understanding.
- **Preferences and Availability**: Structured data (industry, language, time windows) is used for filtering and scoring; e.g., availability overlap is calculated in minutes, preference matches boost scores.
- **User Profiles**: Stored in PostgreSQL; embeddings cached for real-time matching.
- **Feedback Loop**: Post-mentorship feedback refines future recommendations via re-ranking weights.

### Architecture

- **Backend**: FastAPI routes handle auth, matching, and requests; SQLAlchemy manages database interactions.
- **Frontend**: Jinja2 templates render pages; JavaScript handles dynamic interactions and API calls.
- **Deployment**: Supports Docker; runs on standard WSGI servers like Uvicorn.

## Features

- **User Authentication**: JWT-based login with support for both header and cookie methods.
- **User Roles**: Separate flows for mentees and mentors.
- **AI Matching**: Semantic similarity algorithm for mentor recommendations.
- **Dashboard**: Personalized dashboards for mentees and mentors.
- **Request Management**: Mentees can send and track mentorship requests.
- **Feedback System**: Post-mentorship feedback collection.
- **Responsive UI**: Clean, mobile-friendly interface using vanilla JS and Jinja2 templates.
- **Health Check**: Endpoint to monitor FAISS index and embedding model status.

## Tech Stack

- **Backend**: Python, FastAPI~=0.111.0, SQLAlchemy~=2.0.30, PostgreSQL (psycopg2-binary~=2.9.9).
- **Frontend**: Vanilla JavaScript, HTML, CSS, Jinja2.
- **AI/ML**: Sentence-transformers~=2.7.0 for embeddings, FAISS-cpu~=1.8.0 for indexing, scikit-learn~=1.5.0, numpy~=1.26.4.
- **Authentication**: python-jose[cryptography]~=3.3.0, passlib[bcrypt]~=1.7.4.
- **Other**: pydantic-settings~=2.2.1, python-multipart~=0.0.9, filelock~=3.14.0, pandas~=2.2.2.

## Prerequisites

- Python 3.8+
- PostgreSQL database
- Virtual environment tool (e.g., venv)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd mentorship_match
   ```

2. Set up virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables in `.env`:
   ```env
   DATABASE_URL=postgresql://user:password@localhost/dbname
   SECRET_KEY=your-secret-key
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
   EMBEDDING_DIMENSION=384
   ```

5. Set up the database:
   ```bash
   # Ensure PostgreSQL is running and create database
   # Run migrations if applicable
   ```

## Running the Application

1. Activate virtual environment and start the server:
   ```bash
   uvicorn src.main:app --reload
   ```

2. Access the app at `http://localhost:8000`.

## Usage

1. **Registration**: Visit `/register` to create an account.
2. **Profile Setup**: Complete `/get-started` for mentees or `/signup/mentor` for mentors.
3. **Matching**: Mentees view recommendations at `/mentees/{id}/recommendations`.
4. **Requests**: Mentees send requests via `/api/mentees/{id}/requests/pick_mentor/{mentor_id}`.
5. **Dashboard**: Access personalized dashboards at `/dashboard/mentee/{id}` or `/dashboard/mentor/{id}`.

## Project Structure

```
mentorship_match/
├── src/
│   ├── main.py              # FastAPI app entry point
│   ├── routers/             # API route handlers (auth, profile, mentorship, matching, frontend, feedback)
│   ├── models.py            # Database models (User, Mentor, Mentee, MentorshipRequest, Feedback)
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic (e.g., matching)
│   ├── core/                # Core modules (embeddings, vector_store, filtering, re_ranking)
│   ├── config.py            # Settings and configuration
│   ├── database.py          # Database connection and setup
│   └── static/              # Frontend assets (JS, CSS, HTML)
├── requirements.txt
├── .env
└── README.md
```

## API Reference

Key endpoints:
- `POST /register` - User registration
- `POST /token` - User login
- `GET /users/me` - Get current user profile
- `POST /logout` - User logout
- `POST /api/mentees/match-or-create` - Create or update mentee profile and get matches
- `POST /api/mentees/{mentee_id}/match` - Get mentor matches for a mentee
- `GET /api/mentors/` - List mentors
- `POST /api/mentees/{id}/requests/pick_mentor/{mentor_id}` - Send mentorship request
- `GET /api/mentors/{id}/requests` - View mentor requests
- `GET /health` - Health check for FAISS and embedding model

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Make changes and test.
4. Submit a pull request.

## License

This project is licensed under the MIT License.