# src/routers/__init__.py
from . import auth_router
from . import profile_router
from . import mentorship_router
from . import frontend_router
from . import matching_router

__all__ = [
    "auth_router",
    "profile_router", 
    "mentorship_router",
    "frontend_router",
    "matching_router"
]