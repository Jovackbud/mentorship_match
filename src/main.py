import os
import logging
from fastapi import FastAPI, Depends, HTTPException, status, Query, Request, Response
from starlette.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Dict, Any, Optional, cast
from sqlalchemy.orm import Session, load_only, joinedload
from datetime import datetime, timedelta, timezone

from .config import get_settings
from . import database, models
from . import schemas
from .matching_service import MatchingService
from . import embeddings
from .embeddings import load_embedding_model
from .vector_store import faiss_index_manager
from .security import authenticate_user, create_access_token, get_current_user, get_password_hash, verify_password
from . import dependencies # Import your new authorization dependencies

# --- Configure Logging ---
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Career-Focused Mentorship Matching API",
    description="A lightweight neural-matching pipeline for mentor-mentee recommendations.",
    version="1.0.0",
)

# --- Frontend Setup ---
app.mount("/static", StaticFiles(directory="src/static"), name="static")
templates = Jinja2Templates(directory="src/templates")

# --- API Endpoints ---

@app.on_event("startup")
async def startup_event():
    """Initializes database, loads embedding model, and populates FAISS index on startup."""
    logger.info("Application startup event triggered.")
    try:
        database.create_db_and_tables()
        load_embedding_model() # Pre-load the Sentence Transformer model
        
        with database.SessionLocal() as db:
            matching_service_instance = MatchingService(db) # Renamed instance
            matching_service_instance.initialize_faiss_with_mentors()
        logger.info("Startup sequence completed successfully.")
    except Exception as e:
        logger.critical(f"Critical error during startup: {e}", exc_info=True)
        # Depending on desired behavior, could sys.exit(1) here for unrecoverable errors

# --- Frontend Routes (Additional for Auth) ---
@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """
    Renders the homepage.
    """
    return templates.TemplateResponse("index.html", {"request": request, "title": "Mentorship Matching"})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """
    Renders the user registration page.
    """
    return templates.TemplateResponse("register.html", {"request": request, "title": "Register"})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Renders the user login page.
    """
    return templates.TemplateResponse("login.html", {"request": request, "title": "Login"})

@app.get("/signup/mentor", response_class=HTMLResponse)
async def mentor_signup_page(request: Request):
    """
    Renders the mentor signup page.
    """
    return templates.TemplateResponse("mentor_signup.html", {"request": request, "title": "Become a Mentor"})

@app.get("/signup/mentee", response_class=HTMLResponse)
async def mentee_signup_page(request: Request):
    """
    Renders the mentee signup page.
    """
    return templates.TemplateResponse("mentee_signup.html", {"request": request, "title": "Find a Mentor"})

@app.get("/feedback", response_class=HTMLResponse)
async def feedback_form_page(request: Request):
    """
    Renders the feedback submission form.
    """
    return templates.TemplateResponse("feedback_form.html", {"request": request, "title": "Submit Feedback"})


@app.get("/dashboard/mentor/{mentor_id}", response_class=HTMLResponse)
async def mentor_dashboard_page(
    request: Request,
    mentor_id: int,
    db: Session = Depends(database.get_db),
):
    """
    Renders the mentor dashboard page for a specific mentor.
    This frontend route itself does not enforce ownership, but API calls made from it do.
    """
    mentor = db.query(models.Mentor).filter(models.Mentor.id == mentor_id).first()
    if not mentor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentor not found.")
    
    return templates.TemplateResponse(
        "mentor_dashboard.html", 
        {"request": request, "title": f"Mentor Dashboard - {mentor.name}", "mentor_id": mentor_id}
    )

@app.get("/dashboard/mentee/{mentee_id}", response_class=HTMLResponse)
async def mentee_dashboard_page(
    request: Request,
    mentee_id: int,
    db: Session = Depends(database.get_db),
):
    """
    Renders the mentee dashboard page for a specific mentee.
    This frontend route itself does not enforce ownership, but API calls made from it do.
    """
    mentee = db.query(models.Mentee).filter(models.Mentee.id == mentee_id).first()
    if not mentee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentee not found.")
    
    return templates.TemplateResponse(
        "mentee_dashboard.html", 
        {"request": request, "title": f"Mentee Dashboard - {mentee.name}", "mentee_id": mentee_id}
    )

# --- User Authentication API Endpoints ---
@app.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """
    Registers a new user with a unique username and hashed password.
    """
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"User {db_user.username} registered successfully.")
    return db_user

@app.post("/token")
async def login_for_access_token(
    response: Response, # This is correct
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(database.get_db)
):
    """
    Authenticates a user and sets an HttpOnly access token cookie.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire_time_utc = datetime.now(timezone.utc) + access_token_expires
    
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # This line correctly adds the Set-Cookie header to the 'response' object
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=expire_time_utc,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
    )
    logger.debug(f"Cookie set: key='access_token', value='{access_token[:10]}...', httponly=True, max_age={settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60}, expires={expire_time_utc}, samesite='lax', secure={settings.COOKIE_SECURE}")
    logger.info(f"User {user.username} logged in successfully, HttpOnly cookie set.")
    
    # --- THIS IS THE CRUCIAL CHANGE ---
    # Create a dictionary for the content
    response_content = {"message": "Login successful"}
    
    # Return a JSONResponse, explicitly passing the headers from the 'response' object
    # that `response.set_cookie` modified.
    return JSONResponse(content=response_content, status_code=status.HTTP_200_OK, headers=response.headers)

