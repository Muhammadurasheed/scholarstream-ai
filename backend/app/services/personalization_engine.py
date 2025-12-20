"""
Personalization Engine - Deep matching based on user interests and passions
Transforms ScholarStream from generic to highly personalized
"""
from typing import Dict, Any, List
import structlog

logger = structlog.get_logger()


class PersonalizationEngine:
    """Advanced personalization using interests, passions, and behavior"""
    
    def __init__(self):
        # Interest-to-keyword mapping for intelligent matching
        self.interest_keywords = {
            'artificial intelligence': ['AI', 'machine learning', 'deep learning', 'neural networks', 'NLP', 'computer vision', 'GPT', 'LLM'],
            'web development': ['web', 'frontend', 'backend', 'fullstack', 'React', 'Node.js', 'JavaScript', 'TypeScript', 'Next.js'],
            'cybersecurity': ['security', 'hacking', 'penetration testing', 'bug bounty', 'CTF', 'cryptography', 'ethical hacking'],
            'data science': ['data', 'analytics', 'statistics', 'visualization', 'pandas', 'numpy', 'data analysis'],
            'mobile development': ['mobile', 'iOS', 'Android', 'React Native', 'Flutter', 'Swift', 'Kotlin', 'app development'],
            'blockchain': ['blockchain', 'cryptocurrency', 'Web3', 'smart contracts', 'Ethereum', 'Solidity', 'DeFi'],
            'game development': ['game', 'Unity', '3D', 'graphics', 'Unreal Engine', 'game design', 'gaming'],
            'robotics': ['robotics', 'automation', 'embedded systems', 'Arduino', 'ROS', 'mechatronics', 'IoT'],
            'healthcare tech': ['healthcare', 'medical', 'biotech', 'health informatics', 'telemedicine', 'healthtech'],
            'fintech': ['finance', 'banking', 'payments', 'trading', 'financial technology', 'fintech'],
            'social impact': ['social good', 'nonprofit', 'education', 'accessibility', 'sustainability', 'impact'],
            'entrepreneurship': ['startup', 'business', 'innovation', 'venture', 'founder', 'entrepreneur'],
            'cloud computing': ['cloud', 'AWS', 'Azure', 'GCP', 'serverless', 'DevOps', 'infrastructure'],
            'ui/ux design': ['design', 'UI', 'UX', 'user experience', 'Figma', 'product design', 'interface'],
            # Direct User Inputs
            'ai': ['AI', 'artificial intelligence', 'machine learning', 'LLM', 'GPT'],
            'coding': ['coding', 'software', 'programming', 'development', 'code'],
            'python': ['python', 'django', 'flask', 'fastapi', 'pandas'],
            'hackathons': ['hackathon', 'hack', 'build', 'competition'],
            'software': ['software', 'engineering', 'developer', 'SaaS'],
        }
    
    def _get_attr(self, obj: Any, attr: str, default: Any = None) -> Any:
        """Helper to get attribute from object or key from dict"""
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    def _safe_get_dict(self, data: Dict[str, Any], key: str) -> Dict[str, Any]:
        """Safely get a nested dict, handling cases where it might be a string"""
        val = data.get(key)
        if isinstance(val, dict):
            return val
        return {}

    def calculate_personalized_score(
        self, 
        opportunity: Dict[str, Any], 
        user_profile: Any
    ) -> float:
        """
        Calculate personalized match score (0-100)
        Considers interests, passions, skills, and demographics
        """
        score = 0.0
        max_score = 100.0
        
        # 1. Interest Match (40 points max) - MOST IMPORTANT
        interest_score = self._score_interests(opportunity, user_profile)
        score += interest_score * 0.4
        
        # 2. Passion Alignment (30 points max)
        passion_score = self._score_passions(opportunity, user_profile)
        score += passion_score * 0.3
        
        # 3. Demographic Match (20 points max)
        demographic_score = self._score_demographics(opportunity, user_profile)
        score += demographic_score * 0.2
        
        # 4. Academic Fit (10 points max)
        academic_score = self._score_academics(opportunity, user_profile)
        score += academic_score * 0.1
        
        try:
             opp_name = opportunity.get('name') or opportunity.get('title') or 'Unknown'
             logger.debug(
                "Personalization score calculated",
                opportunity=opp_name,
                interest_score=interest_score,
                passion_score=passion_score,
                demographic_score=demographic_score,
                academic_score=academic_score,
                final_score=score
             )
        except Exception:
             pass
        
        # Minimum Floor: Every opportunity gets at least 30 points 
        # to avoid showing "0% Match" for new users with empty profiles.
        return max(min(score, max_score), 30.0)
    
    def _score_interests(self, opp: Dict[str, Any], profile: Any) -> float:
        """Score based on user interests (0-100)"""
        interests = self._get_attr(profile, 'interests') or []
        
        if not interests:
            return 50.0  # Neutral score if no interests
        
        user_interests = [str(i).lower() for i in interests]
        opp_text = self._get_opportunity_text(opp).lower()
        
    def _score_interests(self, opp: Dict[str, Any], profile: Any) -> float:
        """Score based on user interests (0-100)"""
        interests = self._get_attr(profile, 'interests') or []
        
        if not interests:
            return 50.0  # Neutral score if no interests
        
        user_interests = [str(i).lower() for i in interests]
        opp_text = self._get_opportunity_text(opp).lower()
        
        satisfied_interests = 0
        matched_details = []
        
        for interest in user_interests:
            # Get keywords for this interest
            keywords = self.interest_keywords.get(interest, [interest])
            
            # Check if ANY keyword matches (Interest Satisfied)
            if any(keyword.lower() in opp_text for keyword in keywords):
                satisfied_interests += 1
                matched_details.append(interest)
        
        if not user_interests:
            return 50.0
        
        # Calculate match rate: % of User's Interests found in Opportunity
        match_rate = satisfied_interests / len(user_interests)
        
        # Boost: If more than 50% of interests match, boost by 1.2
        if match_rate > 0.5:
            match_rate = min(match_rate * 1.2, 1.0)
            
        logger.debug(
            "Interest scoring",
            user_interests=user_interests,
            matched=matched_details,
            rate=match_rate
        )
        
        return match_rate * 100
    
    def _score_passions(self, opp: Dict[str, Any], profile: Any) -> float:
        """Score based on user passions (0-100)"""
        # Passions are stored in profile.background or profile.interests
        background = self._get_attr(profile, 'background') or []
        
        if not background:
            return 50.0
        
        opp_text = self._get_opportunity_text(opp).lower()
        
        # Check for passion matches
        passion_matches = 0
        for passion in background:
            if isinstance(passion, str) and passion.lower() in opp_text:
                passion_matches += 1
        
        if len(background) == 0:
            return 50.0
        
        match_rate = passion_matches / len(background)
        return match_rate * 100
    
    def _score_demographics(self, opp: Dict[str, Any], profile: Any) -> float:
        """Score based on demographic match (0-100)"""
        score = 0.0
        checks = 0
        
        eligibility = self._safe_get_dict(opp, 'eligibility')
        
        # GPA check
        gpa_min = eligibility.get('gpa_min')
        user_gpa = self._get_attr(profile, 'gpa')
        
        if gpa_min and user_gpa:
            checks += 1
            if user_gpa >= gpa_min:
                score += 100
            elif user_gpa >= (gpa_min - 0.3):
                score += 50
        
        # Major check
        required_majors = eligibility.get('majors')
        user_major = self._get_attr(profile, 'major')
        
        if required_majors and user_major:
            checks += 1
            if any(major.lower() in user_major.lower() for major in required_majors):
                score += 100
        elif not required_majors:
            # Open to all majors
            checks += 1
            score += 80
        
        # Background check
        required_backgrounds = eligibility.get('backgrounds', [])
        user_background = self._get_attr(profile, 'background') or []
        
        if required_backgrounds and user_background:
            checks += 1
            if any(bg in required_backgrounds for bg in user_background):
                score += 100
        
        return (score / checks) if checks > 0 else 50.0
    
    def _score_academics(self, opp: Dict[str, Any], profile: Any) -> float:
        """Score based on academic fit (0-100)"""
        score = 0.0
        
        # Academic status match
        academic_status = self._get_attr(profile, 'academic_status')
        
        if academic_status:
            eligibility = self._safe_get_dict(opp, 'eligibility')
            grade_levels = eligibility.get('grade_levels', []) or eligibility.get('grades_eligible', [])
            
            if academic_status in grade_levels:
                score += 100
            elif any(level.lower() in academic_status.lower() for level in grade_levels):
                score += 70
            elif not grade_levels:
                # Open to all academic levels
                score += 60
        
        return score
    
    def _get_opportunity_text(self, opp: Dict[str, Any]) -> str:
        """Get all searchable text from opportunity"""
        parts = [
            opp.get('name', ''),
            opp.get('description', ''),
            opp.get('organization', ''),
            ' '.join(opp.get('tags', [])),
        ]
        
        # Add requirements text
        requirements = self._safe_get_dict(opp, 'requirements')
        skills = requirements.get('skills_needed', [])
        if skills:
            parts.append(' '.join(skills))
        
        return ' '.join(parts)


# Global instance
personalization_engine = PersonalizationEngine()
