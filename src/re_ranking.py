import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Define weights for the re-ranking heuristics
# These can be tuned based on desired prioritization
WEIGHTS = {
    "cosine_similarity": 1.0, # Directly from embedding similarity
    "availability_overlap_minutes": 0.01, # 1 minute of overlap = 0.01 score point
    "preference_match_count": 0.5, # Each matching preference adds 0.5
    # Add more weights here for other relevant features if needed
}

def re_rank_mentors(candidate_mentors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Re-ranks a list of candidate mentors based on a weighted sum of heuristic features.

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

    ranked_mentors = []
    for mentor in candidate_mentors:
        # Features that should be present from previous steps (retrieval and filtering)
        cosine_similarity = mentor.get('__score', 0.0)
        availability_overlap_minutes = mentor.get('__overlap_minutes', 0)
        preference_match_count = mentor.get('__preference_match_count', 0)

        # Calculate a combined re-ranking score
        re_rank_score = (
            WEIGHTS["cosine_similarity"] * cosine_similarity +
            WEIGHTS["availability_overlap_minutes"] * availability_overlap_minutes +
            WEIGHTS["preference_match_count"] * preference_match_count
        )
        mentor['__re_rank_score'] = re_rank_score
        ranked_mentors.append(mentor)

    # Sort mentors by the calculated re-rank score in descending order
    ranked_mentors.sort(key=lambda x: x['__re_rank_score'], reverse=True)

    logger.info(f"Re-ranked {len(ranked_mentors)} mentors.")
    return ranked_mentors

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Example candidate mentors with mock scores and filter attributes
    # '__score' would come from FAISS similarity
    # '__overlap_minutes' and '__preference_match_count' from filtering.py
    mentors_to_rank = [
        {'id': 1, 'bio': 'Python SE', '__score': 0.85, '__overlap_minutes': 90, '__preference_match_count': 2},
        {'id': 2, 'bio': 'Data Scientist', '__score': 0.88, '__overlap_minutes': 30, '__preference_match_count': 1},
        {'id': 3, 'bio': 'Product Manager', '__score': 0.70, '__overlap_minutes': 120, '__preference_match_count': 2},
        {'id': 4, 'bio': 'Frontend Dev', '__score': 0.90, '__overlap_minutes': 60, '__preference_match_count': 1},
    ]

    print("Original order:")
    for m in mentors_to_rank:
        print(f"  ID: {m['id']}, Sim: {m['__score']:.2f}, Overlap: {m['__overlap_minutes']}, PrefMatch: {m['__preference_match_count']}")

    ranked_list = re_rank_mentors(mentors_to_rank)

    print("\nRe-ranked order:")
    for m in ranked_list:
        print(f"  ID: {m['id']}, Re-rank Score: {m['__re_rank_score']:.2f}, Sim: {m['__score']:.2f}")

    # Expected order based on weights (1.0 * sim + 0.01 * overlap + 0.5 * pref_match)
    # Mentor 1: 0.85 + 0.01*90 + 0.5*2 = 0.85 + 0.9 + 1.0 = 2.75
    # Mentor 2: 0.88 + 0.01*30 + 0.5*1 = 0.88 + 0.3 + 0.5 = 1.68
    # Mentor 3: 0.70 + 0.01*120 + 0.5*2 = 0.70 + 1.2 + 1.0 = 2.90
    # Mentor 4: 0.90 + 0.01*60 + 0.5*1 = 0.90 + 0.6 + 0.5 = 2.00
    # Expected ranking: 3, 1, 4, 2
    assert ranked_list[0]['id'] == 3
    assert ranked_list[1]['id'] == 1
    assert ranked_list[2]['id'] == 4
    assert ranked_list[3]['id'] == 2

    print("\nRe-ranking tests passed!")