@app.get("/users/me/", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    """
    Retrieves the current authenticated user's profile.
    Requires a valid JWT token (HttpOnly cookie).
    """
    return current_user

@app.post("/logout", status_code=status.HTTP_200_OK)
async def logout_user(response: Response):
    """
    Logs out the current user by clearing the HttpOnly access token cookie.
    """
    response.delete_cookie(key="access_token")
    logger.info("User logged out, HttpOnly cookie cleared.")
    return {"message": "Logged out successfully"}


# --- Profile Retrieval API Endpoints ---
# These remain public as they only retrieve data, not modify.
# Frontend JS will make calls to the /api/.../requests endpoints for user-specific data
@app.get("/mentors/{mentor_id}", response_model=schemas.MentorResponse)
async def read_mentor_profile(mentor_id: int, db: Session = Depends(database.get_db)):
    """
    Retrieves a full mentor profile by ID. Public endpoint.
    """
    mentor = db.query(models.Mentor).filter(models.Mentor.id == mentor_id).first()
    if not mentor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentor not found")
    return mentor

@app.get("/mentees/{mentee_id}", response_model=schemas.MenteeResponse)
async def read_mentee_profile(mentee_id: int, db: Session = Depends(database.get_db)):
    """
    Retrieves a full mentee profile by ID. Public endpoint.
    """
    mentee = db.query(models.Mentee).filter(models.Mentee.id == mentee_id).first()
    if not mentee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentee not found")
    return mentee


# --- Backend API Endpoints (Now with fine-grained authorization) ---

@app.get("/api/mentors/{mentor_id}/requests", response_model=List[schemas.MentorshipRequestResponse])
async def get_mentor_requests(
    owned_mentor: models.Mentor = Depends(dependencies.get_owned_mentor_profile), # AUTHORIZATION CHECK
    db: Session = Depends(database.get_db)
):
    """
    Retrieves all mentorship requests associated with a specific mentor.
    Requires authentication AND that current_user owns this mentor profile.
    """
    # The owned_mentor dependency already verified ownership and fetched the mentor object.
    # Eagerly load mentee relationship for names
    requests = db.query(models.MentorshipRequest).options(
        load_only(models.MentorshipRequest.id, models.MentorshipRequest.mentee_id, 
                  models.MentorshipRequest.mentor_id, models.MentorshipRequest.status,
                  models.MentorshipRequest.request_message, models.MentorshipRequest.request_date,
                  models.MentorshipRequest.acceptance_date, models.MentorshipRequest.rejection_reason,
                  models.MentorshipRequest.completed_date),
        joinedload(models.MentorshipRequest.mentee)
    ).filter(models.MentorshipRequest.mentor_id == owned_mentor.id).all()

    enriched_requests = []
    for req in requests:
        req_dict = schemas.MentorshipRequestResponse.model_validate(req).model_dump()
        req_dict['mentor_name'] = owned_mentor.name
        if req.mentee: 
            req_dict['mentee_name'] = req.mentee.name
        else: # Fallback in case mentee was deleted with SET NULL on Feedback
            req_dict['mentee_name'] = f"Mentee {req.mentee_id}"
        enriched_requests.append(req_dict)
    return enriched_requests

@app.get("/api/mentees/{mentee_id}/requests", response_model=List[schemas.MentorshipRequestResponse])
async def get_mentee_requests(
    owned_mentee: models.Mentee = Depends(dependencies.get_owned_mentee_profile), # AUTHORIZATION CHECK
    db: Session = Depends(database.get_db)
):
    """
    Retrieves all mentorship requests associated with a specific mentee.
    Requires authentication AND that current_user owns this mentee profile.
    """
    # The owned_mentee dependency already verified ownership and fetched the mentee object.
    # Eagerly load mentor relationship for names
    requests = db.query(models.MentorshipRequest).options(
        load_only(models.MentorshipRequest.id, models.MentorshipRequest.mentee_id, 
                  models.MentorshipRequest.mentor_id, models.MentorshipRequest.status,
                  models.MentorshipRequest.request_message, models.MentorshipRequest.request_date,
                  models.MentorshipRequest.acceptance_date, models.MentorshipRequest.rejection_reason,
                  models.MentorshipRequest.completed_date),
        joinedload(models.MentorshipRequest.mentor)
    ).filter(models.MentorshipRequest.mentee_id == owned_mentee.id).all()
    
    enriched_requests = []
    for req in requests:
        req_dict = schemas.MentorshipRequestResponse.model_validate(req).model_dump()
        req_dict['mentee_name'] = owned_mentee.name
        if req.mentor: 
            req_dict['mentor_name'] = req.mentor.name
        else: # Fallback in case mentor was deleted with SET NULL on Feedback
            req_dict['mentor_name'] = f"Mentor {req.mentor_id}"
        enriched_requests.append(req_dict)
    return enriched_requests


@app.post("/mentors/", response_model=schemas.MentorResponse, status_code=status.HTTP_201_CREATED)
async def create_mentor(
    mentor_data: schemas.MentorCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Registers a new mentor in the system, links it to the current user,
    and adds their embedding to the FAISS index.
    Requires authentication.
    """
    # Check if this user already has a mentor profile (one-to-one constraint)
    existing_mentor = db.query(models.Mentor).filter(models.Mentor.user_id == current_user.id).first()
    if existing_mentor:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already have a mentor profile registered. Use PUT to update it.")

    try:
        db_mentor = models.Mentor(
            user_id=current_user.id, # LINK MENTOR TO CURRENT USER HERE
            name=mentor_data.name, # ADDED name
            bio=mentor_data.bio,
            expertise=mentor_data.expertise,
            capacity=mentor_data.capacity,
            current_mentees=0,
            availability=mentor_data.availability.model_dump(mode='json') if mentor_data.availability else None,
            preferences=mentor_data.preferences.model_dump(mode='json') if mentor_data.preferences else None,
            demographics=mentor_data.demographics
        )
        db.add(db_mentor)
        db.commit()
        db.refresh(db_mentor)

        text_to_embed = f"{db_mentor.bio or ''} {db_mentor.expertise or ''} {db_mentor.name or ''}" # ADDED name to embedding text
        mentor_embedding = embeddings.get_embeddings([text_to_embed])

        if mentor_embedding is None or not mentor_embedding:
            logger.error(f"Failed to generate embedding for new mentor {db_mentor.id}. Skipping FAISS update.")
        else:
            db_mentor.embedding = cast(List[float], mentor_embedding[0])
            db.add(db_mentor)
            db.commit()
            db.refresh(db_mentor)
            
            matching_service_instance = MatchingService(db) # Renamed instance
            matching_service_instance.batch_update_faiss_index([(cast(List[float], db_mentor.embedding), db_mentor.id)])

        logger.info(f"Mentor {db_mentor.id} ({db_mentor.name}) created and indexed successfully for user_id {current_user.id}.")
        return db_mentor
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating mentor: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create mentor.")

@app.put("/mentors/{mentor_id}", response_model=schemas.MentorResponse)
async def update_mentor(
    mentor_data: schemas.MentorUpdate,
    owned_mentor: models.Mentor = Depends(dependencies.get_owned_mentor_profile), # AUTHORIZATION CHECK
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user) # Keep for logging or if needed elsewhere
):
    """
    Updates an existing mentor's profile and re-indexes their embedding in FAISS if text fields change.
    Requires authentication AND that current_user owns this mentor profile.
    """
    db_mentor = owned_mentor # Use the mentor object returned by the dependency

    old_text_to_embed = f"{db_mentor.bio or ''} {db_mentor.expertise or ''} {db_mentor.name or ''}" # ADDED name to old embedding text
    text_fields_changed = False

    update_data = mentor_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if key == 'availability' or key == 'preferences' or key == 'demographics':
            setattr(db_mentor, key, value if value is not None else None)
        elif key in ['bio', 'expertise', 'name']: # ADDED 'name' here for change detection
            if getattr(db_mentor, key) != value:
                text_fields_changed = True
            setattr(db_mentor, key, value)
        else:
            setattr(db_mentor, key, value)

    db.add(db_mentor)
    db.commit()
    db.refresh(db_mentor)

    new_text_to_embed = f"{db_mentor.bio or ''} {db_mentor.expertise or ''} {db_mentor.name or ''}" # ADDED name to new embedding text
    if text_fields_changed or new_text_to_embed != old_text_to_embed:
        new_embedding = embeddings.get_embeddings([new_text_to_embed])
        if new_embedding is None or not new_embedding:
            logger.error(f"Failed to generate embedding for updated mentor {db_mentor.id}. FAISS index not updated for text changes.")
        else:
            db_mentor.embedding = cast(List[float], new_embedding[0])
            db.add(db_mentor)
            db.commit()
            db.refresh(db_mentor)
            matching_service_instance = MatchingService(db) # Renamed instance
            matching_service_instance.batch_update_faiss_index([(cast(List[float], db_mentor.embedding), db_mentor.id)])
            logger.info(f"Mentor {db_mentor.id} ({db_mentor.name}) updated and re-indexed in FAISS successfully for user_id {current_user.id}.")
    else:
        logger.info(f"Mentor {db_mentor.id} ({db_mentor.name}) updated in DB, no text changes, FAISS index not touched for user_id {current_user.id}.")

    return db_mentor

@app.delete("/mentors/{mentor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mentor(
    owned_mentor: models.Mentor = Depends(dependencies.get_owned_mentor_profile), # AUTHORIZATION CHECK
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user) # Keep for logging or if needed elsewhere
):
    """
    Deletes a mentor from the system and removes their embedding from the FAISS index.
    Requires authentication AND that current_user owns this mentor profile.
    """
    db_mentor = owned_mentor # Use the mentor object returned by the dependency

    active_mentees_for_mentor = db.query(models.MentorshipRequest).filter(
        models.MentorshipRequest.mentor_id == db_mentor.id,
        models.MentorshipRequest.status == models.MentorshipStatus.ACCEPTED.value
    ).count()

    if active_mentees_for_mentor > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Mentor has {active_mentees_for_mentor} active mentees. Cannot delete until relationships are ended (by REJECT or COMPLETE).")

    db.delete(db_mentor)
    db.commit()

    faiss_index_manager.remove_embedding(db_mentor.id) # Use the ID from the authorized mentor object
    logger.info(f"Mentor {db_mentor.id} ({db_mentor.name}) deleted from DB and FAISS index by user_id {current_user.id}.")
    return Response(status_code=status.HTTP_204_NO_CONTENT) # Return Response directly for 204

@app.post("/match/", response_model=schemas.MatchResponse)
async def get_matches(
    mentee_profile_data: schemas.MenteeMatchRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Creates or updates the current user's mentee profile and then recommends top mentors.
    Requires authentication.
    """
    logger.info(f"Received match request from user_id: {current_user.id}. Processing mentee profile.")
    matching_service_instance = MatchingService(db) # Renamed instance

    # 1. Find or Create/Update Mentee Profile for the current_user
    db_mentee = db.query(models.Mentee).filter(models.Mentee.user_id == current_user.id).first()
    
    mentee_needs_embedding_update = False
    if db_mentee is None:
        # Create a new mentee profile linked to the current user
        db_mentee = models.Mentee(
            user_id=current_user.id, # Link to current user
            name=mentee_profile_data.name, # ADDED name
            bio=mentee_profile_data.bio,
            goals=mentee_profile_data.goals,
            preferences=mentee_profile_data.preferences.model_dump(mode='json') if mentee_profile_data.preferences else None,
            availability=mentee_profile_data.availability.model_dump(mode='json') if mentee_profile_data.availability else None,
            mentorship_style=mentee_profile_data.mentorship_style,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(db_mentee)
        db.flush()
        mentee_needs_embedding_update = True
        logger.info(f"New mentee profile created for user_id {current_user.id} with mentee_id {db_mentee.id} (Name: {db_mentee.name}).")
    else:
        # Update existing mentee profile
        old_text_to_embed = f"{db_mentee.bio or ''} {db_mentee.goals or ''} {db_mentee.name or ''}" # ADDED name to old embedding text

        # Update fields only if provided in the request (using model_dump(exclude_unset=True) from Pydantic)
        update_fields = mentee_profile_data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            if key in ['availability', 'preferences']:
                setattr(db_mentee, key, value if value is not None else None)
            elif key in ['bio', 'goals', 'mentorship_style', 'name']: # ADDED 'name' here for change detection
                setattr(db_mentee, key, value)
            
        db_mentee.updated_at = datetime.now(timezone.utc)

        # Check if text fields relevant for embedding have changed
        new_text_to_embed = f"{db_mentee.bio or ''} {db_mentee.goals or ''} {db_mentee.name or ''}" # ADDED name to new embedding text
        if new_text_to_embed != old_text_to_embed:
            mentee_needs_embedding_update = True
            logger.info(f"Mentee profile text changed for mentee_id {db_mentee.id}. Embedding will be updated.")

        db.add(db_mentee)
        logger.info(f"Existing mentee profile updated for user_id {current_user.id} (mentee_id {db_mentee.id}, Name: {db_mentee.name}).")

    db.commit()
    db.refresh(db_mentee)
    generated_mentee_id = cast(int, db_mentee.id)

    # 2. Generate and store embedding if needed
    if mentee_needs_embedding_update:
        text_to_embed = f"{db_mentee.bio or ''} {db_mentee.goals or ''} {db_mentee.name or ''}" # ADDED name to embedding text
        mentee_embedding = embeddings.get_embeddings([text_to_embed])

        if mentee_embedding is None or not mentee_embedding:
            logger.error(f"Failed to generate embedding for mentee {db_mentee.id}. Match quality might be affected.")
            db_mentee.embedding = None # Clear old embedding if new one fails or couldn't be generated
        else:
            db_mentee.embedding = cast(List[float], mentee_embedding[0])
            db.add(db_mentee)
            db.commit()
            db.refresh(db_mentee)

    # 3. Perform Matching using the db_mentee's actual profile data
    mentee_profile_for_matching = {
        'id': db_mentee.id,
        'name': db_mentee.name, # ADDED name for matching service
        'bio': db_mentee.bio,
        'goals': db_mentee.goals,
        'preferences': db_mentee.preferences,
        'availability': db_mentee.availability,
        'mentorship_style': db_mentee.mentorship_style
    }
    recommendations = matching_service_instance.get_mentor_recommendations(mentee_profile_for_matching)
        
    matched_mentors_response = [
        schemas.MatchedMentor(**rec) for rec in recommendations
    ]

    return schemas.MatchResponse(
        mentee_id=generated_mentee_id,
        mentee_name=db_mentee.name,
        recommendations=matched_mentors_response,
        message="Top mentor recommendations generated successfully."
    )

@app.post("/mentee/{mentee_id}/pick_mentor/{mentor_id}", response_model=schemas.MentorshipRequestResponse, status_code=status.HTTP_201_CREATED)
async def pick_mentor(
    mentor_id: int,
    request_message: Optional[str] = Query(None, description="Optional message for the mentor."),
    db_mentee: models.Mentee = Depends(dependencies.get_owned_mentee_profile), # AUTHORIZATION CHECK
    db: Session = Depends(database.get_db), # Keep db for specific queries
):
    """
    Allows a mentee to pick a mentor from the recommendations, creating a PENDING mentorship request.
    This also checks the mentee's current active mentorship count.
    Requires authentication AND that current_user owns this mentee profile.
    """
    # The db_mentee dependency already verified ownership and fetched the mentee object.
    # Now we need to ensure the target mentor exists.
    db_mentor = db.query(models.Mentor).filter(models.Mentor.id == mentor_id).first()
    if db_mentor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentor not found.")
    
    # Check mentee's active mentorship limit
    active_mentorships_for_mentee = db.query(models.MentorshipRequest).filter(
        models.MentorshipRequest.mentee_id == db_mentee.id,
        models.MentorshipRequest.status == models.MentorshipStatus.ACCEPTED.value
    ).count()

    if active_mentorships_for_mentee >= settings.MENTEE_MAX_ACTIVE_MENTORS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Mentee has reached maximum limit of {settings.MENTEE_MAX_ACTIVE_MENTORS} active mentorships.")

    # Check if a pending request already exists for this pair
    existing_pending_request = db.query(models.MentorshipRequest).filter(
        models.MentorshipRequest.mentee_id == db_mentee.id,
        models.MentorshipRequest.mentor_id == db_mentor.id,
        models.MentorshipRequest.status == models.MentorshipStatus.PENDING.value
    ).first()
    if existing_pending_request:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A pending request already exists for this mentee and mentor.")

    # Check mentor capacity before creating request (optional, can also be done on accept)
    if db_mentor.current_mentees >= db_mentor.capacity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mentor has reached maximum capacity.")


    db_request = models.MentorshipRequest(
        mentee_id=db_mentee.id, # Use ID from the authorized mentee object
        mentor_id=db_mentor.id, # Use ID from the fetched mentor object
        status=models.MentorshipStatus.PENDING.value,
        request_message=request_message
    )
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    logger.info(f"Mentee {db_mentee.id} ({db_mentee.name}) picked mentor {db_mentor.id} ({db_mentor.name}). Request {db_request.id} created with PENDING status.")

    # Return enriched response
    req_dict = schemas.MentorshipRequestResponse.model_validate(db_request).model_dump()
    req_dict['mentee_name'] = db_mentee.name
    req_dict['mentor_name'] = db_mentor.name
    return req_dict

@app.put("/mentor/{mentor_id}/request/{request_id}/accept", response_model=schemas.MentorshipRequestResponse)
async def accept_mentee_request(
    db_request: models.MentorshipRequest = Depends(dependencies.get_mentor_owned_request), # AUTHORIZATION CHECK
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user) # Keep for logging or if needed elsewhere
):
    """
    Allows a mentor to accept a pending mentorship request from a mentee.
    Increments mentor's current_mentees count.
    Requires authentication AND that current_user owns the mentor profile associated with this request.
    """
    # The db_request dependency already verified ownership of the mentor and linked the request.
    db_mentor = db_request.mentor # Access mentor via relationship on the request object

    if db_request.status != models.MentorshipStatus.PENDING.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Request is not PENDING (current status: {db_request.status}). Only PENDING requests can be ACCEPTED.")

    if db_mentor.current_mentees >= db_mentor.capacity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mentor has reached maximum capacity and cannot accept more mentees.")
    
    # Check mentee's active mentorship limit before accepting
    active_mentorships_for_mentee = db.query(models.MentorshipRequest).filter(
        models.MentorshipRequest.mentee_id == db_request.mentee_id,
        models.MentorshipRequest.status == models.MentorshipStatus.ACCEPTED.value
    ).count()

    if active_mentorships_for_mentee >= settings.MENTEE_MAX_ACTIVE_MENTORS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Mentee has reached maximum limit of {settings.MENTEE_MAX_ACTIVE_MENTORS} active mentorships. Mentor cannot accept.")


    db_request.status = models.MentorshipStatus.ACCEPTED.value
    db_request.acceptance_date = datetime.now(timezone.utc)
    db_mentor.current_mentees += 1

    db.add(db_request)
    db.add(db_mentor)
    db.commit()
    db.refresh(db_request)
    db.refresh(db_mentor)

    logger.info(f"Mentorship request {db_request.id} from mentee {db_request.mentee_id} accepted by mentor {db_mentor.id} ({db_mentor.name}).")
    
    # Return enriched response
    req_dict = schemas.MentorshipRequestResponse.model_validate(db_request).model_dump()
    if db_request.mentee: req_dict['mentee_name'] = db_request.mentee.name
    if db_request.mentor: req_dict['mentor_name'] = db_request.mentor.name
    return req_dict

@app.put("/mentor/{mentor_id}/request/{request_id}/reject", response_model=schemas.MentorshipRequestResponse)
async def reject_mentee_request(
    rejection_reason: Optional[str] = Query(None, description="Optional reason for rejection."),
    db_request: models.MentorshipRequest = Depends(dependencies.get_mentor_owned_request), # AUTHORIZATION CHECK
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user) # Keep for logging or if needed elsewhere
):
    """
    Allows a mentor to reject a mentorship request (either PENDING or ACCEPTED).
    If the request was ACCEPTED, it decrements the current_mentees count.
    Requires authentication AND that current_user owns the mentor profile associated with this request.
    """
    db_mentor = db_request.mentor # Access mentor via relationship on the request object

    if db_request.status in [models.MentorshipStatus.REJECTED.value, models.MentorshipStatus.COMPLETED.value, models.MentorshipStatus.CANCELLED.value]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Request is already {db_request.status}.")

    # If the request was previously accepted, decrement current_mentees
    if db_request.status == models.MentorshipStatus.ACCEPTED.value:
        if db_mentor.current_mentees > 0:
            db_mentor.current_mentees -= 1
        db.add(db_mentor)
        logger.info(f"Mentor {db_mentor.id} ({db_mentor.name}) current_mentees decremented due to rejection of ACCEPTED request {db_request.id}.")

    db_request.status = models.MentorshipStatus.REJECTED.value
    db_request.rejection_reason = rejection_reason
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    db.refresh(db_mentor) # Refresh mentor to get updated count

    logger.info(f"Mentorship request {db_request.id} from mentee {db_request.mentee_id} rejected by mentor {db_mentor.id} ({db_mentor.name}).")
    
    # Return enriched response
    req_dict = schemas.MentorshipRequestResponse.model_validate(db_request).model_dump()
    if db_request.mentee: req_dict['mentee_name'] = db_request.mentee.name
    if db_request.mentor: req_dict['mentor_name'] = db_request.mentor.name
    return req_dict

@app.put("/mentor/{mentor_id}/request/{request_id}/complete", response_model=schemas.MentorshipRequestResponse)
async def complete_mentee_request(
    db_request: models.MentorshipRequest = Depends(dependencies.get_mentor_owned_request), # AUTHORIZATION CHECK
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user) # Keep for logging or if needed elsewhere
):
    """
    Allows a mentor to mark an ACCEPTED mentorship request as COMPLETED.
    Decrements mentor's current_mentees count.
    Requires authentication AND that current_user owns the mentor profile associated with this request.
    """
    db_mentor = db_request.mentor # Access mentor via relationship on the request object

    if db_request.status != models.MentorshipStatus.ACCEPTED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Request is not ACCEPTED (current status: {db_request.status}). Only ACCEPTED requests can be COMPLETED.")

    db_request.status = models.MentorshipStatus.COMPLETED.value
    db_request.completed_date = datetime.now(timezone.utc)
    if db_mentor.current_mentees > 0:
        db_mentor.current_mentees -= 1

    db.add(db_request)
    db.add(db_mentor)
    db.commit()
    db.refresh(db_request)
    db.refresh(db_mentor)

    logger.info(f"Mentorship request {db_request.id} from mentee {db_request.mentee_id} marked as COMPLETED by mentor {db_mentor.id} ({db_mentor.name}).")
    
    # Return enriched response
    req_dict = schemas.MentorshipRequestResponse.model_validate(db_request).model_dump()
    if db_request.mentee: req_dict['mentee_name'] = db_request.mentee.name
    if db_request.mentor: req_dict['mentor_name'] = db_request.mentor.name
    return req_dict

