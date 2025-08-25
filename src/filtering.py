import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Helper function to parse time strings (e.g., "09:00-11:00") into start and end time objects
def parse_time_range(time_str: str) -> Optional[Tuple[time, time]]:
    """Parses a 'HH:MM-HH:MM' string into (start_time, end_time) time objects."""
    try:
        start_str, end_str = time_str.split('-')
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
        # Handle cases where end time is on the next day (e.g., 23:00-01:00), though current implementation might simplify this to same-day only for overlap calc
        # For simple overlap, this is often treated as up to midnight. If actual cross-day is needed, date context is required.
        return start_time, end_time
    except ValueError as e:
        logger.warning(f"Failed to parse time range '{time_str}': {e}")
        return None

def calculate_time_overlap_minutes(
    mentor_windows: Dict[str, List[str]], mentee_windows: Dict[str, List[str]]
) -> int:
    """
    Calculates the total overlapping minutes between mentor and mentee availability windows.
    Windows format: {'Mon': ['09:00-11:00', '14:00-16:00'], 'Wed': ['10:00-12:00']}
    """
    total_overlap_minutes = 0

    # Define days of the week in order for consistent iteration
    days_of_week = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    for day in days_of_week:
        mentor_day_ranges = [parse_time_range(ts) for ts in mentor_windows.get(day, [])]
        mentee_day_ranges = [parse_time_range(ts) for ts in mentee_windows.get(day, [])]

        # Filter out any unparseable ranges
        mentor_day_ranges = [r for r in mentor_day_ranges if r is not None]
        mentee_day_ranges = [r for r in mentee_day_ranges if r is not None]

        # Convert time objects to minutes from midnight for easier comparison
        def time_to_minutes(t: time) -> int:
            return t.hour * 60 + t.minute

        for m_start_t, m_end_t in mentor_day_ranges:
            m_start_min = time_to_minutes(m_start_t)
            m_end_min = time_to_minutes(m_end_t)

            for e_start_t, e_end_t in mentee_day_ranges:
                e_start_min = time_to_minutes(e_start_t)
                e_end_min = time_to_minutes(e_end_t)

                # Calculate overlap for current pair of ranges
                overlap_start = max(m_start_min, e_start_min)
                overlap_end = min(m_end_min, e_end_min)

                if overlap_end > overlap_start:
                    total_overlap_minutes += (overlap_end - overlap_start)

    return total_overlap_minutes

