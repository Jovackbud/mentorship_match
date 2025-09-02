# src/routers/frontend_router.py
from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Mentor, Mentee
from ..schemas import MentorResponse, MenteeResponse

router = APIRouter(tags=["frontend"])
templates = Jinja2Templates(directory="src/templates")

@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Mentorship Matching"})

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "title": "Register"})

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "title": "Login"})

@router.get("/signup/mentor", response_class=HTMLResponse)
async def mentor_signup_page(request: Request):
    return templates.TemplateResponse("mentor_signup.html", {"request": request, "title": "Become a Mentor"})

@router.get("/signup/mentee", response_class=HTMLResponse)
async def mentee_signup_page(request: Request):
    return templates.TemplateResponse("mentee_signup.html", {"request": request, "title": "Find a Mentor"})

@router.get("/feedback", response_class=HTMLResponse)
async def feedback_form_page(request: Request):
    return templates.TemplateResponse("feedback_form.html", {"request": request, "title": "Submit Feedback"})

@router.get("/dashboard/mentor/{mentor_id}", response_class=HTMLResponse)
async def mentor_dashboard_page(request: Request, mentor_id: int, db: Session = Depends(get_db)):
    mentor = db.query(Mentor).filter(Mentor.id == mentor_id).first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")
    return templates.TemplateResponse("mentor_dashboard.html", {
        "request": request, 
        "title": mentor.name, 
        "mentor_id": mentor_id
    })

@router.get("/dashboard/mentee/{mentee_id}", response_class=HTMLResponse)
async def mentee_dashboard_page(request: Request, mentee_id: int, db: Session = Depends(get_db)):
    mentee = db.query(Mentee).filter(Mentee.id == mentee_id).first()
    if not mentee:
        raise HTTPException(status_code=404, detail="Mentee not found")
    return templates.TemplateResponse("mentee_dashboard.html", {
        "request": request, 
        "title": mentee.name, 
        "mentee_id": mentee_id
    })

# Public profile endpoints (API endpoints, not HTML)
@router.get("/api/mentors/{mentor_id}", response_model=MentorResponse)
async def read_mentor_profile(mentor_id: int, db: Session = Depends(get_db)):
    mentor = db.query(Mentor).filter(Mentor.id == mentor_id).first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")
    return mentor

@router.get("/api/mentees/{mentee_id}", response_model=MenteeResponse)
async def read_mentee_profile(mentee_id: int, db: Session = Depends(get_db)):
    mentee = db.query(Mentee).filter(Mentee.id == mentee_id).first()
    if not mentee:
        raise HTTPException(status_code=404, detail="Mentee not found")
    return mentee