@app.put("/mentee/{mentee_id}/request/{request_id}/cancel", response_model=schemas.MentorshipRequestResponse)
async def cancel_mentee_request(
    db_request: models.MentorshipRequest = Depends(dependencies.get_mentee_owned_request), # AUTHORIZATION CHECK
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user) # Keep for logging or if needed elsewhere
):
    """
    Allows a mentee to cancel a PENDING mentorship request.
    No impact on mentor's current_mentees as it was never accepted.
    Requires authentication AND that current_user owns the mentee profile associated with this request.
    """
    if db_request.status != models.MentorshipStatus.PENDING.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Request is not PENDING (current status: {db_request.status}). Only PENDING requests can be CANCELLED.")

    db_request.status = models.MentorshipStatus.CANCELLED.value
    db.add(db_request)
    db.commit()
    db.refresh(db_request)

    logger.info(f"Mentorship request {db_request.id} from mentee {db_request.mentee_id} cancelled by user_id {current_user.id}.")
    
    # Return enriched response
    req_dict = schemas.MentorshipRequestResponse.model_validate(db_request).model_dump()
    if db_request.mentee: req_dict['mentee_name'] = db_request.mentee.name
    if db_request.mentor: req_dict['mentor_name'] = db_request.mentor.name
    return req_dict