def apply_filters(mentee_profile: Dict[str, Any], candidate_mentors: List[Dict[str, Any]],
                  min_overlap_minutes: int = 30) -> List[Dict[str, Any]]:
    """
    Applies rule-based filters to a list of candidate mentors.

    Args:
        mentee_profile (Dict[str, Any]): The mentee's profile data.
        candidate_mentors (List[Dict[str, Any]]): List of mentor profiles (dictionaries).
        min_overlap_minutes (int): Minimum required availability overlap in minutes.

    Returns:
        List[Dict[str, Any]]: Filtered list of mentor profiles.
    """
    filtered_mentors = []

    # Safely get mentee preferences and availability, ensuring they are dicts or empty dicts
    # The `or {}` idiom ensures that if .get() returns None, it defaults to an empty dictionary.
    mentee_availability = mentee_profile.get('availability') or {}
    mentee_preferences = mentee_profile.get('preferences') or {}

    mentee_target_industries = [ind.lower() for ind in mentee_preferences.get('industries', [])]
    mentee_target_languages = [lang.lower() for lang in mentee_preferences.get('languages', [])]

    for mentor in candidate_mentors:
        mentor_id = mentor.get('id', 'N/A') # For logging

        # 1. Capacity Check
        if mentor.get('current_mentees', 0) >= mentor.get('capacity', 1):
            logger.debug(f"Mentor {mentor_id} filtered out: Exceeded capacity.")
            continue

        # 2. Availability Overlap Check
        mentor_availability = mentor.get('availability') or {} # Ensure it's a dict
        
        # Only check if both mentee and mentor have 'windows' specified within their availability
        mentor_windows = mentor_availability.get('windows') or {}
        mentee_windows = mentee_availability.get('windows') or {}

        if mentor_windows and mentee_windows: # Only check if both have availability windows specified
            overlap_minutes = calculate_time_overlap_minutes(mentor_windows, mentee_windows)
            if overlap_minutes < min_overlap_minutes:
                logger.debug(f"Mentor {mentor_id} filtered out: Insufficient availability overlap ({overlap_minutes} min).")
                continue
            # Store overlap for re-ranking
            mentor['__overlap_minutes'] = overlap_minutes
        else:
            # If no availability windows specified by mentor or mentee, consider it a match by default
            # or apply a stricter rule (e.g., if one has it, other must also)
            logger.debug(f"Mentor {mentor_id}: Availability check skipped (missing data).")
            mentor['__overlap_minutes'] = 0 # Default if not specified

        # 3. Preferences Match (Industry/Language)
        # Ensure mentor preferences is a dict
        mentor_preferences = mentor.get('preferences') or {}
        mentor_industries = [ind.lower() for ind in mentor_preferences.get('industries', [])]
        mentor_languages = [lang.lower() for lang in mentor_preferences.get('languages', [])]

        industry_match = False
        if mentee_target_industries: # If mentee specified industries
            if not mentor_industries: # And mentor didn't specify, assume no match or broad
                industry_match = False
            else:
                if any(ind in mentor_industries for ind in mentee_target_industries):
                    industry_match = True
        else: # If mentee didn't specify, consider it a match
            industry_match = True

        language_match = False
        if mentee_target_languages: # If mentee specified languages
            if not mentor_languages: # And mentor didn't specify, assume no match or broad
                language_match = False
            else:
                if any(lang in mentor_languages for lang in mentee_target_languages):
                    language_match = True
        else: # If mentee didn't specify, consider it a match
            language_match = True

        if not (industry_match and language_match):
            logger.debug(f"Mentor {mentor_id} filtered out: Preference mismatch (Industry: {industry_match}, Language: {language_match}).")
            continue

        # Store preference match info for re-ranking
        mentor['__industry_match'] = industry_match
        mentor['__language_match'] = language_match
        # Simple count of preference matches (can be extended)
        mentor['__preference_match_count'] = int(industry_match) + int(language_match)

        filtered_mentors.append(mentor)

    logger.info(f"Filtered {len(candidate_mentors)} candidates down to {len(filtered_mentors)}.")
    return filtered_mentors

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    # Example Mentor and Mentee Profiles
    mentor1 = {
        'id': 1, 'bio': 'SE, Python', 'capacity': 2, 'current_mentees': 0,
        'availability': {'hours_per_month': 10, 'windows': {'Mon': ['09:00-11:00'], 'Wed': ['10:00-12:00']}},
        'preferences': {'industries': ['Tech'], 'languages': ['Python', 'English']}
    }
    mentor2 = {
        'id': 2, 'bio': 'PM, AI', 'capacity': 1, 'current_mentees': 1, # Exceeded capacity
        'availability': {'hours_per_month': 5, 'windows': {'Tue': ['14:00-16:00']}},
        'preferences': {'industries': ['AI'], 'languages': ['English']}
    }
    mentor3 = { # This mentor will have preferences: None in some tests, simulating the issue
        'id': 3, 'bio': 'Data Scientist', 'capacity': 3, 'current_mentees': 1,
        'availability': {'hours_per_month': 8, 'windows': {'Mon': ['10:00-11:00'], 'Thu': ['15:00-17:00']}}, # Partial overlap with mentee
        'preferences': None # <--- Test case for the bug
    }
    mentor4 = {
        'id': 4, 'bio': 'HR, recruiting', 'capacity': 2, 'current_mentees': 0,
        'availability': {'hours_per_month': 10, 'windows': {'Mon': ['14:00-16:00'], 'Wed': ['10:00-12:00']}},
        'preferences': {'industries': ['HR'], 'languages': ['English']} # No industry match
    }
    mentor5 = {
        'id': 5, 'bio': 'SE, Java', 'capacity': 2, 'current_mentees': 0,
        'availability': {'hours_per_month': 10, 'windows': {'Mon': ['09:00-11:00'], 'Wed': ['10:00-12:00']}},
        'preferences': {'industries': ['Tech'], 'languages': ['Java', 'English']}
    }


    mentee_profile = {
        'id': 101, 'bio': 'Aspiring SW Eng',
        'availability': {'hours_per_month': 6, 'windows': {'Mon': ['10:30-12:30'], 'Fri': ['09:00-10:00']}},
        'preferences': {'industries': ['Tech'], 'languages': ['English']}
    }

    mentee_profile_no_prefs = { # Test case for mentee with no preferences
        'id': 102, 'bio': 'Aspiring SW Eng with no prefs',
        'availability': {'hours_per_month': 6, 'windows': {'Mon': ['10:30-12:30'], 'Fri': ['09:00-10:00']}},
        'preferences': None
    }


    candidates = [mentor1, mentor2, mentor3, mentor4, mentor5]

    print("\n--- Testing Filters ---")
    filtered_mentors = apply_filters(mentee_profile, candidates, min_overlap_minutes=30)

    print("\nFiltered Mentors (after all filters):")
    for m in filtered_mentors:
        print(f"  Mentor ID: {m['id']}, Current Mentees: {m['current_mentees']}/{m['capacity']}, Overlap (min): {m.get('__overlap_minutes')}, IndMatch: {m.get('__industry_match')}, LangMatch: {m.get('__language_match')}")

    assert len(filtered_mentors) == 3, f"Expected 3 filtered mentors, got {len(filtered_mentors)}"
    assert mentor1 in filtered_mentors
    assert mentor3 in filtered_mentors # Mentor 3 should now pass preference check as mentee has preferences and mentor has None
    assert mentor5 in filtered_mentors
    assert mentor2 not in filtered_mentors # Capacity
    assert mentor4 not in filtered_mentors # Industry mismatch

    print("\n--- Testing Filters with Mentee No Preferences ---")
    filtered_mentors_no_prefs = apply_filters(mentee_profile_no_prefs, candidates, min_overlap_minutes=30)
    print("\nFiltered Mentors (Mentee No Prefs):")
    for m in filtered_mentors_no_prefs:
         print(f"  Mentor ID: {m['id']}, Current Mentees: {m['current_mentees']}/{m['capacity']}, Overlap (min): {m.get('__overlap_minutes')}, IndMatch: {m.get('__industry_match')}, LangMatch: {m.get('__language_match')}")
    # With no mentee preferences, all mentors that pass capacity/availability should pass preference filters.
    # Mentor 1, 3, 5 should pass. Mentor 2 fails capacity, Mentor 4 fails availability overlap based on setup.
    assert len(filtered_mentors_no_prefs) == 3
    assert mentor1 in filtered_mentors_no_prefs
    assert mentor3 in filtered_mentors_no_prefs
    assert mentor5 in filtered_mentors_no_prefs


    # Test time overlap calculation
    print("\n--- Testing Time Overlap ---")
    mentor_avail_test = {'Mon': ['09:00-11:00', '14:00-16:00']}
    mentee_avail_test = {'Mon': ['10:00-12:00', '15:00-17:00']}
    overlap = calculate_time_overlap_minutes(mentor_avail_test, mentee_avail_test)
    print(f"Overlap for test: {overlap} minutes") # Expected: 60 (10-11) + 60 (15-16) = 120
    assert overlap == 120, f"Expected 120 minutes overlap, got {overlap}"

    mentor_avail_test2 = {'Tue': ['09:00-10:00']}
    mentee_avail_test2 = {'Wed': ['09:00-10:00']}
    overlap2 = calculate_time_overlap_minutes(mentor_avail_test2, mentee_avail_test2)
    print(f"Overlap for test2 (no overlap): {overlap2} minutes")
    assert overlap2 == 0

    mentor_avail_test3 = {'Mon': ['09:00-10:00']}
    mentee_avail_test3 = {'Mon': ['09:00-09:30']}
    overlap3 = calculate_time_overlap_minutes(mentor_avail_test3, mentee_avail_test3)
    print(f"Overlap for test3 (partial overlap): {overlap3} minutes")
    assert overlap3 == 30

    print("\nFiltering tests passed!")