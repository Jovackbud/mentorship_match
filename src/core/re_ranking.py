import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def _normalize_score(score: float, min_val: float, max_val: float) -> float:
    """
    Min-Max Normalization to scale a score to [0, 1].
    Handles cases where min_val == max_val to prevent division by zero.
    """
    if max_val == min_val:
        return 1.0 if score > min_val else 0.0 # If all values are same, assign max importance if it's the max, else min.
    return (score - min_val) / (max_val - min_val)

# Define weights for the re-ranking heuristics
# These can be tuned based on desired prioritization
WEIGHTS = {
    "cosine_similarity": 1.0, # Directly from embedding similarity
    "availability_overlap_minutes": 0.8, # 1 minute of overlap = 0.8 score point
    "preference_match_count": 0.7, # Each matching preference adds 0.7
    # Add more weights here for other relevant features if needed
}

def re_rank_mentors(candidate_mentors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Re-ranks a list of candidate mentors based on a weighted sum of heuristic features.
    Features are normalized to a [0, 1] range before applying weights.

    Args:
        candidate_mentors (List[Dict[str, Any]]): A list of mentor profiles,
                                                  expected to contain '__score', '__overlap_minutes',
                                                  and '__preference_match_count'
                                                  populated by previous steps.

    Returns:
        List[Dict[str, Any]]: The re-ranked list of mentor profiles.
    """
    if not candidate_mentors:
        return []

    # --- Step 1: Extract raw feature values to determine min/max for normalization ---
    # Ensure we handle cases where a feature might be missing for all candidates
    raw_overlap_minutes_values = [m.get('__overlap_minutes', 0) for m in candidate_mentors if '__overlap_minutes' in m]
    raw_preference_match_counts = [m.get('__preference_match_count', 0) for m in candidate_mentors if '__preference_match_count' in m]

    # Determine min/max for normalization. If no values, default to 0 for min/max.
    min_overlap, max_overlap = (min(raw_overlap_minutes_values), max(raw_overlap_minutes_values)) if raw_overlap_minutes_values else (0, 0)
    min_pref_count, max_pref_count = (min(raw_preference_match_counts), max(raw_preference_match_counts)) if raw_preference_match_counts else (0, 0)

    # --- Step 2: Calculate normalized scores and combined re-rank score ---
    ranked_mentors = []
    for mentor in candidate_mentors:
        cosine_similarity = mentor.get('__score', 0.0) # Assume cosine_similarity is already normalized [0, 1]
        raw_overlap = mentor.get('__overlap_minutes', 0)
        raw_pref_match = mentor.get('__preference_match_count', 0)

        # Normalize the features
        normalized_overlap = _normalize_score(raw_overlap, min_overlap, max_overlap)
        normalized_pref_match = _normalize_score(raw_pref_match, min_pref_count, max_pref_count)

        # Calculate a combined re-ranking score using normalized values
        re_rank_score = (
            WEIGHTS["cosine_similarity"] * cosine_similarity +
            WEIGHTS["availability_overlap_minutes"] * normalized_overlap +
            WEIGHTS["preference_match_count"] * normalized_pref_match
        )
        mentor['__re_rank_score'] = re_rank_score
        ranked_mentors.append(mentor)

    # Sort mentors by the calculated re-rank score in descending order
    ranked_mentors.sort(key=lambda x: x['__re_rank_score'], reverse=True)

    logger.info(f"Re-ranked {len(ranked_mentors)} mentors.")
    return ranked_mentors

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    mentors_to_rank = [
        {'id': 1, 'bio': 'Python SE', '__score': 0.85, '__overlap_minutes': 90, '__preference_match_count': 2},
        {'id': 2, 'bio': 'Data Scientist', '__score': 0.88, '__overlap_minutes': 30, '__preference_match_count': 1},
        {'id': 3, 'bio': 'Product Manager', '__score': 0.70, '__overlap_minutes': 120, '__preference_match_count': 2},
        {'id': 4, 'bio': 'Frontend Dev', '__score': 0.90, '__overlap_minutes': 60, '__preference_match_count': 1},
        {'id': 5, 'bio': 'UX Designer', '__score': 0.75, '__overlap_minutes': 90, '__preference_match_count': 0}, # Add an edge case
    ]

    print("Original order:")
    for m in mentors_to_rank:
        print(f"  ID: {m['id']}, Sim: {m['__score']:.2f}, Overlap: {m['__overlap_minutes']}, PrefMatch: {m['__preference_match_count']}")

    ranked_list = re_rank_mentors(mentors_to_rank)

    print("\nRe-ranked order:")
    for m in ranked_list:
        print(f"  ID: {m['id']}, Re-rank Score: {m['__re_rank_score']:.2f}, Sim: {m['__score']:.2f}, Overlap: {m.get('__overlap_minutes')}, PrefMatch: {m.get('__preference_match_count')}")

    assert ranked_list[0]['id'] == 3
    assert ranked_list[1]['id'] == 1
    assert ranked_list[2]['id'] == 4
    assert ranked_list[3]['id'] == 5
    assert ranked_list[4]['id'] == 2

    print("\nRe-ranking tests passed with normalization!")