@app.put("/mentee/{mentee_id}/request/{request_id}/conclude", response_model=schemas.MentorshipRequestResponse)
async def conclude_mentorship_as_mentee(
    db_request: models.MentorshipRequest = Depends(dependencies.get_mentee_owned_request), # AUTHORIZATION CHECK
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user) # Keep for logging or if needed elsewhere
):
    """
    Allows a mentee to conclude an ACCEPTED mentorship request.
    This will mark the request as COMPLETED and decrement the mentor's current_mentees count.
    Requires authentication AND that current_user owns the mentee profile associated with this request.
    """
    if not db_request.status == models.MentorshipStatus.ACCEPTED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Request is not ACCEPTED (current status: {db_request.status}). Only ACCEPTED requests can be concluded.")

    db_mentor = db.query(models.Mentor).filter(models.Mentor.id == db_request.mentor_id).first()
    if db_mentor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated mentor not found (internal error).")

    db_request.status = models.MentorshipStatus.COMPLETED.value
    db_request.completed_date = datetime.now(timezone.utc)
    if db_mentor.current_mentees > 0:
        db_mentor.current_mentees -= 1

    db.add(db_request)
    db.add(db_mentor)
    db.commit()
    db.refresh(db_request)
    db.refresh(db_mentor)

    logger.info(f"Mentee {db_request.mentee_id} concluded mentorship request {db_request.id}. Status set to COMPLETED by user_id {current_user.id}.")
    
    # Return enriched response
    req_dict = schemas.MentorshipRequestResponse.model_validate(db_request).model_dump()
    if db_request.mentee: req_dict['mentee_name'] = db_request.mentee.name
    if db_request.mentor: req_dict['mentor_name'] = db_request.mentor.name
    return req_dict


