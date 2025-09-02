# src/utils/response_enricher.py
from typing import Dict, Any, List
from ..models import MentorshipRequest
from ..schemas import MentorshipRequestResponse

class ResponseEnricher:
    @staticmethod
    def enrich_requests(requests: List[MentorshipRequest]) -> List[Dict[str, Any]]:
        """Enriches mentorship requests with mentor/mentee names"""
        enriched = []
        for req in requests:
            req_dict = MentorshipRequestResponse.model_validate(req).model_dump()
            req_dict['mentor_name'] = req.mentor.name if req.mentor else f"Mentor {req.mentor_id}"
            req_dict['mentee_name'] = req.mentee.name if req.mentee else f"Mentee {req.mentee_id}"
            enriched.append(req_dict)
        return enriched
    
    @staticmethod
    def enrich_single_request(request: MentorshipRequest) -> Dict[str, Any]:
        """Enriches a single mentorship request"""
        return ResponseEnricher.enrich_requests([request])[0]