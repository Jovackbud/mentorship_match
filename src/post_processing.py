import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def post_process_matches(
    ranked_mentors: List[Dict[str, Any]],
    mentee_profile: Dict[str, Any],
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    Applies post-processing to the ranked list of mentors.
    Enforces limits and adds explanations.

    Args:
        ranked_mentors (List[Dict[str, Any]]): List of ranked mentor profiles.
        mentee_profile (Dict[str, Any]): The mentee's profile.
        limit (int): The maximum number of recommendations to return.

    Returns:
        List[Dict[str, Any]]: Final list of recommended mentors with explanations.
    """
    final_recommendations = []

    top_n_mentors = ranked_mentors[:limit]

    for mentor in top_n_mentors:
        explanations = []

        # Explanation for semantic similarity
        cosine_similarity = mentor.get('__score')
        if cosine_similarity is not None:
            explanations.append(f"High goal alignment (semantic similarity: {cosine_similarity:.2f}).")

        # Explanation for availability overlap
        overlap_minutes = mentor.get('__overlap_minutes')
        if overlap_minutes is not None and overlap_minutes > 0:
            # Enhanced explanation for hours/minutes (from previous feedback)
            hours, minutes_remainder = divmod(overlap_minutes, 60)
            overlap_str_parts = []
            if hours > 0:
                overlap_str_parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
            if minutes_remainder > 0:
                overlap_str_parts.append(f"{minutes_remainder} minute{'s' if minutes_remainder > 1 else ''}")
            
            if overlap_str_parts:
                explanations.append(f"Availability overlap of {', '.join(overlap_str_parts)} per week.")

        # Explanation for preference matches
        preference_match_count = mentor.get('__preference_match_count')
        if preference_match_count is not None and preference_match_count > 0:
            pref_details = []
            if mentor.get('__industry_match'):
                pref_details.append("matching industry")
            if mentor.get('__language_match'):
                pref_details.append("matching language")
            if pref_details:
                explanations.append(f"Strong preference alignment ({', '.join(pref_details)}).")

        # Assemble the final recommendation structure
        # NEW: Added mentor_name, keeping mentor_bio_snippet
        raw_bio = mentor.get('bio', '')
        bio_snippet = raw_bio[:100]
        if len(raw_bio) > 100:
            bio_snippet += '...'

        recommendation = {
            "mentor_id": mentor.get('id'),
            "mentor_name": mentor.get('name', 'Unknown Mentor'), # ADD THIS LINE
            "mentor_bio_snippet": bio_snippet, # Using refined bio snippet
            "re_rank_score": mentor.get('__re_rank_score'),
            "explanations": explanations,
            "mentor_details": {
                "expertise": mentor.get('expertise'),
                "capacity_info": f"{mentor.get('current_mentees')}/{mentor.get('capacity')} mentees",
            }
        }
        final_recommendations.append(recommendation)

    logger.info(f"Post-processed to {len(final_recommendations)} recommendations.")
    return final_recommendations

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Example ranked mentors from re_ranking.py output
    ranked_mentors = [
        {'id': 3, 'bio': 'Product Manager with 10 years experience in tech startups. Specializing in AI products.', 'expertise': 'Product Management', 'capacity': 2, 'current_mentees': 0, '__score': 0.70, '__overlap_minutes': 120, '__preference_match_count': 2, '__industry_match': True, '__language_match': True, '__re_rank_score': 2.90},
        {'id': 1, 'bio': 'Experienced software engineer with 10 years in Python backend development. Focus on scalable systems.', 'expertise': 'Software Engineering', 'capacity': 2, 'current_mentees': 0, '__score': 0.85, '__overlap_minutes': 90, '__preference_match_count': 2, '__industry_match': True, '__language_match': True, '__re_rank_score': 2.75},
        {'id': 4, 'bio': 'Seasoned Frontend Developer with expertise in React and Vue. Passionate about user experience.', 'expertise': 'Frontend Development', 'capacity': 2, 'current_mentees': 0, '__score': 0.90, '__overlap_minutes': 60, '__preference_match_count': 1, '__industry_match': True, '__language_match': False, '__re_rank_score': 2.00},
        {'id': 2, 'bio': 'Data scientist focusing on ethical AI and ML models. Helping aspiring data professionals.', 'expertise': 'Data Science', 'capacity': 1, 'current_mentees': 0, '__score': 0.88, '__overlap_minutes': 30, '__preference_match_count': 1, '__industry_match': True, '__language_match': False, '__re_rank_score': 1.68},
    ]

    mentee_profile = {'id': 101, 'bio': 'Looking for a tech mentor.'}

    print("\n--- Testing Post-Processing ---")
    recommendations = post_process_matches(ranked_mentors, mentee_profile, limit=3)

    print("\nFinal Recommendations:")
    for rec in recommendations:
        print(f"  Mentor ID: {rec['mentor_id']}, Score: {rec['re_rank_score']:.2f}")
        print(f"    Explanations: {'; '.join(rec['explanations'])}")
        print(f"    Details: {rec['mentor_details']}")

    assert len(recommendations) == 3
    assert recommendations[0]['mentor_id'] == 3
    assert recommendations[1]['mentor_id'] == 1
    assert recommendations[2]['mentor_id'] == 4

    # Check a specific explanation
    assert "High goal alignment (semantic similarity: 0.70)." in recommendations[0]['explanations']
    assert "Availability overlap of 120 minutes per week." in recommendations[0]['explanations']
    assert "Strong preference alignment (matching industry, matching language)." in recommendations[0]['explanations']


    print("\nPost-processing tests passed!")