@app.post("/feedback/", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    feedback: schemas.FeedbackCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Submits feedback on a mentor-mentee match.
    Requires authentication AND that current_user is the mentee submitting feedback.
    """
    # Authorization check: Ensure the mentee submitting feedback is the current_user
    db_mentee = db.query(models.Mentee).filter(models.Mentee.id == feedback.mentee_id).first()
    if not db_mentee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentee profile not found for feedback submission.")
    if db_mentee.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to submit feedback for this mentee profile.")

    try:
        db_feedback = models.Feedback(
            mentee_id=feedback.mentee_id,
            mentor_id=feedback.mentor_id,
            rating=feedback.rating,
            comment=feedback.comment
        )
        db.add(db_feedback)
        db.commit()
        db.refresh(db_feedback)
        
        # Fetch names for logging, not critical for response, but good for context
        mentee_name = db_mentee.name if db_mentee else "Unknown Mentee"
        mentor_obj = db.query(models.Mentor).filter(models.Mentor.id == feedback.mentor_id).first()
        mentor_name = mentor_obj.name if mentor_obj else "Unknown Mentor"

        logger.info(f"Feedback submitted for mentee {feedback.mentee_id} ({mentee_name}) and mentor {feedback.mentor_id} ({mentor_name}) by user_id {current_user.id}.")
        return {"message": "Feedback submitted successfully."}
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting feedback by user_id {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not submit feedback.")